"""
Unit tests for document models and PDF generation service.

This module tests the unified document engine functionality including
template management, PDF generation, and document instances.
"""

import json
import time
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.core.models import (
    DocumentTemplate, DocumentInstance, Project, Client, Organization, Contact, Role
)
from apps.core.services.pdf_service import PDFGenerationService

User = get_user_model()


class DocumentTemplateTestCase(TestCase):
    """Test cases for DocumentTemplate model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001'
        )
        
        self.template = DocumentTemplate.objects.create(
            name='Test Template',
            description='A test template',
            template_type='INTAKE',
            content='<html><body><h1>{{ data.title }}</h1></body></html>',
            status='PUBLISHED',
            required_fields=['title'],
            optional_fields=['subtitle'],
            created_by=self.user
        )

    def test_template_creation(self):
        """Test template creation."""
        self.assertEqual(self.template.name, 'Test Template')
        self.assertEqual(self.template.template_type, 'INTAKE')
        self.assertEqual(self.template.status, 'PUBLISHED')
        self.assertTrue(self.template.is_published())

    def test_template_validation(self):
        """Test template data validation."""
        # Valid data
        valid_data = {'title': 'Test Title'}
        is_valid, missing = self.template.validate_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(missing), 0)

        # Invalid data - missing required field
        invalid_data = {'subtitle': 'Test Subtitle'}
        is_valid, missing = self.template.validate_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn('title', missing)

    def test_template_fields(self):
        """Test template field retrieval."""
        fields = self.template.get_all_fields()
        self.assertEqual(fields['required'], ['title'])
        self.assertEqual(fields['optional'], ['subtitle'])

    def test_template_str_representation(self):
        """Test string representation."""
        expected = 'Test Template v1.0 (INTAKE)'
        self.assertEqual(str(self.template), expected)


class DocumentInstanceTestCase(TestCase):
    """Test cases for DocumentInstance model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123',
            employee_id='EMP002'
        )
        
        self.template = DocumentTemplate.objects.create(
            name='Test Template',
            template_type='INTAKE',
            content='<html><body><h1>{{ data.title }}</h1></body></html>',
            status='PUBLISHED',
            created_by=self.user
        )

        # Create organization and client for project
        self.organization = Organization.objects.create(
            name='Test Organization',
            organization_type='business'
        )
        
        self.contact = Contact.objects.create(
            organization=self.organization,
            first_name='John',
            last_name='Doe',
            email='john@testorg.com',
            phone='+1234567890'
        )
        
        self.client = Client.objects.create(
            organization=self.organization,
            client_since=timezone.now().date(),
            relationship_status='active'
        )
        
        self.project = Project.objects.create(
            project_name='Test Project',
            client=self.client,
            service_type='web_development',
            status='planning',
            description='Test project description',
            start_date=timezone.now().date()
        )

        self.document = DocumentInstance.objects.create(
            template=self.template,
            project=self.project,
            filled_data={'title': 'Test Document'},
            document_title='Test Document Title',
            document_number='DOC-001',
            created_by=self.user
        )

    def test_document_creation(self):
        """Test document instance creation."""
        self.assertEqual(self.document.document_title, 'Test Document Title')
        self.assertEqual(self.document.status, 'GENERATED')
        self.assertFalse(self.document.is_signed())

    def test_document_signing(self):
        """Test document signing functionality."""
        # Should not be able to sign without PDF
        self.assertFalse(self.document.can_be_signed())
        
        # Add a PDF file
        pdf_content = b'%PDF-1.4 fake pdf content'
        self.document.generated_pdf.save(
            'test.pdf',
            ContentFile(pdf_content),
            save=True
        )
        
        # Now should be able to sign
        self.assertTrue(self.document.can_be_signed())
        
        # Sign the document
        self.document.sign(self.user)
        
        # Check signing results
        self.assertTrue(self.document.is_signed())
        self.assertEqual(self.document.status, 'SIGNED')
        self.assertEqual(self.document.signed_by, self.user)

    def test_document_file_operations(self):
        """Test document file operations."""
        # Test without file
        self.assertEqual(self.document.get_file_size(), 0)
        self.assertIsNone(self.document.get_file_url())
        
        # Test with file
        pdf_content = b'%PDF-1.4 fake pdf content'
        self.document.generated_pdf.save(
            'test.pdf',
            ContentFile(pdf_content),
            save=True
        )
        
        self.assertEqual(self.document.get_file_size(), len(pdf_content))
        self.assertIsNotNone(self.document.get_file_url())

    def test_document_str_representation(self):
        """Test string representation."""
        expected = 'Test Document Title - Test Project'
        self.assertEqual(str(self.document), expected)


class PDFGenerationServiceTestCase(TestCase):
    """Test cases for PDFGenerationService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='testpass123',
            employee_id='EMP003'
        )
        
        self.template = DocumentTemplate.objects.create(
            name='Test Template',
            template_type='INTAKE',
            content='<html><body><h1>{{ data.title }}</h1><p>Generated by {{ system.company }}</p></body></html>',
            status='PUBLISHED',
            required_fields=['title'],
            created_by=self.user
        )

        # Create project
        self.organization = Organization.objects.create(
            name='Test Organization',
            organization_type='business'
        )
        
        self.contact = Contact.objects.create(
            organization=self.organization,
            first_name='John',
            last_name='Doe',
            email='john@testorg.com'
        )
        
        self.client = Client.objects.create(
            organization=self.organization,
            client_since=timezone.now().date()
        )
        
        self.project = Project.objects.create(
            project_name='Test Project',
            client=self.client,
            service_type='web_development',
            status='planning',
            description='Test project description',
            start_date=timezone.now().date()
        )

    def test_generate_from_template_success(self):
        """Test successful PDF generation."""
        data = {'title': 'Test Document Title'}
        
        document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
            template_name='Test Template',
            data=data,
            user=self.user,
            project=self.project
        )
        
        # Check document instance
        self.assertIsInstance(document_instance, DocumentInstance)
        self.assertEqual(document_instance.template, self.template)
        self.assertEqual(document_instance.project, self.project)
        self.assertEqual(document_instance.filled_data, data)
        self.assertEqual(document_instance.created_by, self.user)
        
        # Check PDF content (placeholder for now)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertIn(b'Test Document Title', pdf_bytes)

    def test_generate_from_template_validation_failure(self):
        """Test PDF generation with invalid data."""
        data = {}  # Missing required field 'title'
        
        with self.assertRaises(ValueError) as context:
            PDFGenerationService.generate_from_template(
                template_name='Test Template',
                data=data,
                user=self.user,
                project=self.project
            )
        
        self.assertIn('Missing required fields', str(context.exception))

    def test_generate_from_template_not_found(self):
        """Test PDF generation with non-existent template."""
        data = {'title': 'Test Title'}
        
        with self.assertRaises(ValueError) as context:
            PDFGenerationService.generate_from_template(
                template_name='Non-existent Template',
                data=data,
                user=self.user,
                project=self.project
            )
        
        self.assertIn('Published template not found', str(context.exception))

    def test_validate_required_fields(self):
        """Test field validation."""
        # Valid data
        is_valid, missing = PDFGenerationService.validate_required_fields(
            self.template, {'title': 'Test Title'}
        )
        self.assertTrue(is_valid)
        self.assertEqual(len(missing), 0)
        
        # Invalid data
        is_valid, missing = PDFGenerationService.validate_required_fields(
            self.template, {}
        )
        self.assertFalse(is_valid)
        self.assertIn('title', missing)

    def test_store_audited_copy(self):
        """Test storing audited PDF copy."""
        pdf_bytes = b'%PDF-1.4 fake pdf content'
        metadata = {'template_name': 'Test Template', 'template_type': 'INTAKE'}
        
        file_path = PDFGenerationService.store_audited_copy(
            pdf_bytes=pdf_bytes,
            metadata=metadata,
            user=self.user
        )
        
        self.assertIsInstance(file_path, str)
        self.assertIn('audit_', file_path)
        self.assertIn('.pdf', file_path)

    def test_performance_statistics(self):
        """Test performance statistics retrieval."""
        stats = PDFGenerationService.get_performance_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_documents', stats)
        self.assertIn('performance_thresholds', stats)
        self.assertIsInstance(stats['performance_thresholds'], dict)


class DocumentAPITestCase(TestCase):
    """Test cases for document API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser4',
            email='test4@example.com',
            password='testpass123',
            employee_id='EMP004'
        )
        # Assign superadmin role to have all permissions
        self.user.role = Role.objects.get(codename='superadmin')
        self.user.save()
        
        self.template = DocumentTemplate.objects.create(
            name='Test Template',
            template_type='INTAKE',
            content='<html><body><h1>{{ data.title }}</h1></body></html>',
            status='PUBLISHED',
            required_fields=['title'],
            created_by=self.user
        )

        # Create project
        self.organization = Organization.objects.create(
            name='Test Organization',
            organization_type='business'
        )
        
        self.contact = Contact.objects.create(
            organization=self.organization,
            first_name='John',
            last_name='Doe',
            email='john@testorg.com'
        )
        
        self.client_obj = Client.objects.create(
            organization=self.organization,
            client_since=timezone.now().date()
        )
        
        self.project = Project.objects.create(
            project_name='Test Project',
            client=self.client_obj,
            service_type='web_development',
            status='planning',
            description='Test project description',
            start_date=timezone.now().date()
        )

    def test_template_list_unauthorized(self):
        """Test template list without authentication."""
        response = self.client.get('/api/documents/templates/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_template_list_authorized(self):
        """Test template list with authentication."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/documents/templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data.get('results', [])), 1)
        # Check that our test template is in the results
        template_names = [t.get('name') for t in response.data.get('results', [])]
        self.assertIn('Test Template', template_names)

    def test_template_list_by_type(self):
        """Test template list filtered by type."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/documents/templates/?type=INTAKE')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data.get('results', [])), 1)
        # Check that our test template is in the filtered results
        template_names = [t.get('name') for t in response.data.get('results', [])]
        self.assertIn('Test Template', template_names)

    def test_generate_document_success(self):
        """Test successful document generation via API."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'template_name': 'Test Template',
            'project_id': str(self.project.id),
            'data': {'title': 'API Generated Document'}
        }
        
        response = self.client.post('/api/documents/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check response data
        self.assertIn('id', response.data)
        self.assertEqual(response.data['document_title'], 'Test Template - API Generated Document - Test Project')
        self.assertIn('document_number', response.data)

    def test_generate_document_validation_failure(self):
        """Test document generation with invalid data."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'template_name': 'Test Template',
            'project_id': str(self.project.id),
            'data': {}  # Missing required field
        }
        
        response = self.client.post('/api/documents/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_document_statistics(self):
        """Test document statistics endpoint."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/documents/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertIn('total_templates', response.data)
        self.assertIn('total_documents', response.data)
        self.assertIn('performance_thresholds', response.data)


class DocumentPerformanceTestCase(TestCase):
    """Test cases for document generation performance."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser5',
            email='test5@example.com',
            password='testpass123',
            employee_id='EMP005'
        )
        
        # Create a simple template for performance testing
        self.simple_template = DocumentTemplate.objects.create(
            name='Simple Template',
            template_type='INTAKE',
            content='<html><body><h1>{{ data.title }}</h1></body></html>',
            status='PUBLISHED',
            required_fields=['title'],
            created_by=self.user
        )

    def test_simple_document_performance(self):
        """Test performance of simple document generation."""
        data = {'title': 'Performance Test Document'}
        
        start_time = time.time()
        
        document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
            template_name='Simple Template',
            data=data,
            user=self.user
        )
        
        generation_time = time.time() - start_time
        
        # Should complete within 3 seconds for simple documents
        self.assertLess(generation_time, 3.0)
        self.assertIsInstance(document_instance, DocumentInstance)
        self.assertIsInstance(pdf_bytes, bytes)

    def test_multiple_document_generation(self):
        """Test performance of generating multiple documents."""
        data = {'title': 'Batch Test Document'}
        
        start_time = time.time()
        
        # Generate 5 documents
        for i in range(5):
            document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
                template_name='Simple Template',
                data={**data, 'title': f'{data["title"]} {i+1}'},
                user=self.user
            )
        
        total_time = time.time() - start_time
        
        # Should complete within 15 seconds for 5 simple documents
        self.assertLess(total_time, 15.0)
        
        # Verify all documents were created
        documents = DocumentInstance.objects.filter(template=self.simple_template)
        self.assertEqual(documents.count(), 5)
