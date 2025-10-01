#!/usr/bin/env python3
"""
End-to-end integration test for Pilot Handover workflow.
Tests the complete workflow from handover creation to PDF generation.
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

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from apps.core.models import (
    PilotHandover, Project, Client, Organization, DocumentInstance,
    DocumentTemplate, Role, Permission
)

User = get_user_model()


class PilotHandoverIntegrationTestCase(TestCase):
    """End-to-end integration test for Pilot Handover workflow."""

    def setUp(self):
        """Set up test data for integration testing."""
        # Create roles
        self.superadmin_role, _ = Role.objects.get_or_create(
            codename='superadmin', defaults={'name': 'Super Admin'}
        )
        self.staff_role, _ = Role.objects.get_or_create(
            codename='staff', defaults={'name': 'Staff'}
        )

        # Create users
        self.staff_user = User.objects.create_user(
            username='integrationuser', email='integration@example.com', password='testpass', employee_id='INT001'
        )
        self.staff_user.role = self.staff_role
        self.staff_user.save()

        # Create permissions
        manage_projects_perm, _ = Permission.objects.get_or_create(codename='core.manage_projects')
        self.staff_user.role.permissions.add(manage_projects_perm)

        # Create organization and client
        self.organization = Organization.objects.create(
            name='Integration Test School', organization_type='educational'
        )
        self.client_obj = Client.objects.create(
            organization=self.organization, client_since=timezone.now().date()
        )

        # Create project
        self.project = Project.objects.create(
            project_name='Integration Test Project',
            project_code='INT001',
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

        # Set up API client
        self.client = Client()

    def test_complete_handover_workflow(self):
        """Test the complete handover workflow from creation to PDF generation."""
        print("\n=== Testing Complete Pilot Handover Workflow ===")
        
        # Step 1: Login
        print("Step 1: User authentication...")
        login_success = self.client.login(username='integrationuser', password='testpass')
        self.assertTrue(login_success, "User should be able to login")
        
        # Step 2: Create handover via API
        print("Step 2: Creating pilot handover via API...")
        handover_data = {
            'project_id': str(self.project.id),
            'expected_delivery_date': timezone.now().date().isoformat(),
            'assigned_team_members': ['Team Member 1', 'Team Member 2'],
            'checklist': {
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
            },
            'team_lead_signature': {
                'name': 'Integration Test Team Lead',
                'signature': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
                'date': timezone.now().isoformat(),
            }
        }
        
        # Create handover
        response = self.client.post('/api/pilot-handover/', handover_data, content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Handover creation failed: {response.content}")
        
        handover_id = response.json()['id']
        print(f"Handover created with ID: {handover_id}")
        
        # Step 3: Retrieve created handover
        print("Step 3: Retrieving created handover...")
        response = self.client.get(f'/api/pilot-handover/{handover_id}/')
        self.assertEqual(response.status_code, 200, "Should be able to retrieve handover")
        
        handover_data = response.json()
        self.assertEqual(handover_data['project'], self.project.id)
        self.assertEqual(handover_data['status'], 'draft')
        
        # Step 4: Update checklist section
        print("Step 4: Updating checklist section...")
        update_data = {
            'section_data': {
                'domain_configured': False,
                'ssl_active': True,
                'site_load_ok': False,
            }
        }
        
        response = self.client.post(
            f'/api/pilot-handover/{handover_id}/update_checklist_technical_setup/', 
            update_data, 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200, "Should be able to update checklist")
        
        # Step 5: Sign handover
        print("Step 5: Signing handover...")
        signature_data = {
            'signature_data': {
                'name': 'Integration Test Signer',
                'signature': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
                'date': timezone.now().isoformat(),
            }
        }
        
        response = self.client.post(
            f'/api/pilot-handover/{handover_id}/sign_handover/', 
            signature_data, 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200, "Should be able to sign handover")
        
        # Verify signature was recorded
        response = self.client.get(f'/api/pilot-handover/{handover_id}/')
        handover_data = response.json()
        self.assertTrue(handover_data['team_lead_signed'])
        
        # Step 6: Generate PDF document
        print("Step 6: Generating PDF document...")
        response = self.client.post(f'/api/pilot-handover/{handover_id}/generate_handover_document/')
        self.assertEqual(response.status_code, 200, "Should be able to generate PDF")
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertGreater(len(response.content), 1000, "PDF should contain substantial content")
        
        # Step 7: Verify database state
        print("Step 7: Verifying database state...")
        handover = PilotHandover.objects.get(id=handover_id)
        self.assertTrue(handover.team_lead_signed)
        self.assertIsNotNone(handover.team_lead_signed_at)
        self.assertEqual(handover.status, 'draft')
        
        # Verify document instance was created
        self.assertIsNotNone(handover.document_instance)
        self.assertIsNotNone(handover.document_instance.generated_pdf)
        
        print("✅ Complete handover workflow test passed!")

    def test_handover_statistics_api(self):
        """Test handover statistics API endpoint."""
        print("\n=== Testing Handover Statistics API ===")
        
        # Login
        self.client.login(username='integrationuser', password='testpass')
        
        # Create multiple handovers for statistics
        for i in range(3):
            handover_data = {
                'project_id': str(self.project.id),
                'expected_delivery_date': timezone.now().date().isoformat(),
                'assigned_team_members': [f'Team Member {i+1}'],
                'checklist': {
                    'technical_setup': {
                        'domain_configured': i % 2 == 0,
                        'ssl_active': True,
                        'site_load_ok': True,
                    }
                }
            }
            
            response = self.client.post('/api/pilot-handover/', handover_data, content_type='application/json')
            self.assertEqual(response.status_code, 201)
        
        # Get statistics
        response = self.client.get('/api/pilot-handover/statistics/')
        self.assertEqual(response.status_code, 200)
        
        stats = response.json()
        self.assertIn('total_handovers', stats)
        self.assertIn('status_breakdown', stats)
        self.assertIn('approval_breakdown', stats)
        self.assertIn('average_completion_percentage', stats)
        
        self.assertEqual(stats['total_handovers'], 3)
        
        print("✅ Statistics API test passed!")

    def test_handover_permissions(self):
        """Test handover permissions and access control."""
        print("\n=== Testing Handover Permissions ===")
        
        # Test unauthenticated access
        response = self.client.get('/api/pilot-handover/')
        self.assertEqual(response.status_code, 401, "Unauthenticated users should be denied access")
        
        # Test authenticated access
        self.client.login(username='integrationuser', password='testpass')
        response = self.client.get('/api/pilot-handover/')
        self.assertEqual(response.status_code, 200, "Authenticated users should have access")
        
        print("✅ Permissions test passed!")

    def test_handover_data_relationships(self):
        """Test that handover data relationships work correctly."""
        print("\n=== Testing Data Relationships ===")
        
        # Create handover with full data
        handover_data = {
            'project_id': str(self.project.id),
            'expected_delivery_date': timezone.now().date().isoformat(),
            'assigned_team_members': ['Team Member A', 'Team Member B'],
            'checklist': {
                'technical_setup': {
                    'domain_configured': True,
                    'ssl_active': False,
                    'site_load_ok': True,
                }
            }
        }
        
        self.client.login(username='integrationuser', password='testpass')
        response = self.client.post('/api/pilot-handover/', handover_data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        handover_id = response.json()['id']
        
        # Retrieve and verify relationships
        response = self.client.get(f'/api/pilot-handover/{handover_id}/')
        handover_data = response.json()
        
        # Verify project relationship
        self.assertEqual(handover_data['project'], self.project.id)
        self.assertEqual(handover_data['project_name'], self.project.project_name)
        self.assertEqual(handover_data['client_school_name'], self.organization.name)
        
        # Verify document instance relationship
        self.assertIsNotNone(handover_data['document_instance'])
        self.assertIsNotNone(handover_data['document_instance_detail'])
        
        # Verify created_by relationship
        self.assertEqual(handover_data['created_by'], self.staff_user.id)
        self.assertEqual(handover_data['created_by_username'], self.staff_user.username)
        
        print("✅ Data relationships test passed!")


def run_integration_tests():
    """Run all integration tests."""
    print("Starting Pilot Handover Integration Tests...")
    print("=" * 50)
    
    # Run tests
    test_case = PilotHandoverIntegrationTestCase()
    test_case.setUp()
    
    try:
        test_case.test_complete_handover_workflow()
        test_case.test_handover_statistics_api()
        test_case.test_handover_permissions()
        test_case.test_handover_data_relationships()
        
        print("\n" + "=" * 50)
        print("✅ All integration tests passed!")
        print("Pilot Handover workflow is fully functional.")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        raise


if __name__ == '__main__':
    run_integration_tests()
