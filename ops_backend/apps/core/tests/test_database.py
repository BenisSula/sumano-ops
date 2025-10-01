"""
Database connection and model tests for Sumano OMS.
"""
from django.test import TestCase
from django.db import connection
from django.core.exceptions import ValidationError
from apps.core.models import Organization, Client, Project, Contact


class DatabaseConnectionTestCase(TestCase):
    """Test database connectivity and basic operations."""

    def test_database_connection(self):
        """Test that we can connect to the database."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)

    def test_database_name(self):
        """Test that we're connected to the correct database."""
        db_name = connection.settings_dict['NAME']
        self.assertIn('sumano_ops', db_name)


class NormalizedModelsBasicTestCase(TestCase):
    """Test basic functionality of normalized models."""

    def test_organization_creation(self):
        """Test creating an Organization instance."""
        org = Organization.objects.create(
            name="Test Organization",
            organization_type="business",
            email="contact@testorg.com"
        )
        
        self.assertEqual(org.name, "Test Organization")
        self.assertEqual(org.organization_type, "business")
        self.assertEqual(org.status, "prospect")  # default
        self.assertIsNotNone(org.id)
        self.assertIsNotNone(org.created_at)
        self.assertIsNotNone(org.updated_at)


class NormalizedModelsTestCase(TestCase):
    """Test the new normalized models functionality."""

    def test_organization_creation(self):
        """Test creating an Organization instance."""
        org = Organization.objects.create(
            name="Test Organization",
            organization_type="business",
            email="contact@testorg.com"
        )
        
        self.assertEqual(org.name, "Test Organization")
        self.assertEqual(org.organization_type, "business")
        self.assertEqual(org.status, "prospect")  # default
        self.assertIsNotNone(org.id)

    def test_client_organization_relationship(self):
        """Test Client-Organization relationship."""
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        
        self.assertEqual(client.organization, org)
        self.assertEqual(org.client_profile, client)

    def test_project_client_relationship(self):
        """Test Project-Client relationship."""
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        project = Project.objects.create(
            client=client,
            project_name="Test Project",
            service_type="web_development",
            start_date="2024-01-01"
        )
        
        self.assertEqual(project.client, client)
        self.assertEqual(project.client_name, "Test Org")
        self.assertIn(project, client.projects.all())
