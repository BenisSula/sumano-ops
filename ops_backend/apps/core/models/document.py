"""
Document models for the Sumano Operations Management System.

This module provides unified document template and instance models for all
document types across the system, ensuring consistent PDF generation and storage.
"""

import uuid
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.core.files.storage import default_storage
from django.utils import timezone

from .base import TimeStampedModel


class DocumentTemplate(TimeStampedModel):
    """
    Unified document template model for all document types.
    
    This model stores HTML templates that can be used to generate PDFs
    for various business processes including intake, acceptance, change,
    handover, and legal documents.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template identification
    name = models.CharField(
        max_length=255,
        default="Untitled Template",
        help_text="Human-readable name for this template"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this template is used for"
    )
    
    # Template classification
    template_type = models.CharField(
        max_length=50,
        choices=[
            ('INTAKE', 'Intake Document'),
            ('ACCEPTANCE', 'Acceptance Document'),
            ('CHANGE', 'Change Request Document'),
            ('HANDOVER', 'Handover Document'),
            ('LEGAL', 'Legal Document'),
        ],
        default='INTAKE',
        help_text="Type of document this template generates"
    )
    
    # Template content
    content = models.TextField(
        default="<html><body><h1>Template Content</h1><p>Template content goes here.</p></body></html>",
        help_text="HTML template content with Django template syntax"
    )
    version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Version number of this template"
    )
    
    # Template status
    status = models.CharField(
        max_length=20,
        choices=[
            ('DRAFT', 'Draft'),
            ('PUBLISHED', 'Published'),
            ('ARCHIVED', 'Archived'),
        ],
        default='DRAFT',
        help_text="Current status of this template"
    )
    
    # Template metadata
    required_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="List of required field names for this template"
    )
    optional_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="List of optional field names for this template"
    )
    
    # Audit information
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        related_name='created_document_templates',
        null=True,
        blank=True,
        help_text="User who created this template"
    )
    
    class Meta:
        verbose_name = "Document Template"
        verbose_name_plural = "Document Templates"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template_type', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['name']),
        ]
        unique_together = [['name', 'version']]
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.template_type})"
    
    def is_published(self):
        """Check if this template is published and ready for use."""
        return self.status == 'PUBLISHED'
    
    def get_all_fields(self):
        """Get all required and optional fields for this template."""
        return {
            'required': self.required_fields or [],
            'optional': self.optional_fields or [],
        }
    
    def validate_data(self, data):
        """
        Validate that provided data contains all required fields.
        
        Args:
            data (dict): Data to validate
            
        Returns:
            tuple: (is_valid, missing_fields)
        """
        required_fields = self.required_fields or []
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        return len(missing_fields) == 0, missing_fields


class DocumentInstance(TimeStampedModel):
    """
    Document instance model for generated documents.
    
    This model represents a specific document that was generated from
    a template with actual data, including the generated PDF file.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Document relationships
    template = models.ForeignKey(
        DocumentTemplate,
        on_delete=models.PROTECT,
        related_name='instances',
        help_text="Template used to generate this document"
    )
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True,
        help_text="Project this document belongs to"
    )
    
    # Document data
    filled_data = models.JSONField(
        default=dict,
        help_text="Data used to fill the template"
    )
    
    # Generated document
    generated_pdf = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        blank=True,
        null=True,
        help_text="Generated PDF file"
    )
    
    # Document metadata
    document_title = models.CharField(
        max_length=255,
        default="Untitled Document",
        help_text="Title of this specific document instance"
    )
    document_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Document number or reference"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ('GENERATED', 'Generated'),
            ('SIGNED', 'Signed'),
            ('ARCHIVED', 'Archived'),
        ],
        default='GENERATED',
        help_text="Current status of this document"
    )
    
    # Signature information
    signed_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='signed_documents',
        help_text="User who signed this document"
    )
    signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this document was signed"
    )
    
    # Audit information
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        related_name='created_documents',
        null=True,
        blank=True,
        help_text="User who generated this document"
    )
    
    class Meta:
        verbose_name = "Document Instance"
        verbose_name_plural = "Document Instances"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template', 'project']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['project', 'created_at']),
            models.Index(fields=['document_number']),
        ]
    
    def __str__(self):
        project_name = self.project.project_name if self.project else "No Project"
        return f"{self.document_title} - {project_name}"
    
    def is_signed(self):
        """Check if this document has been signed."""
        return self.status == 'SIGNED' and self.signed_by is not None
    
    def can_be_signed(self):
        """Check if this document can be signed."""
        return self.status == 'GENERATED' and self.generated_pdf
    
    def sign(self, user):
        """
        Sign this document.
        
        Args:
            user: User signing the document
        """
        if self.can_be_signed():
            self.status = 'SIGNED'
            self.signed_by = user
            self.signed_at = timezone.now()
            self.save(update_fields=['status', 'signed_by', 'signed_at', 'updated_at'])
    
    def get_file_size(self):
        """Get the size of the generated PDF file."""
        if self.generated_pdf:
            try:
                return self.generated_pdf.size
            except (ValueError, OSError):
                return 0
        return 0
    
    def get_file_url(self):
        """Get the URL for downloading the PDF file."""
        if self.generated_pdf:
            return self.generated_pdf.url
        return None