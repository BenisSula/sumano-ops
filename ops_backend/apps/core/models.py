"""
Core models for the Sumano Operations Management System.

This module provides the main entry point for all core models.
Models are organized by domain in separate files for better maintainability.
"""

# Import all models from their respective modules
from .models.client import Client, Organization, Contact
from .models.project import Project, ProjectPhase
from .models.document import DocumentTemplate, DocumentInstance
from .models.system import User, Role, Permission

# Backward compatibility - keep the old ServiceProject model for now
# TODO: Migrate existing ServiceProject data to new normalized structure
import uuid
from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base class that provides self-updating 'created_at' and 'updated_at' fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ServiceProject(TimeStampedModel):
    """
    Legacy MVP placeholder model for Sumano Tech's service delivery tracking.
    
    DEPRECATED: This model will be replaced by the normalized Project model.
    Kept for backward compatibility during migration.
    """
    SERVICE_TYPES = [
        ('web_development', 'Website Development'),
        ('mobile_app', 'Mobile Application'),
        ('operations_system', 'Operations Management System'),
        ('portal', 'Portal Development'),
        ('audit', 'System Audit'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_name = models.CharField(max_length=200, help_text="Name of the project")
    service_type = models.CharField(
        max_length=50,
        choices=SERVICE_TYPES,
        help_text="Type of service we are providing"
    )
    client_name = models.CharField(max_length=200, help_text="Name of our client")
    description = models.TextField(blank=True, help_text="Project description and scope")
    status = models.CharField(
        max_length=50,
        default='PLANNING',
        choices=[
            ('PLANNING', 'Planning'),
            ('IN_PROGRESS', 'In Progress'),
            ('TESTING', 'Testing'),
            ('DELIVERED', 'Delivered'),
            ('ONGOING_SUPPORT', 'Ongoing Support'),
            ('COMPLETED', 'Completed'),
        ],
        help_text="Current status of the service delivery"
    )
    start_date = models.DateField(null=True, blank=True, help_text="Project start date")
    expected_completion = models.DateField(null=True, blank=True, help_text="Expected completion date")

    class Meta:
        db_table = 'core_service_projects'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project_name} - {self.client_name} ({self.get_service_type_display()})"