"""
Test cases for Pilot Handover functionality.
"""
import json
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.core.models import (
    PilotHandover, Project, Client, Organization, DocumentInstance,
    DocumentTemplate, Role, Permission
)

User = get_user_model()


class PilotHandoverModelTestCase(TestCase):
    """Test cases for the PilotHandover model."""

    def setUp(self):
        # Create roles
        self.superadmin_role, _ = Role.objects.get_or_create(
            codename='superadmin', defaults={'name': 'Super Admin'}
        )
        self.staff_role, _ = Role.objects.get_or_create(
            codename='staff', defaults={'name': 'Staff'}
        )

        # Create users
        self.staff_user = User.objects.create_user(
            username='staffuser', email='staff@example.com', password='testpass', employee_id='EMP001'
        )
        self.staff_user.role = self.staff_role
        self.staff_user.save()

        # Create organization and client
        self.organization = Organization.objects.create(
            name='Test School', organization_type='educational'
        )
        self.client_obj = Client.objects.create(
            organization=self.organization, client_since=timezone.now().date()
        )

        # Create project
        self.project = Project.objects.create(
            project_name='Test Pilot Project',
            project_code='TPP001',
            client=self.client_obj,
            service_type='operations_system',
            status='testing',
            start_date=timezone.now().date()
        )

        # Create document template
        self.document_template, _ = DocumentTemplate.objects.get_or_create(
            name='Internal Pilot Handover',
            template_type='HANDOVER',
            defaults={
                'content': '<html><body>Internal Handover</body></html>',
                'status': 'PUBLISHED'
            }
        )

        # Create document instance
        self.document_instance = DocumentInstance.objects.create(
            template=self.document_template,
            project=self.project,
            filled_data={
                'project_reference': {
                    'client_school_name': 'Test School',
                    'pilot_start_date': timezone.now().date().isoformat(),
                    'expected_delivery_date': timezone.now().date().isoformat(),
                    'assigned_team_members': ['Staff User', 'Admin User']
                },
                'checklist': {
                    'technical_setup': {
                        'domain_configured': True,
                        'ssl_active': True,
                        'site_load_ok': False
                    }
                }
            },
            created_by=self.staff_user,
            document_title="Internal Handover Document"
        )

        # Create pilot handover
        self.pilot_handover = PilotHandover.objects.create(
            project=self.project,
            document_instance=self.document_instance,
            expected_delivery_date=timezone.now().date(),
            assigned_team_members=['Staff User', 'Admin User'],
            status='draft',
            created_by=self.staff_user
        )

    def test_pilot_handover_creation(self):
        """Test pilot handover creation."""
        self.assertIsNotNone(self.pilot_handover.id)
        self.assertEqual(self.pilot_handover.project, self.project)
        self.assertEqual(self.pilot_handover.document_instance, self.document_instance)
        self.assertEqual(self.pilot_handover.status, 'draft')
        self.assertEqual(self.pilot_handover.created_by, self.staff_user)

    def test_pilot_handover_str(self):
        """Test string representation."""
        expected = f"Handover - {self.project.project_name} (Draft)"
        self.assertEqual(str(self.pilot_handover), expected)

    def test_is_ready_for_handover_property(self):
        """Test is_ready_for_handover property."""
        self.assertFalse(self.pilot_handover.is_ready_for_handover)
        
        self.pilot_handover.status = 'ready_for_review'
        self.assertFalse(self.pilot_handover.is_ready_for_handover)
        
        self.pilot_handover.team_lead_signed = True
        self.assertTrue(self.pilot_handover.is_ready_for_handover)

    def test_completion_percentage_property(self):
        """Test completion_percentage property."""
        # With current test data (2 out of 3 items completed: domain_configured=True, ssl_active=True, site_load_ok=False)
        expected_percentage = int((2 / 3) * 100)  # 66%
        self.assertEqual(self.pilot_handover.completion_percentage, expected_percentage)

    def test_get_checklist_sections_classmethod(self):
        """Test get_checklist_sections class method."""
        sections = PilotHandover.get_checklist_sections()
        self.assertIn('technical_setup', sections)
        self.assertIn('core_pages', sections)
        self.assertIn('content_accuracy', sections)
        self.assertIn('security_compliance', sections)
        self.assertIn('training_handover_prep', sections)
        self.assertIn('final_test_run', sections)

    def test_get_project_reference_data(self):
        """Test getting project reference data."""
        data = self.pilot_handover.get_project_reference_data()
        self.assertEqual(data['client_school_name'], 'Test School')

    def test_get_checklist_data(self):
        """Test getting checklist data."""
        data = self.pilot_handover.get_checklist_data()
        self.assertIn('technical_setup', data)
        self.assertTrue(data['technical_setup']['domain_configured'])

    def test_update_checklist_section(self):
        """Test updating checklist section."""
        new_section_data = {
            'domain_configured': False,
            'ssl_active': False,
            'site_load_ok': True
        }
        self.pilot_handover.update_checklist_section('technical_setup', new_section_data)
        
        data = self.pilot_handover.get_checklist_data()
        self.assertFalse(data['technical_setup']['domain_configured'])
        self.assertTrue(data['technical_setup']['site_load_ok'])

    def test_sign_handover(self):
        """Test signing handover document."""
        signature_data = {
            'name': 'Team Lead', 'signature': 'base64_team_lead_sig', 'date': timezone.now().isoformat()
        }
        
        self.pilot_handover.sign_handover(self.staff_user, signature_data)
        
        self.assertTrue(self.pilot_handover.team_lead_signed)
        self.assertIsNotNone(self.pilot_handover.team_lead_signed_at)
        
        signature_data_stored = self.pilot_handover.get_signature_data()
        self.assertEqual(signature_data_stored['team_lead']['name'], 'Team Lead')

    def test_can_be_signed_by(self):
        """Test can_be_signed_by method."""
        # Staff user can sign (not signed yet)
        self.assertTrue(self.pilot_handover.can_be_signed_by(self.staff_user))
        
        # After signing, can't sign again
        self.pilot_handover.team_lead_signed = True
        self.assertFalse(self.pilot_handover.can_be_signed_by(self.staff_user))

    def test_can_be_reviewed_by(self):
        """Test can_be_reviewed_by method."""
        # Staff can review
        self.assertTrue(self.pilot_handover.can_be_reviewed_by(self.staff_user))

    def test_prepare_pdf_data(self):
        """Test _prepare_pdf_data method."""
        pdf_data = self.pilot_handover._prepare_pdf_data()
        
        self.assertEqual(pdf_data['client_school_name'], self.organization.name)
        self.assertIn('technical_setup', pdf_data)
        self.assertEqual(pdf_data['status'], 'Draft')


class PilotHandoverSerializerTestCase(TestCase):
    """Test cases for PilotHandover serializers."""

    def setUp(self):
        # Create roles and users
        self.staff_role, _ = Role.objects.get_or_create(
            codename='staff', defaults={'name': 'Staff'}
        )
        self.staff_user = User.objects.create_user(
            username='staffuser', email='staff@example.com', password='testpass', employee_id='EMP001'
        )
        self.staff_user.role = self.staff_role
        self.staff_user.save()

        # Create organization, client, and project
        self.organization = Organization.objects.create(
            name='Serializer Test Org', organization_type='educational'
        )
        self.client_obj = Client.objects.create(
            organization=self.organization, client_since=timezone.now().date()
        )
        self.project = Project.objects.create(
            project_name='Serializer Test Project',
            project_code='STP001',
            client=self.client_obj,
            service_type='operations_system',
            status='testing',
            start_date=timezone.now().date()
        )

        # Create document template
        self.document_template, _ = DocumentTemplate.objects.get_or_create(
            name='Internal Pilot Handover',
            template_type='HANDOVER',
            defaults={
                'content': '<html><body>Internal Handover</body></html>',
                'status': 'PUBLISHED'
            }
        )

        # Create document instance and pilot handover
        self.document_instance = DocumentInstance.objects.create(
            template=self.document_template,
            project=self.project,
            filled_data={},
            created_by=self.staff_user,
            document_title="Internal Handover Document"
        )

        self.pilot_handover = PilotHandover.objects.create(
            project=self.project,
            document_instance=self.document_instance,
            expected_delivery_date=timezone.now().date(),
            assigned_team_members=['Staff User'],
            status='draft',
            created_by=self.staff_user
        )

    def test_pilot_handover_serializer(self):
        """Test PilotHandoverSerializer serialization."""
        from apps.core.serializers.pilot_handover import PilotHandoverSerializer
        
        serializer = PilotHandoverSerializer(instance=self.pilot_handover)
        data = serializer.data
        
        self.assertEqual(data['project_name'], self.project.project_name)
        self.assertEqual(data['client_school_name'], self.organization.name)
        self.assertEqual(data['status'], 'draft')
        self.assertIn('is_ready_for_handover', data)
        self.assertIn('completion_percentage', data)

    def test_pilot_handover_create_serializer(self):
        """Test PilotHandoverCreateSerializer."""
        from apps.core.serializers.pilot_handover import PilotHandoverCreateSerializer
        
        data = {
            'project_id': self.project.id,
            'expected_delivery_date': timezone.now().date().isoformat(),
            'assigned_team_members': ['New Team Member']
        }
        
        # Create a mock request object
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/')
        request.user = self.staff_user
        
        serializer = PilotHandoverCreateSerializer(
            data=data, 
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Delete existing handover to allow creation
        self.pilot_handover.delete()
        
        new_handover = serializer.save()
        self.assertIsNotNone(new_handover.id)
        self.assertEqual(new_handover.project, self.project)
        self.assertEqual(new_handover.status, 'draft')


class PilotHandoverAPITestCase(TestCase):
    """Test cases for PilotHandover API endpoints."""

    def setUp(self):
        self.client = APIClient()

        # Create roles
        self.superadmin_role, _ = Role.objects.get_or_create(
            codename='superadmin', defaults={'name': 'Super Admin'}
        )
        self.staff_role, _ = Role.objects.get_or_create(
            codename='staff', defaults={'name': 'Staff'}
        )

        # Create users with permissions
        self.staff_user = User.objects.create_user(
            username='staffuser', email='staff@example.com', password='testpass', employee_id='EMP001'
        )
        self.staff_user.role = self.staff_role
        self.staff_user.save()
        manage_projects_perm, _ = Permission.objects.get_or_create(codename='core.manage_projects')
        self.staff_user.role.permissions.add(manage_projects_perm)

        # Create organization, client, and project
        self.organization = Organization.objects.create(
            name='API Test Org', organization_type='educational'
        )
        self.client_obj = Client.objects.create(
            organization=self.organization, client_since=timezone.now().date()
        )
        self.project = Project.objects.create(
            project_name='API Test Project',
            project_code='ATP001',
            client=self.client_obj,
            service_type='operations_system',
            status='testing',
            start_date=timezone.now().date()
        )

        # Create document template
        self.document_template, _ = DocumentTemplate.objects.get_or_create(
            name='Internal Pilot Handover',
            template_type='HANDOVER',
            defaults={
                'content': '<html><body>Internal Handover</body></html>',
                'status': 'PUBLISHED'
            }
        )

        # Create document instance and pilot handover
        self.document_instance = DocumentInstance.objects.create(
            template=self.document_template,
            project=self.project,
            filled_data={},
            created_by=self.staff_user,
            document_title="API Internal Handover Document"
        )

        self.pilot_handover = PilotHandover.objects.create(
            project=self.project,
            document_instance=self.document_instance,
            expected_delivery_date=timezone.now().date(),
            assigned_team_members=['Staff User'],
            status='draft',
            created_by=self.staff_user
        )

        # Set up URLs
        self.list_url = reverse('pilot-handover-list')
        self.detail_url = reverse('pilot-handover-detail', kwargs={'pk': self.pilot_handover.pk})
        self.sign_url = reverse('pilot-handover-sign-handover', kwargs={'pk': self.pilot_handover.pk})
        self.generate_doc_url = reverse('pilot-handover-generate-handover-document', kwargs={'pk': self.pilot_handover.pk})
        self.statistics_url = reverse('pilot-handover-statistics')

    def test_list_unauthenticated(self):
        """Test listing pilot handovers without authentication."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_authenticated(self):
        """Test listing pilot handovers with authentication."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_pilot_handover(self):
        """Test creating a new pilot handover."""
        self.client.force_authenticate(user=self.staff_user)
        
        # Delete existing handover to allow creation
        self.pilot_handover.delete()
        
        data = {
            'project_id': self.project.id,
            'expected_delivery_date': timezone.now().date().isoformat(),
            'assigned_team_members': ['New Team Member']
        }
        
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify handover was created
        self.assertEqual(PilotHandover.objects.count(), 1)
        handover = PilotHandover.objects.first()
        self.assertEqual(handover.project, self.project)
        self.assertEqual(handover.status, 'draft')

    def test_sign_handover(self):
        """Test signing handover document."""
        self.client.force_authenticate(user=self.staff_user)
        
        data = {
            'signature_data': {
                'name': 'Test Signer',
                'signature': 'base64_test_signature',
                'date': timezone.now().isoformat()
            }
        }
        
        response = self.client.post(self.sign_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify signature was recorded
        self.pilot_handover.refresh_from_db()
        self.assertTrue(self.pilot_handover.team_lead_signed)
        self.assertIsNotNone(self.pilot_handover.team_lead_signed_at)

    def test_generate_handover_document(self):
        """Test generating handover document."""
        self.client.force_authenticate(user=self.staff_user)
        
        response = self.client.post(self.generate_doc_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertGreater(len(response.content), 100)

    def test_update_checklist_section(self):
        """Test updating checklist section."""
        self.client.force_authenticate(user=self.staff_user)
        
        update_url = reverse('pilot-handover-update-checklist-technical-setup', kwargs={'pk': self.pilot_handover.pk})
        data = {
            'section_data': {
                'domain_configured': True,
                'ssl_active': False,
                'site_load_ok': True
            }
        }
        
        response = self.client.post(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify checklist was updated
        self.pilot_handover.refresh_from_db()
        checklist_data = self.pilot_handover.get_checklist_data()
        self.assertTrue(checklist_data['technical_setup']['domain_configured'])
        self.assertFalse(checklist_data['technical_setup']['ssl_active'])

    def test_statistics(self):
        """Test getting pilot handover statistics."""
        self.client.force_authenticate(user=self.staff_user)
        
        response = self.client.get(self.statistics_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertIn('total_handovers', data)
        self.assertIn('status_breakdown', data)
        self.assertIn('approval_breakdown', data)
        self.assertIn('average_completion_percentage', data)

    def test_my_handovers(self):
        """Test getting handovers assigned to current user."""
        self.client.force_authenticate(user=self.staff_user)
        
        url = reverse('pilot-handover-my-handovers')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_pending_review(self):
        """Test getting handovers pending review."""
        self.client.force_authenticate(user=self.staff_user)
        
        # Set status to ready for review
        self.pilot_handover.status = 'ready_for_review'
        self.pilot_handover.save()
        
        url = reverse('pilot-handover-pending-review')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
