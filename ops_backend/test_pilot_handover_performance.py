#!/usr/bin/env python3
"""
Performance test for Pilot Handover workflow.
Tests handover form submission + PDF generation performance.
Target: ≤10 seconds for handover form + PDF generation.
"""
import os
import sys
import django
import time
from decimal import Decimal

# Setup Django
sys.path.append(os.path.join(os.path.dirname(__file__), 'ops_backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ops_backend.settings')
django.setup()

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.core.files.base import ContentFile

from apps.core.models import (
    PilotHandover, Project, Client, Organization, DocumentInstance,
    DocumentTemplate, Role, Permission
)

User = get_user_model()


class PilotHandoverPerformanceTestCase(TestCase):
    """Performance test for Pilot Handover workflow."""

    def setUp(self):
        """Set up test data for performance testing."""
        # Create roles
        self.superadmin_role, _ = Role.objects.get_or_create(
            codename='superadmin', defaults={'name': 'Super Admin'}
        )
        self.staff_role, _ = Role.objects.get_or_create(
            codename='staff', defaults={'name': 'Staff'}
        )

        # Create users
        self.staff_user = User.objects.create_user(
            username='perfuser', email='perf@example.com', password='testpass', employee_id='PERF001'
        )
        self.staff_user.role = self.staff_role
        self.staff_user.save()

        # Create organization and client
        self.organization = Organization.objects.create(
            name='Performance Test School', organization_type='educational'
        )
        self.client_obj = Client.objects.create(
            organization=self.organization, client_since=timezone.now().date()
        )

        # Create project
        self.project = Project.objects.create(
            project_name='Performance Test Project',
            project_code='PERF001',
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
                'content': '''
                <!DOCTYPE html>
                <html>
                <head><title>Internal Handover Document</title></head>
                <body>
                    <h1>Internal Handover Document</h1>
                    <h2>Project: {{ data.project_name }}</h2>
                    <h3>Client: {{ data.client_school_name }}</h3>
                    <p>Delivery Date: {{ data.expected_delivery_date }}</p>
                    <h3>Checklist Completion: {{ data.completion_percentage }}%</h3>
                    {% for section, items in data.checklist.items %}
                        <h4>{{ section|title }}</h4>
                        {% for item, value in items.items %}
                            <p>{{ item|title }}: {% if value %}✓{% else %}✗{% endif %}</p>
                        {% endfor %}
                    {% endfor %}
                    <h3>Team Lead Signature</h3>
                    <p>Name: {{ data.team_lead_name }}</p>
                    <p>Date: {{ data.team_lead_date }}</p>
                    {% if data.team_lead_signature %}
                        <img src="{{ data.team_lead_signature }}" alt="Signature" style="max-width: 200px;">
                    {% endif %}
                </body>
                </html>
                ''',
                'status': 'PUBLISHED'
            }
        )

    def create_full_checklist_data(self):
        """Create comprehensive checklist data for testing."""
        return {
            'technical_setup': {
                'domain_configured': True,
                'ssl_active': True,
                'site_load_ok': True,
                'responsive_design': True,
                'no_broken_links': True,
            },
            'core_pages': {
                'home_completed': True,
                'about_news_added': True,
                'contact_correct': True,
                'portal_links_ok': True,
                'social_media_tested': True,
            },
            'content_accuracy': {
                'logo_correct': True,
                'photos_optimized': True,
                'text_proofread': True,
                'info_matches_official': True,
            },
            'security_compliance': {
                'admin_created': True,
                'restricted_access': True,
                'privacy_statement_included': True,
            },
            'training_handover_prep': {
                'training_scheduled': True,
                'training_materials_ready': True,
                'howto_instructions': True,
                'support_contact_added': True,
            },
            'final_test_run': {
                'browsers_tested': True,
                'forms_tested': True,
                'backup_taken': True,
                'screenshots_captured': True,
            },
        }

    def test_handover_creation_performance(self):
        """Test handover creation performance."""
        print("\n=== Testing Handover Creation Performance ===")
        
        start_time = time.time()
        
        # Create document instance with full data
        filled_data = {
            'expected_delivery_date': timezone.now().date().isoformat(),
            'assigned_team_members': ['Team Member 1', 'Team Member 2', 'Team Member 3'],
            'checklist': self.create_full_checklist_data(),
            'team_lead_signature': {
                'name': 'Performance Test Team Lead',
                'signature': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
                'date': timezone.now().isoformat(),
            }
        }
        
        document_instance = DocumentInstance.objects.create(
            template=self.document_template,
            project=self.project,
            filled_data=filled_data,
            created_by=self.staff_user,
            title="Performance Test Internal Handover Document"
        )
        
        # Create pilot handover
        pilot_handover = PilotHandover.objects.create(
            project=self.project,
            document_instance=document_instance,
            expected_delivery_date=timezone.now().date(),
            assigned_team_members=['Team Member 1', 'Team Member 2', 'Team Member 3'],
            status='draft',
            created_by=self.staff_user
        )
        
        creation_time = time.time() - start_time
        print(f"Handover creation time: {creation_time:.3f} seconds")
        
        # Assert creation time is reasonable
        self.assertLess(creation_time, 2.0, "Handover creation should take less than 2 seconds")
        
        return pilot_handover

    def test_pdf_generation_performance(self):
        """Test PDF generation performance."""
        print("\n=== Testing PDF Generation Performance ===")
        
        # Create handover first
        pilot_handover = self.test_handover_creation_performance()
        
        start_time = time.time()
        
        try:
            # Generate handover document
            document_instance, pdf_bytes = pilot_handover.generate_handover_document(self.staff_user)
            
            generation_time = time.time() - start_time
            print(f"PDF generation time: {generation_time:.3f} seconds")
            print(f"Generated PDF size: {len(pdf_bytes)} bytes")
            
            # Assert generation time meets requirement (≤8 seconds for complex documents)
            self.assertLess(generation_time, 8.0, "PDF generation should take less than 8 seconds")
            
            # Assert PDF was generated successfully
            self.assertIsNotNone(document_instance)
            self.assertGreater(len(pdf_bytes), 1000, "PDF should contain substantial content")
            
            return document_instance, pdf_bytes
            
        except Exception as e:
            generation_time = time.time() - start_time
            print(f"PDF generation failed after {generation_time:.3f} seconds: {e}")
            raise

    def test_complete_workflow_performance(self):
        """Test complete handover workflow performance."""
        print("\n=== Testing Complete Workflow Performance ===")
        
        start_time = time.time()
        
        # Step 1: Create handover
        print("Step 1: Creating handover...")
        step1_start = time.time()
        pilot_handover = self.test_handover_creation_performance()
        step1_time = time.time() - step1_start
        print(f"Step 1 completed in {step1_time:.3f} seconds")
        
        # Step 2: Update checklist sections
        print("Step 2: Updating checklist sections...")
        step2_start = time.time()
        pilot_handover.update_checklist_section('technical_setup', {
            'domain_configured': True,
            'ssl_active': True,
            'site_load_ok': True,
        })
        pilot_handover.update_checklist_section('core_pages', {
            'home_completed': True,
            'about_news_added': True,
        })
        step2_time = time.time() - step2_start
        print(f"Step 2 completed in {step2_time:.3f} seconds")
        
        # Step 3: Sign handover
        print("Step 3: Signing handover...")
        step3_start = time.time()
        signature_data = {
            'name': 'Performance Test Signer',
            'signature': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
            'date': timezone.now().isoformat(),
        }
        pilot_handover.sign_handover(self.staff_user, signature_data)
        step3_time = time.time() - step3_start
        print(f"Step 3 completed in {step3_time:.3f} seconds")
        
        # Step 4: Generate PDF
        print("Step 4: Generating PDF...")
        step4_start = time.time()
        document_instance, pdf_bytes = pilot_handover.generate_handover_document(self.staff_user)
        step4_time = time.time() - step4_start
        print(f"Step 4 completed in {step4_time:.3f} seconds")
        
        total_time = time.time() - start_time
        print(f"\nTotal workflow time: {total_time:.3f} seconds")
        
        # Assert total time meets requirement (≤10 seconds)
        self.assertLess(total_time, 10.0, "Complete workflow should take less than 10 seconds")
        
        # Print performance summary
        print(f"\n=== Performance Summary ===")
        print(f"Handover creation: {step1_time:.3f}s")
        print(f"Checklist updates: {step2_time:.3f}s")
        print(f"Signature capture: {step3_time:.3f}s")
        print(f"PDF generation: {step4_time:.3f}s")
        print(f"Total workflow: {total_time:.3f}s")
        print(f"PDF size: {len(pdf_bytes)} bytes")
        
        return pilot_handover, document_instance, pdf_bytes

    def test_bulk_handover_creation_performance(self):
        """Test creating multiple handovers for bulk performance testing."""
        print("\n=== Testing Bulk Handover Creation Performance ===")
        
        # Create multiple projects for bulk testing
        projects = []
        for i in range(5):
            org = Organization.objects.create(
                name=f'Bulk Test School {i+1}', 
                organization_type='educational'
            )
            client = Client.objects.create(
                organization=org, 
                client_since=timezone.now().date()
            )
            project = Project.objects.create(
                project_name=f'Bulk Test Project {i+1}',
                project_code=f'BULK{i+1:03d}',
                client=client,
                service_type='operations_system',
                status='testing',
                start_date=timezone.now().date()
            )
            projects.append(project)
        
        start_time = time.time()
        handovers = []
        
        for i, project in enumerate(projects):
            # Create document instance
            filled_data = {
                'expected_delivery_date': timezone.now().date().isoformat(),
                'assigned_team_members': [f'Team Member {i+1}', f'Team Member {i+2}'],
                'checklist': self.create_full_checklist_data(),
                'team_lead_signature': {
                    'name': f'Bulk Test Team Lead {i+1}',
                    'signature': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
                    'date': timezone.now().isoformat(),
                }
            }
            
            document_instance = DocumentInstance.objects.create(
                template=self.document_template,
                project=project,
                filled_data=filled_data,
                created_by=self.staff_user,
                title=f"Bulk Test Internal Handover Document {i+1}"
            )
            
            # Create pilot handover
            handover = PilotHandover.objects.create(
                project=project,
                document_instance=document_instance,
                expected_delivery_date=timezone.now().date(),
                assigned_team_members=[f'Team Member {i+1}', f'Team Member {i+2}'],
                status='draft',
                created_by=self.staff_user
            )
            handovers.append(handover)
        
        bulk_time = time.time() - start_time
        print(f"Created {len(handovers)} handovers in {bulk_time:.3f} seconds")
        print(f"Average time per handover: {bulk_time/len(handovers):.3f} seconds")
        
        # Assert bulk creation performance
        self.assertLess(bulk_time, 15.0, "Bulk handover creation should take less than 15 seconds for 5 handovers")
        self.assertLess(bulk_time/len(handovers), 3.0, "Average handover creation should take less than 3 seconds")
        
        return handovers

    def test_checklist_completion_calculation_performance(self):
        """Test checklist completion calculation performance."""
        print("\n=== Testing Checklist Completion Calculation Performance ===")
        
        pilot_handover = self.test_handover_creation_performance()
        
        # Test completion percentage calculation performance
        start_time = time.time()
        
        for _ in range(100):  # Calculate 100 times
            completion_percentage = pilot_handover.completion_percentage
        
        calc_time = time.time() - start_time
        print(f"100 completion calculations in {calc_time:.3f} seconds")
        print(f"Average calculation time: {calc_time/100:.6f} seconds")
        
        # Assert calculation performance
        self.assertLess(calc_time, 1.0, "100 completion calculations should take less than 1 second")
        self.assertLess(calc_time/100, 0.01, "Individual calculation should take less than 10ms")
        
        print(f"Completion percentage: {completion_percentage}%")


def run_performance_tests():
    """Run all performance tests."""
    print("Starting Pilot Handover Performance Tests...")
    print("=" * 50)
    
    # Run tests
    test_case = PilotHandoverPerformanceTestCase()
    test_case.setUp()
    
    try:
        # Test individual components
        test_case.test_handover_creation_performance()
        test_case.test_pdf_generation_performance()
        test_case.test_complete_workflow_performance()
        test_case.test_bulk_handover_creation_performance()
        test_case.test_checklist_completion_calculation_performance()
        
        print("\n" + "=" * 50)
        print("✅ All performance tests passed!")
        print("Pilot Handover workflow meets performance requirements.")
        
    except Exception as e:
        print(f"\n❌ Performance test failed: {e}")
        raise


if __name__ == '__main__':
    run_performance_tests()
