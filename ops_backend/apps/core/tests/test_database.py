"""
Database connection and model tests for Sumano OMS.
"""
from django.test import TestCase
from django.db import connection
from django.core.exceptions import ValidationError
from apps.core.models import ServiceProject


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


class ServiceProjectModelTestCase(TestCase):
    """Test the ServiceProject model functionality."""

    def test_service_project_creation(self):
        """Test creating a ServiceProject instance."""
        project = ServiceProject.objects.create(
            project_name="Test Website Project",
            service_type="web_development",
            client_name="Test Client",
            description="A test website development project",
            status="PLANNING"
        )
        
        self.assertEqual(project.project_name, "Test Website Project")
        self.assertEqual(project.service_type, "web_development")
        self.assertEqual(project.client_name, "Test Client")
        self.assertEqual(project.status, "PLANNING")
        self.assertIsNotNone(project.id)
        self.assertIsNotNone(project.created_at)
        self.assertIsNotNone(project.updated_at)

    def test_service_type_choices(self):
        """Test that service type choices are valid."""
        valid_choices = [
            'web_development',
            'mobile_app',
            'operations_system',
            'portal',
            'audit'
        ]
        
        for choice in valid_choices:
            project = ServiceProject.objects.create(
                project_name=f"Test {choice}",
                service_type=choice,
                client_name="Test Client"
            )
            self.assertEqual(project.service_type, choice)

    def test_service_project_string_representation(self):
        """Test the string representation of ServiceProject."""
        project = ServiceProject.objects.create(
            project_name="Test Project",
            service_type="web_development",
            client_name="Test Client"
        )
        
        expected_str = "Test Project - Test Client (Website Development)"
        self.assertEqual(str(project), expected_str)

    def test_service_project_ordering(self):
        """Test that ServiceProject instances are ordered by created_at descending."""
        # Create projects with slight delays
        project1 = ServiceProject.objects.create(
            project_name="First Project",
            service_type="web_development",
            client_name="Client 1"
        )
        
        project2 = ServiceProject.objects.create(
            project_name="Second Project",
            service_type="mobile_app",
            client_name="Client 2"
        )
        
        projects = ServiceProject.objects.all()
        self.assertEqual(projects[0], project2)  # Most recent first
        self.assertEqual(projects[1], project1)
