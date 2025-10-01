"""
Unit tests for project status service and transitions.

This module tests the ProjectStatusService functionality including
status transitions, validation, progress calculation, and audit trails.
"""

import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import Project, StatusTransition, Organization, Client, User
from apps.core.services.status_service import ProjectStatusService


class ProjectStatusServiceTestCase(TestCase):
    """Test ProjectStatusService functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create organization and client
        self.org = Organization.objects.create(
            name="Test Organization",
            organization_type="business",
            email="contact@testorg.com"
        )
        self.client = Client.objects.create(
            organization=self.org,
            client_since="2024-01-01",
            relationship_status="active"
        )
        
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@sumano.tech",
            first_name="Test",
            last_name="User"
        )
        
        # Create project
        self.project = Project.objects.create(
            client=self.client,
            project_name="Test Project",
            project_code="TEST-001",
            service_type="web_development",
            description="A test project",
            start_date="2024-01-01"
        )
    
    def test_valid_status_transitions(self):
        """Test that valid status transitions are allowed."""
        # Test lead -> quoted
        self.assertTrue(
            ProjectStatusService.validate_status_transition('lead', 'quoted')
        )
        
        # Test quoted -> approved
        self.assertTrue(
            ProjectStatusService.validate_status_transition('quoted', 'approved')
        )
        
        # Test development -> testing
        self.assertTrue(
            ProjectStatusService.validate_status_transition('development', 'testing')
        )
        
        # Test any status -> on_hold
        self.assertTrue(
            ProjectStatusService.validate_status_transition('development', 'on_hold')
        )
        
        # Test on_hold -> development
        self.assertTrue(
            ProjectStatusService.validate_status_transition('on_hold', 'development')
        )
    
    def test_invalid_status_transitions(self):
        """Test that invalid status transitions raise ValidationError."""
        # Test invalid transitions
        with self.assertRaises(ValidationError):
            ProjectStatusService.validate_status_transition('lead', 'development')
        
        with self.assertRaises(ValidationError):
            ProjectStatusService.validate_status_transition('completed', 'development')
        
        with self.assertRaises(ValidationError):
            ProjectStatusService.validate_status_transition('testing', 'lead')
    
    def test_same_status_transition(self):
        """Test that same status transition is allowed."""
        self.assertTrue(
            ProjectStatusService.validate_status_transition('development', 'development')
        )
    
    def test_transition_status_success(self):
        """Test successful status transition."""
        # Transition from lead to quoted
        transition = ProjectStatusService.transition_status(
            self.project,
            'quoted',
            user=self.user,
            reason="Client requested quote",
            notes="Initial quote provided"
        )
        
        # Verify project status updated
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, 'quoted')
        self.assertEqual(self.project.progress_percentage, 5)  # STATUS_PROGRESS_MAP
        
        # Verify status transition record created
        self.assertEqual(transition.from_status, 'lead')
        self.assertEqual(transition.to_status, 'quoted')
        self.assertEqual(transition.user, self.user)
        self.assertEqual(transition.reason, "Client requested quote")
        self.assertEqual(transition.notes, "Initial quote provided")
        
        # Verify timestamp updated
        self.assertIsNotNone(self.project.status_updated_at)
    
    def test_transition_status_invalid(self):
        """Test status transition with invalid transition."""
        with self.assertRaises(ValidationError):
            ProjectStatusService.transition_status(
                self.project,
                'development',  # Invalid: lead -> development
                user=self.user
            )
        
        # Verify project status unchanged
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, 'lead')
    
    def test_transition_status_audit_trail(self):
        """Test that status transitions create proper audit trail."""
        # Make multiple transitions
        ProjectStatusService.transition_status(
            self.project, 'quoted', user=self.user, reason="Quote requested"
        )
        ProjectStatusService.transition_status(
            self.project, 'approved', user=self.user, reason="Quote approved"
        )
        ProjectStatusService.transition_status(
            self.project, 'planning', user=self.user, reason="Project approved"
        )
        
        # Verify audit trail
        transitions = self.project.status_transitions.all().order_by('timestamp')
        self.assertEqual(transitions.count(), 3)
        
        # Check transition sequence
        self.assertEqual(transitions[0].from_status, 'lead')
        self.assertEqual(transitions[0].to_status, 'quoted')
        self.assertEqual(transitions[1].from_status, 'quoted')
        self.assertEqual(transitions[1].to_status, 'approved')
        self.assertEqual(transitions[2].from_status, 'approved')
        self.assertEqual(transitions[2].to_status, 'planning')
    
    def test_calculate_progress_no_phases(self):
        """Test progress calculation for project without phases."""
        # Set project status to development
        self.project.status = 'development'
        self.project.save()
        
        progress = ProjectStatusService.calculate_progress(self.project)
        self.assertEqual(progress, 50)  # STATUS_PROGRESS_MAP['development']
    
    def test_calculate_progress_with_phases(self):
        """Test progress calculation for project with phases."""
        from apps.core.models import ProjectPhase
        
        # Create project phases
        phase1 = ProjectPhase.objects.create(
            project=self.project,
            phase_name="Phase 1",
            phase_number=1,
            description="First phase",
            start_date="2024-01-01",
            target_end_date="2024-01-15",
            status="completed"
        )
        phase2 = ProjectPhase.objects.create(
            project=self.project,
            phase_name="Phase 2",
            phase_number=2,
            description="Second phase",
            start_date="2024-01-16",
            target_end_date="2024-01-30",
            status="in_progress"
        )
        
        progress = ProjectStatusService.calculate_progress(self.project)
        # 1 completed out of 2 phases = 50%
        self.assertEqual(progress, 50)
    
    def test_calculate_progress_with_documents(self):
        """Test progress calculation with documents."""
        from apps.core.models import DocumentTemplate, DocumentInstance
        
        # Create document template
        template = DocumentTemplate.objects.create(
            name="Test Template",
            description="Test",
            document_type="proposal",
            template_content="Content",
            template_format="html"
        )
        
        # Create document instances
        doc1 = DocumentInstance.objects.create(
            project=self.project,
            template=template,
            template_version="1.0",
            document_name="Doc 1",
            document_type="proposal",
            filled_data={},
            status="final"
        )
        doc2 = DocumentInstance.objects.create(
            project=self.project,
            template=template,
            template_version="1.0",
            document_name="Doc 2",
            document_type="proposal",
            filled_data={},
            status="draft"
        )
        
        # Create phases
        from apps.core.models import ProjectPhase
        ProjectPhase.objects.create(
            project=self.project,
            phase_name="Phase 1",
            phase_number=1,
            description="First phase",
            start_date="2024-01-01",
            target_end_date="2024-01-15",
            status="completed"
        )
        ProjectPhase.objects.create(
            project=self.project,
            phase_name="Phase 2",
            phase_number=2,
            description="Second phase",
            start_date="2024-01-16",
            target_end_date="2024-01-30",
            status="in_progress"
        )
        
        progress = ProjectStatusService.calculate_progress(self.project)
        # 50% phases * 0.7 + 50% docs * 0.3 = 50%
        self.assertEqual(progress, 50)
    
    def test_update_progress(self):
        """Test updating project progress."""
        # Set initial progress
        self.project.progress_percentage = 0
        self.project.save()
        
        # Update progress
        ProjectStatusService.update_progress(self.project)
        
        # Verify progress updated
        self.project.refresh_from_db()
        self.assertEqual(self.project.progress_percentage, 0)  # lead status = 0%
    
    def test_get_service_type_stats(self):
        """Test service type statistics aggregation."""
        # Create additional projects
        Project.objects.create(
            client=self.client,
            project_name="Mobile Project",
            project_code="MOBILE-001",
            service_type="mobile_app",
            description="Mobile app project",
            start_date="2024-01-01"
        )
        Project.objects.create(
            client=self.client,
            project_name="Audit Project",
            project_code="AUDIT-001",
            service_type="audit",
            description="Audit project",
            start_date="2024-01-01"
        )
        
        stats = ProjectStatusService.get_service_type_stats()
        
        # Verify web_development stats
        self.assertEqual(stats['web_development']['total_projects'], 1)
        self.assertEqual(stats['web_development']['name'], 'Website Development')
        
        # Verify mobile_app stats
        self.assertEqual(stats['mobile_app']['total_projects'], 1)
        self.assertEqual(stats['mobile_app']['name'], 'Mobile Application')
        
        # Verify audit stats
        self.assertEqual(stats['audit']['total_projects'], 1)
        self.assertEqual(stats['audit']['name'], 'System Audit')
    
    def test_get_status_distribution(self):
        """Test status distribution aggregation."""
        # Create projects with different statuses
        Project.objects.create(
            client=self.client,
            project_name="Project 2",
            project_code="PROJ-002",
            service_type="web_development",
            description="Second project",
            start_date="2024-01-01",
            status="quoted"
        )
        Project.objects.create(
            client=self.client,
            project_name="Project 3",
            project_code="PROJ-003",
            service_type="mobile_app",
            description="Third project",
            start_date="2024-01-01",
            status="development"
        )
        
        distribution = ProjectStatusService.get_status_distribution()
        
        self.assertEqual(distribution['lead']['count'], 1)
        self.assertEqual(distribution['quoted']['count'], 1)
        self.assertEqual(distribution['development']['count'], 1)
        self.assertEqual(distribution['completed']['count'], 0)
    
    def test_get_priority_distribution(self):
        """Test priority distribution aggregation."""
        # Create projects with different priorities
        self.project.priority = 'high'
        self.project.save()
        
        Project.objects.create(
            client=self.client,
            project_name="Low Priority Project",
            project_code="LOW-001",
            service_type="web_development",
            description="Low priority project",
            start_date="2024-01-01",
            priority="low"
        )
        
        distribution = ProjectStatusService.get_priority_distribution()
        
        self.assertEqual(distribution['high']['count'], 1)
        self.assertEqual(distribution['low']['count'], 1)
        self.assertEqual(distribution['medium']['count'], 0)
    
    def test_get_overdue_projects(self):
        """Test getting overdue projects."""
        from datetime import timedelta
        
        # Create overdue project
        overdue_date = timezone.now().date() - timedelta(days=5)
        overdue_project = Project.objects.create(
            client=self.client,
            project_name="Overdue Project",
            project_code="OVERDUE-001",
            service_type="web_development",
            description="Overdue project",
            start_date="2024-01-01",
            target_end_date=overdue_date,
            status="development"
        )
        
        # Create non-overdue project
        future_date = timezone.now().date() + timedelta(days=5)
        Project.objects.create(
            client=self.client,
            project_name="Future Project",
            project_code="FUTURE-001",
            service_type="web_development",
            description="Future project",
            start_date="2024-01-01",
            target_end_date=future_date,
            status="development"
        )
        
        overdue_projects = ProjectStatusService.get_overdue_projects()
        
        self.assertEqual(overdue_projects.count(), 1)
        self.assertEqual(overdue_projects.first(), overdue_project)
    
    def test_get_project_timeline(self):
        """Test getting project timeline."""
        # Create status transitions
        ProjectStatusService.transition_status(
            self.project, 'quoted', user=self.user, reason="Quote requested"
        )
        ProjectStatusService.transition_status(
            self.project, 'approved', user=self.user, reason="Quote approved"
        )
        
        timeline = ProjectStatusService.get_project_timeline(self.project)
        
        self.assertEqual(timeline.count(), 2)
        self.assertEqual(timeline[0].to_status, 'quoted')  # First transition
        self.assertEqual(timeline[1].to_status, 'approved')  # Second transition
    
    def test_transaction_rollback_on_error(self):
        """Test that transaction is rolled back on error."""
        # Mock an error during save
        original_save = Project.save
        
        def failing_save(self, *args, **kwargs):
            raise Exception("Database error")
        
        Project.save = failing_save
        
        try:
            with self.assertRaises(Exception):
                ProjectStatusService.transition_status(
                    self.project, 'quoted', user=self.user
                )
            
            # Verify no status transition was created
            self.assertEqual(self.project.status_transitions.count(), 0)
        finally:
            # Restore original save method
            Project.save = original_save
    
    def test_status_progress_mapping(self):
        """Test that status changes update progress correctly."""
        # Test each status and its expected progress
        status_progress_tests = [
            ('quoted', 5),
            ('approved', 10),
            ('planning', 20),
            ('development', 50),
            ('testing', 80),
            ('client_review', 95),
            ('completed', 100),
        ]
        
        # Reset project to lead and transition through valid sequence
        self.project.status = 'lead'
        self.project.progress_percentage = 0
        self.project.save()
        
        # Transition through valid sequence: lead -> quoted -> approved -> planning -> development -> testing -> client_review -> completed
        valid_sequence = ['quoted', 'approved', 'planning', 'development', 'testing', 'client_review', 'completed']
        
        for i, status in enumerate(valid_sequence):
            expected_progress = status_progress_tests[i][1]
            
            # Transition to new status
            ProjectStatusService.transition_status(
                self.project, status, user=self.user
            )
            
            # Verify progress updated
            self.project.refresh_from_db()
            self.assertEqual(self.project.progress_percentage, expected_progress)
    
    def test_on_hold_status_progress_preservation(self):
        """Test that on_hold status preserves existing progress."""
        # Set project to development (50% progress)
        self.project.status = 'development'
        self.project.progress_percentage = 50
        self.project.save()
        
        # Transition to on_hold
        ProjectStatusService.transition_status(
            self.project, 'on_hold', user=self.user
        )
        
        # Verify progress preserved
        self.project.refresh_from_db()
        self.assertEqual(self.project.progress_percentage, 50)
    
    def test_user_optional_in_transition(self):
        """Test that user is optional in status transition."""
        transition = ProjectStatusService.transition_status(
            self.project, 'quoted'
        )
        
        self.assertIsNone(transition.user)
        self.assertEqual(transition.from_status, 'lead')
        self.assertEqual(transition.to_status, 'quoted')
