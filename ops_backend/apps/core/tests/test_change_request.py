"""
Test cases for Change Request functionality.
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
    ChangeRequest, Project, Client, Organization, DocumentInstance,
    DocumentTemplate, Role, Permission
)

User = get_user_model()


class ChangeRequestModelTestCase(TestCase):
    """Test cases for the ChangeRequest model."""

    def setUp(self):
        # Create roles
        self.superadmin_role, _ = Role.objects.get_or_create(
            codename='superadmin', defaults={'name': 'Super Admin'}
        )
        self.staff_role, _ = Role.objects.get_or_create(
            codename='staff', defaults={'name': 'Staff'}
        )
        self.client_contact_role, _ = Role.objects.get_or_create(
            codename='client_contact', defaults={'name': 'Client Contact'}
        )

        # Create users
        self.staff_user = User.objects.create_user(
            username='staffuser', email='staff@example.com', password='testpass', employee_id='EMP001'
        )
        self.staff_user.role = self.staff_role
        self.staff_user.save()

        self.client_user = User.objects.create_user(
            username='clientuser', email='client@example.com', password='testpass', employee_id='CLI001'
        )
        self.client_user.role = self.client_contact_role
        self.client_user.save()

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
            status='development',
            start_date=timezone.now().date()
        )

        # Create document template
        self.document_template, _ = DocumentTemplate.objects.get_or_create(
            name='Change Request Authorization',
            template_type='CHANGE',
            defaults={
                'content': '<html><body>Change Request</body></html>',
                'status': 'PUBLISHED'
            }
        )

        # Create document instance
        self.document_instance = DocumentInstance.objects.create(
            template=self.document_template,
            project=self.project,
            filled_data={
                'change_request': {
                    'description': 'Test change description',
                    'reason': 'Test change reason'
                },
                'impact_assessment': {
                    'no_additional_cost': False,
                    'requires_additional_effort': True,
                    'estimated_time': 5,
                    'estimated_cost': '1000.00'
                }
            },
            created_by=self.staff_user,
            title="Change Request Document"
        )

        # Create change request
        self.change_request = ChangeRequest.objects.create(
            project=self.project,
            document_instance=self.document_instance,
            request_date=timezone.now().date(),
            reference_agreement='Test Agreement',
            status='draft',
            created_by=self.staff_user
        )

    def test_change_request_creation(self):
        """Test change request creation."""
        self.assertIsNotNone(self.change_request.id)
        self.assertEqual(self.change_request.project, self.project)
        self.assertEqual(self.change_request.document_instance, self.document_instance)
        self.assertEqual(self.change_request.status, 'draft')
        self.assertEqual(self.change_request.created_by, self.staff_user)

    def test_change_request_str(self):
        """Test string representation."""
        expected = f"Change Request - {self.project.project_name} (Draft)"
        self.assertEqual(str(self.change_request), expected)

    def test_is_fully_signed_property(self):
        """Test is_fully_signed property."""
        self.assertFalse(self.change_request.is_fully_signed)
        
        self.change_request.client_rep_signed = True
        self.assertFalse(self.change_request.is_fully_signed)
        
        self.change_request.provider_signed = True
        self.assertTrue(self.change_request.is_fully_signed)

    def test_is_ready_for_client_decision_property(self):
        """Test is_ready_for_client_decision property."""
        self.assertFalse(self.change_request.is_ready_for_client_decision)
        
        self.change_request.status = 'impact_assessed'
        self.change_request.assessed_by = self.staff_user
        self.assertTrue(self.change_request.is_ready_for_client_decision)

    def test_get_change_request_data(self):
        """Test getting change request data."""
        data = self.change_request.get_change_request_data()
        self.assertEqual(data['description'], 'Test change description')
        self.assertEqual(data['reason'], 'Test change reason')

    def test_get_impact_assessment_data(self):
        """Test getting impact assessment data."""
        data = self.change_request.get_impact_assessment_data()
        self.assertFalse(data['no_additional_cost'])
        self.assertTrue(data['requires_additional_effort'])
        self.assertEqual(data['estimated_time'], 5)
        self.assertEqual(data['estimated_cost'], '1000.00')

    def test_update_change_request_data(self):
        """Test updating change request data."""
        self.change_request.update_change_request_data('description', 'Updated description')
        
        data = self.change_request.get_change_request_data()
        self.assertEqual(data['description'], 'Updated description')

    def test_update_impact_assessment(self):
        """Test updating impact assessment."""
        assessment_data = {
            'no_additional_cost': True,
            'requires_additional_effort': False,
            'estimated_time': 0,
            'estimated_cost': '0.00'
        }
        
        self.change_request.update_impact_assessment(assessment_data)
        
        data = self.change_request.get_impact_assessment_data()
        self.assertTrue(data['no_additional_cost'])
        self.assertFalse(data['requires_additional_effort'])
        self.assertEqual(data['estimated_time'], 0)
        
        # Check status was updated
        self.change_request.refresh_from_db()
        self.assertEqual(self.change_request.status, 'impact_assessed')

    def test_sign_change_request_client_rep(self):
        """Test signing change request as client representative."""
        signature_data = {
            'name': 'Client Rep', 'signature': 'base64_client_sig', 'date': timezone.now().isoformat()
        }
        
        self.change_request.sign_change_request(self.client_user, signature_data)
        
        self.assertTrue(self.change_request.client_rep_signed)
        self.assertIsNotNone(self.change_request.client_rep_signed_at)
        
        signature_data_stored = self.change_request.get_signature_data()
        self.assertEqual(signature_data_stored['client_representative']['name'], 'Client Rep')

    def test_sign_change_request_provider_rep(self):
        """Test signing change request as provider representative."""
        signature_data = {
            'name': 'Provider Rep', 'signature': 'base64_provider_sig', 'date': timezone.now().isoformat()
        }
        
        self.change_request.sign_change_request(self.staff_user, signature_data)
        
        self.assertTrue(self.change_request.provider_signed)
        self.assertIsNotNone(self.change_request.provider_signed_at)
        
        signature_data_stored = self.change_request.get_signature_data()
        self.assertEqual(signature_data_stored['provider_representative']['name'], 'Provider Rep')

    def test_can_be_signed_by(self):
        """Test can_be_signed_by method."""
        # Client user can sign (not signed yet)
        self.assertTrue(self.change_request.can_be_signed_by(self.client_user))
        
        # Staff user can sign (not signed yet)
        self.assertTrue(self.change_request.can_be_signed_by(self.staff_user))
        
        # After client signs, client can't sign again
        self.change_request.client_rep_signed = True
        self.assertFalse(self.change_request.can_be_signed_by(self.client_user))
        self.assertTrue(self.change_request.can_be_signed_by(self.staff_user))
        
        # After both sign, neither can sign again
        self.change_request.provider_signed = True
        self.assertFalse(self.change_request.can_be_signed_by(self.client_user))
        self.assertFalse(self.change_request.can_be_signed_by(self.staff_user))

    def test_can_be_assessed_by(self):
        """Test can_be_assessed_by method."""
        # Staff can assess
        self.assertTrue(self.change_request.can_be_assessed_by(self.staff_user))
        
        # Client cannot assess
        self.assertFalse(self.change_request.can_be_assessed_by(self.client_user))

    def test_prepare_pdf_data(self):
        """Test _prepare_pdf_data method."""
        pdf_data = self.change_request._prepare_pdf_data()
        
        self.assertEqual(pdf_data['project_title'], self.project.project_name)
        self.assertEqual(pdf_data['client_name'], self.organization.name)
        self.assertEqual(pdf_data['description'], 'Test change description')
        self.assertEqual(pdf_data['reason'], 'Test change reason')
        self.assertEqual(pdf_data['estimated_time'], 5)
        self.assertEqual(pdf_data['estimated_cost'], '1000.00')


class ChangeRequestSerializerTestCase(TestCase):
    """Test cases for ChangeRequest serializers."""

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
            status='development',
            start_date=timezone.now().date()
        )

        # Create document template
        self.document_template, _ = DocumentTemplate.objects.get_or_create(
            name='Change Request Authorization',
            template_type='CHANGE',
            defaults={
                'content': '<html><body>Change Request</body></html>',
                'status': 'PUBLISHED'
            }
        )

        # Create document instance and change request
        self.document_instance = DocumentInstance.objects.create(
            template=self.document_template,
            project=self.project,
            filled_data={},
            created_by=self.staff_user,
            title="Change Request Document"
        )

        self.change_request = ChangeRequest.objects.create(
            project=self.project,
            document_instance=self.document_instance,
            request_date=timezone.now().date(),
            status='draft',
            created_by=self.staff_user
        )

    def test_change_request_serializer(self):
        """Test ChangeRequestSerializer serialization."""
        from apps.core.serializers.change_request import ChangeRequestSerializer
        
        serializer = ChangeRequestSerializer(instance=self.change_request)
        data = serializer.data
        
        self.assertEqual(data['project_name'], self.project.project_name)
        self.assertEqual(data['client_name'], self.organization.name)
        self.assertEqual(data['status'], 'draft')
        self.assertIn('is_fully_signed', data)
        self.assertIn('is_ready_for_client_decision', data)

    def test_change_request_create_serializer(self):
        """Test ChangeRequestCreateSerializer."""
        from apps.core.serializers.change_request import ChangeRequestCreateSerializer
        
        data = {
            'project_id': self.project.id,
            'request_date': timezone.now().date().isoformat(),
            'reference_agreement': 'Test Agreement',
            'change_request': {
                'description': 'Test change description',
                'reason': 'Test change reason'
            }
        }
        
        serializer = ChangeRequestCreateSerializer(
            data=data, 
            context={'request': self.client.request()}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Delete existing change request to avoid conflicts
        self.change_request.delete()
        
        new_change_request = serializer.save()
        self.assertIsNotNone(new_change_request.id)
        self.assertEqual(new_change_request.project, self.project)
        self.assertEqual(new_change_request.status, 'submitted')


class ChangeRequestAPITestCase(TestCase):
    """Test cases for ChangeRequest API endpoints."""

    def setUp(self):
        self.client = APIClient()

        # Create roles
        self.superadmin_role, _ = Role.objects.get_or_create(
            codename='superadmin', defaults={'name': 'Super Admin'}
        )
        self.staff_role, _ = Role.objects.get_or_create(
            codename='staff', defaults={'name': 'Staff'}
        )
        self.client_contact_role, _ = Role.objects.get_or_create(
            codename='client_contact', defaults={'name': 'Client Contact'}
        )

        # Create users with permissions
        self.staff_user = User.objects.create_user(
            username='staffuser', email='staff@example.com', password='testpass', employee_id='EMP001'
        )
        self.staff_user.role = self.staff_role
        self.staff_user.save()
        manage_projects_perm, _ = Permission.objects.get_or_create(codename='core.manage_projects')
        self.staff_user.role.permissions.add(manage_projects_perm)

        self.client_user = User.objects.create_user(
            username='clientuser', email='client@example.com', password='testpass', employee_id='CLI001'
        )
        self.client_user.role = self.client_contact_role
        self.client_user.save()
        view_projects_perm, _ = Permission.objects.get_or_create(codename='core.view_projects')
        self.client_user.role.permissions.add(view_projects_perm)

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
            status='development',
            start_date=timezone.now().date()
        )

        # Create document template
        self.document_template, _ = DocumentTemplate.objects.get_or_create(
            name='Change Request Authorization',
            template_type='CHANGE',
            defaults={
                'content': '<html><body>Change Request</body></html>',
                'status': 'PUBLISHED'
            }
        )

        # Create document instance and change request
        self.document_instance = DocumentInstance.objects.create(
            template=self.document_template,
            project=self.project,
            filled_data={},
            created_by=self.staff_user,
            title="API Change Request Document"
        )

        self.change_request = ChangeRequest.objects.create(
            project=self.project,
            document_instance=self.document_instance,
            request_date=timezone.now().date(),
            status='draft',
            created_by=self.staff_user
        )

        # Set up URLs
        self.list_url = reverse('change-request-list')
        self.detail_url = reverse('change-request-detail', kwargs={'pk': self.change_request.pk})
        self.update_impact_url = reverse('change-request-update-impact-assessment', kwargs={'pk': self.change_request.pk})
        self.sign_url = reverse('change-request-sign-change-request', kwargs={'pk': self.change_request.pk})
        self.generate_doc_url = reverse('change-request-generate-authorization-document', kwargs={'pk': self.change_request.pk})
        self.statistics_url = reverse('change-request-statistics')

    def test_list_unauthenticated(self):
        """Test listing change requests without authentication."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_authenticated(self):
        """Test listing change requests with authentication."""
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_change_request(self):
        """Test creating a new change request."""
        self.client.force_authenticate(user=self.staff_user)
        
        # Delete existing change request to allow creation
        self.change_request.delete()
        
        data = {
            'project_id': self.project.id,
            'request_date': timezone.now().date().isoformat(),
            'reference_agreement': 'Test Agreement',
            'change_request': {
                'description': 'API test change description',
                'reason': 'API test change reason'
            }
        }
        
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify change request was created
        self.assertEqual(ChangeRequest.objects.count(), 1)
        change_request = ChangeRequest.objects.first()
        self.assertEqual(change_request.project, self.project)
        self.assertEqual(change_request.status, 'submitted')

    def test_update_impact_assessment(self):
        """Test updating impact assessment."""
        self.client.force_authenticate(user=self.staff_user)
        
        data = {
            'impact_assessment': {
                'no_additional_cost': False,
                'requires_additional_effort': True,
                'estimated_time': 3,
                'estimated_cost': '500.00'
            }
        }
        
        response = self.client.post(self.update_impact_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify impact assessment was updated
        self.change_request.refresh_from_db()
        self.assertEqual(self.change_request.status, 'impact_assessed')
        self.assertEqual(self.change_request.assessed_by, self.staff_user)
        
        impact_data = self.change_request.get_impact_assessment_data()
        self.assertEqual(impact_data['estimated_time'], 3)
        self.assertEqual(impact_data['estimated_cost'], '500.00')

    def test_sign_change_request(self):
        """Test signing change request."""
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
        self.change_request.refresh_from_db()
        self.assertTrue(self.change_request.provider_signed)
        self.assertIsNotNone(self.change_request.provider_signed_at)

    def test_generate_authorization_document(self):
        """Test generating authorization document."""
        self.client.force_authenticate(user=self.staff_user)
        
        response = self.client.post(self.generate_doc_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertGreater(len(response.content), 100)

    def test_statistics(self):
        """Test getting change request statistics."""
        self.client.force_authenticate(user=self.staff_user)
        
        response = self.client.get(self.statistics_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertIn('total_requests', data)
        self.assertIn('status_breakdown', data)
        self.assertIn('decision_breakdown', data)
        self.assertIn('approval_rate', data)

    def test_pending_assessment(self):
        """Test getting change requests pending assessment."""
        self.client.force_authenticate(user=self.staff_user)
        
        # Set status to submitted
        self.change_request.status = 'submitted'
        self.change_request.save()
        
        url = reverse('change-request-pending-assessment')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_pending_client_decision(self):
        """Test getting change requests pending client decision."""
        self.client.force_authenticate(user=self.client_user)
        
        # Set status to impact_assessed
        self.change_request.status = 'impact_assessed'
        self.change_request.assessed_by = self.staff_user
        self.change_request.save()
        
        url = reverse('change-request-pending-client-decision')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
