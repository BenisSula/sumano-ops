"""
Unit and API tests for the Pilot Acceptance module.

This module tests the PilotAcceptance model, serializers, API endpoints,
and integration with the unified document system for pilot acceptance workflows.
"""

import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.core.models import (
    PilotAcceptance, Project, Client, Organization, DocumentInstance, 
    DocumentTemplate, Role, Permission, StatusTransition
)
from apps.core.services.pdf_service import PDFGenerationService

User = get_user_model()


class PilotAcceptanceModelTestCase(TestCase):
    """Test cases for the PilotAcceptance model."""

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001'
        )
        self.user.role = Role.objects.get(codename='superadmin')
        self.user.save()

        # Create test organization and client
        self.organization = Organization.objects.create(
            name='Test School for Acceptance',
            organization_type='educational',
            email='admin@testschool.edu'
        )
        self.client_obj = Client.objects.create(
            organization=self.organization,
            client_since=timezone.now().date(),
            relationship_status='active'
        )

        # Create test project
        self.project = Project.objects.create(
            project_name='Test Pilot Project',
            client=self.client_obj,
            service_type='web_development',
            status='testing',
            start_date=timezone.now().date() - timezone.timedelta(days=30)
        )

        # Create document template
        self.template = DocumentTemplate.objects.get(template_type='ACCEPTANCE')

    def test_pilot_acceptance_creation(self):
        """Test creating a PilotAcceptance record."""
        # Create document instance first
        document_instance = DocumentInstance.objects.create(
            template=self.template,
            project=self.project,
            filled_data={
                'checklist': {
                    'digital_gateway_live': True,
                    'mobile_friendly': True,
                    'pages_present': True
                },
                'signatures': {},
                'project_reference': {
                    'school_name': self.organization.name,
                    'pilot_start_date': self.project.start_date.isoformat(),
                    'completion_date': timezone.now().date().isoformat(),
                    'token_payment': '100.00'
                }
            },
            created_by=self.user,
            status='DRAFT'
        )

        # Create pilot acceptance
        acceptance = PilotAcceptance.objects.create(
            project=self.project,
            document_instance=document_instance,
            acceptance_status='accepted',
            completion_date=timezone.now().date(),
            token_payment=100.00,
            created_by=self.user
        )

        self.assertEqual(acceptance.project, self.project)
        self.assertEqual(acceptance.acceptance_status, 'accepted')
        self.assertEqual(acceptance.token_payment, 100.00)
        self.assertFalse(acceptance.is_fully_signed)

    def test_checklist_data_management(self):
        """Test checklist data management methods."""
        # Create document instance and acceptance
        document_instance = DocumentInstance.objects.create(
            template=self.template,
            project=self.project,
            filled_data={'checklist': {}},
            created_by=self.user,
            status='DRAFT'
        )
        
        acceptance = PilotAcceptance.objects.create(
            project=self.project,
            document_instance=document_instance,
            acceptance_status='accepted',
            completion_date=timezone.now().date(),
            created_by=self.user
        )

        # Test updating checklist items
        acceptance.update_checklist_item('digital_gateway_live', True)
        acceptance.update_checklist_item('mobile_friendly', False)

        # Verify updates
        checklist_data = acceptance.get_checklist_data()
        self.assertTrue(checklist_data['digital_gateway_live'])
        self.assertFalse(checklist_data['mobile_friendly'])

        # Test invalid field
        with self.assertRaises(ValueError):
            acceptance.update_checklist_item('invalid_field', True)

    def test_completion_percentage_calculation(self):
        """Test completion percentage calculation."""
        document_instance = DocumentInstance.objects.create(
            template=self.template,
            project=self.project,
            filled_data={
                'checklist': {
                    'digital_gateway_live': True,
                    'mobile_friendly': True,
                    'pages_present': False,
                    'portals_linked': False,
                    'social_media_embedded': False,
                    'logo_colors_correct': False,
                    'photos_content_displayed': False,
                    'layout_design_ok': False,
                    'staff_training_completed': False,
                    'training_materials_provided': False,
                    'no_critical_errors': False,
                    'minor_issues_resolved': False
                }
            },
            created_by=self.user,
            status='DRAFT'
        )

        acceptance = PilotAcceptance.objects.create(
            project=self.project,
            document_instance=document_instance,
            acceptance_status='accepted',
            completion_date=timezone.now().date(),
            created_by=self.user
        )

        # Should be 2 out of 12 items completed (16.7%)
        expected_percentage = round((2 / 12) * 100, 1)
        self.assertEqual(acceptance.completion_percentage, expected_percentage)

    def test_signature_workflow(self):
        """Test signature workflow."""
        document_instance = DocumentInstance.objects.create(
            template=self.template,
            project=self.project,
            filled_data={'signatures': {}},
            created_by=self.user,
            status='DRAFT'
        )

        acceptance = PilotAcceptance.objects.create(
            project=self.project,
            document_instance=document_instance,
            acceptance_status='accepted',
            completion_date=timezone.now().date(),
            created_by=self.user
        )

        # Create school representative user
        school_user = User.objects.create_user(
            username='school_rep',
            email='rep@school.edu',
            password='testpass',
            employee_id='SCH001'
        )
        school_user.role = Role.objects.get(codename='client_contact')
        school_user.save()

        # Test signing permissions
        self.assertTrue(acceptance.can_be_signed_by(school_user))
        self.assertTrue(acceptance.can_be_signed_by(self.user))  # staff

        # Sign as school representative
        signature_data = {
            'name': 'Jane Doe',
            'title': 'Principal',
            'signature': 'base64_signature_data',
            'date': timezone.now().isoformat()
        }
        acceptance.sign_acceptance(school_user, signature_data)

        self.assertTrue(acceptance.school_representative_signed)
        self.assertIsNotNone(acceptance.school_representative_signed_at)
        self.assertFalse(acceptance.is_fully_signed)

        # School rep can no longer sign
        self.assertFalse(acceptance.can_be_signed_by(school_user))

        # Sign as company representative
        company_signature_data = {
            'name': 'John Smith',
            'title': 'Project Manager',
            'signature': 'base64_company_signature',
            'date': timezone.now().isoformat()
        }
        acceptance.sign_acceptance(self.user, company_signature_data)

        self.assertTrue(acceptance.company_representative_signed)
        self.assertIsNotNone(acceptance.company_representative_signed_at)
        self.assertTrue(acceptance.is_fully_signed)

    def test_pdf_data_preparation(self):
        """Test PDF data preparation."""
        document_instance = DocumentInstance.objects.create(
            template=self.template,
            project=self.project,
            filled_data={
                'checklist': {
                    'digital_gateway_live': True,
                    'mobile_friendly': False
                },
                'signatures': {
                    'school_representative': {
                        'name': 'Jane Doe',
                        'title': 'Principal'
                    }
                }
            },
            created_by=self.user,
            status='DRAFT'
        )

        acceptance = PilotAcceptance.objects.create(
            project=self.project,
            document_instance=document_instance,
            acceptance_status='accepted',
            completion_date=timezone.now().date(),
            token_payment=150.00,
            created_by=self.user
        )

        pdf_data = acceptance._prepare_pdf_data()

        # Verify PDF data structure
        self.assertEqual(pdf_data['school_name'], self.organization.name)
        self.assertEqual(pdf_data['acceptance_status'], 'Accepted')
        self.assertEqual(pdf_data['digital_gateway_live'], 'Yes')
        self.assertEqual(pdf_data['mobile_friendly'], 'No')
        self.assertEqual(pdf_data['school_representative_name'], 'Jane Doe')
        self.assertIn('completion_percentage', pdf_data)


class PilotAcceptanceSerializerTestCase(TestCase):
    """Test cases for PilotAcceptance serializers."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001'
        )
        self.user.role = Role.objects.get(codename='superadmin')
        self.user.save()

        self.organization = Organization.objects.create(
            name='Serializer Test School',
            organization_type='educational',
            email='serializer@testschool.edu'
        )
        self.client_obj = Client.objects.create(
            organization=self.organization,
            client_since=timezone.now().date(),
            relationship_status='active'
        )
        self.project = Project.objects.create(
            project_name='Serializer Test Project',
            client=self.client_obj,
            service_type='web_development',
            status='testing',
            start_date=timezone.now().date() - timezone.timedelta(days=30)
        )

    def test_pilot_acceptance_create_serializer(self):
        """Test PilotAcceptanceCreateSerializer."""
        valid_data = {
            'project_id': str(self.project.id),
            'acceptance_status': 'accepted',
            'completion_date': timezone.now().date().isoformat(),
            'token_payment': '200.00',
            'issues_to_resolve': 'No issues',
            'checklist': {
                'digital_gateway_live': True,
                'mobile_friendly': True,
                'pages_present': True
            }
        }

        serializer = PilotAcceptanceCreateSerializer(
            data=valid_data,
            context={'request': type('obj', (object,), {'user': self.user})()}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        acceptance = serializer.save()
        self.assertIsNotNone(acceptance.id)
        self.assertEqual(acceptance.project, self.project)
        self.assertEqual(acceptance.acceptance_status, 'accepted')

    def test_project_validation(self):
        """Test project validation in serializer."""
        # Test invalid project ID
        invalid_data = {
            'project_id': '00000000-0000-0000-0000-000000000000',
            'acceptance_status': 'accepted',
            'completion_date': timezone.now().date().isoformat()
        }

        serializer = PilotAcceptanceCreateSerializer(
            data=invalid_data,
            context={'request': type('obj', (object,), {'user': self.user})()}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('project_id', serializer.errors)

        # Test project in wrong status
        self.project.status = 'development'
        self.project.save()

        valid_data = {
            'project_id': str(self.project.id),
            'acceptance_status': 'accepted',
            'completion_date': timezone.now().date().isoformat()
        }

        serializer = PilotAcceptanceCreateSerializer(
            data=valid_data,
            context={'request': type('obj', (object,), {'user': self.user})()}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('project_id', serializer.errors)


class PilotAcceptanceAPITestCase(TestCase):
    """Test cases for PilotAcceptance API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create user with superadmin role
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001'
        )
        self.user.role = Role.objects.get(codename='superadmin')
        self.user.save()

        # Ensure user has the required permissions
        view_permission, _ = Permission.objects.get_or_create(
            codename='core.view_projects',
            defaults={
                'name': 'View Project Information',
                'description': 'Can view project information'
            }
        )
        manage_permission, _ = Permission.objects.get_or_create(
            codename='core.manage_projects',
            defaults={
                'name': 'Manage Project Information',
                'description': 'Can manage project information'
            }
        )
        self.user.role.permissions.add(view_permission, manage_permission)

        # Create test data
        self.organization = Organization.objects.create(
            name='API Test School',
            organization_type='educational',
            email='api@testschool.edu'
        )
        self.client_obj = Client.objects.create(
            organization=self.organization,
            client_since=timezone.now().date(),
            relationship_status='active'
        )
        self.project = Project.objects.create(
            project_name='API Test Project',
            client=self.client_obj,
            service_type='web_development',
            status='testing',
            start_date=timezone.now().date() - timezone.timedelta(days=30)
        )

        self.list_url = reverse('pilot-acceptance-list')
        self.create_url = reverse('pilot-acceptance-list')

    def test_pilot_acceptance_list_unauthorized(self):
        """Test pilot acceptance list without authentication."""
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pilot_acceptance_list_authorized(self):
        """Test pilot acceptance list with authentication."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_pilot_acceptance_create(self):
        """Test creating a pilot acceptance."""
        self.client.force_authenticate(user=self.user)
        data = {
            'project_id': str(self.project.id),
            'acceptance_status': 'accepted',
            'completion_date': timezone.now().date().isoformat(),
            'token_payment': '300.00',
            'issues_to_resolve': 'All requirements met',
            'checklist': {
                'digital_gateway_live': True,
                'mobile_friendly': True,
                'pages_present': True,
                'portals_linked': True,
                'social_media_embedded': True,
                'logo_colors_correct': True,
                'photos_content_displayed': True,
                'layout_design_ok': True,
                'staff_training_completed': True,
                'training_materials_provided': True,
                'no_critical_errors': True,
                'minor_issues_resolved': True
            }
        }

        response = self.client.post(self.create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PilotAcceptance.objects.count(), 1)
        self.assertEqual(response.data['acceptance_status'], 'accepted')

    def test_pilot_acceptance_statistics(self):
        """Test pilot acceptance statistics endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('pilot-acceptance-statistics'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_acceptances', response.data)
        self.assertIn('acceptance_rate', response.data)

    def test_pilot_acceptance_update_checklist(self):
        """Test updating checklist items."""
        # First create an acceptance
        document_instance = DocumentInstance.objects.create(
            template=DocumentTemplate.objects.get(template_type='ACCEPTANCE'),
            project=self.project,
            filled_data={'checklist': {}},
            created_by=self.user,
            status='DRAFT'
        )
        
        acceptance = PilotAcceptance.objects.create(
            project=self.project,
            document_instance=document_instance,
            acceptance_status='accepted',
            completion_date=timezone.now().date(),
            created_by=self.user
        )

        self.client.force_authenticate(user=self.user)
        update_url = reverse('pilot-acceptance-update-checklist', kwargs={'pk': acceptance.pk})
        
        data = {
            'checklist': {
                'digital_gateway_live': True,
                'mobile_friendly': False,
                'pages_present': True
            }
        }

        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify updates
        acceptance.refresh_from_db()
        checklist_data = acceptance.get_checklist_data()
        self.assertTrue(checklist_data['digital_gateway_live'])
        self.assertFalse(checklist_data['mobile_friendly'])
        self.assertTrue(checklist_data['pages_present'])


class PilotAcceptancePDFIntegrationTestCase(TestCase):
    """Test cases for PDF integration with PilotAcceptance."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='pdfuser',
            email='pdf@example.com',
            password='testpass123',
            employee_id='PDF001'
        )
        self.user.role = Role.objects.get(codename='superadmin')
        self.user.save()

        self.organization = Organization.objects.create(
            name='PDF Test School',
            organization_type='educational',
            email='pdf@testschool.edu'
        )
        self.client_obj = Client.objects.create(
            organization=self.organization,
            client_since=timezone.now().date(),
            relationship_status='active'
        )
        self.project = Project.objects.create(
            project_name='PDF Test Project',
            client=self.client_obj,
            service_type='web_development',
            status='completed',
            start_date=timezone.now().date() - timezone.timedelta(days=60)
        )

    def test_pilot_acceptance_pdf_generation(self):
        """Test PDF generation for pilot acceptance."""
        # Create acceptance with full data
        document_instance = DocumentInstance.objects.create(
            template=DocumentTemplate.objects.get(template_type='ACCEPTANCE'),
            project=self.project,
            filled_data={
                'checklist': {
                    'digital_gateway_live': True,
                    'mobile_friendly': True,
                    'pages_present': True,
                    'portals_linked': True,
                    'social_media_embedded': True,
                    'logo_colors_correct': True,
                    'photos_content_displayed': True,
                    'layout_design_ok': True,
                    'staff_training_completed': True,
                    'training_materials_provided': True,
                    'no_critical_errors': True,
                    'minor_issues_resolved': True
                },
                'signatures': {
                    'school_representative': {
                        'name': 'Jane Doe',
                        'title': 'Principal',
                        'signature': 'base64_signature_data',
                        'date': timezone.now().isoformat()
                    },
                    'company_representative': {
                        'name': 'John Smith',
                        'title': 'Project Manager',
                        'signature': 'base64_company_signature',
                        'date': timezone.now().isoformat()
                    }
                },
                'project_reference': {
                    'school_name': self.organization.name,
                    'pilot_start_date': self.project.start_date.isoformat(),
                    'completion_date': timezone.now().date().isoformat(),
                    'token_payment': '500.00'
                }
            },
            created_by=self.user,
            status='DRAFT'
        )

        acceptance = PilotAcceptance.objects.create(
            project=self.project,
            document_instance=document_instance,
            acceptance_status='accepted',
            completion_date=timezone.now().date(),
            token_payment=500.00,
            created_by=self.user
        )

        # Generate PDF
        try:
            document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
                template_name='Pilot Acceptance Certificate',
                data=acceptance._prepare_pdf_data(),
                user=self.user,
                project=acceptance.project
            )
            self.assertIsNotNone(document_instance)
            self.assertIsNotNone(pdf_bytes)
            self.assertGreater(len(pdf_bytes), 1000)  # PDF should be substantial
            print(f"✅ PDF generated successfully: {len(pdf_bytes)} bytes")
        except Exception as e:
            self.fail(f"PDF generation failed: {e}")
