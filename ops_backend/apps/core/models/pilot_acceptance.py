"""
Pilot Acceptance models for the Sumano Operations Management System.

This module provides models for pilot project acceptance workflows,
leveraging the unified document system for acceptance certificates.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from .base import TimeStampedModel
from .project import Project
from .document import DocumentInstance


class PilotAcceptance(TimeStampedModel):
    """
    Pilot Acceptance model for tracking pilot project acceptance workflows.
    
    This model stores acceptance data in DocumentInstance.filled_data and
    provides business logic for pilot acceptance processes.
    """
    
    ACCEPTANCE_STATUS_CHOICES = [
        ('accepted', 'Accepted'),
        ('accepted_with_conditions', 'Accepted with Conditions'),
        ('not_accepted', 'Not Accepted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Project relationship
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='pilot_acceptance',
        help_text="The pilot project being accepted"
    )
    
    # Document instance relationship (stores the actual acceptance data)
    document_instance = models.OneToOneField(
        DocumentInstance,
        on_delete=models.CASCADE,
        related_name='pilot_acceptance_record',
        help_text="Document instance containing acceptance data and PDF"
    )
    
    # Acceptance metadata
    acceptance_status = models.CharField(
        max_length=30,
        choices=ACCEPTANCE_STATUS_CHOICES,
        help_text="Overall acceptance status of the pilot project"
    )
    
    # Completion tracking
    completion_date = models.DateField(
        help_text="Date when the pilot project was completed"
    )
    
    # Token payment information
    token_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Token payment amount for pilot completion"
    )
    
    # Issues and resolution
    issues_to_resolve = models.TextField(
        blank=True,
        help_text="Any issues that need to be resolved"
    )
    
    # Signature tracking
    school_representative_signed = models.BooleanField(
        default=False,
        help_text="Whether school representative has signed"
    )
    school_representative_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When school representative signed"
    )
    
    company_representative_signed = models.BooleanField(
        default=False,
        help_text="Whether company representative has signed"
    )
    company_representative_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When company representative signed"
    )
    
    # Audit information
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        related_name='created_pilot_acceptances',
        help_text="User who created this acceptance record"
    )
    
    class Meta:
        verbose_name = "Pilot Acceptance"
        verbose_name_plural = "Pilot Acceptances"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'acceptance_status']),
            models.Index(fields=['acceptance_status', 'completion_date']),
            models.Index(fields=['created_by', 'created_at']),
        ]
    
    def __str__(self):
        return f"Pilot Acceptance - {self.project.project_name} ({self.get_acceptance_status_display()})"
    
    @property
    def is_fully_signed(self):
        """Check if both parties have signed the acceptance."""
        return self.school_representative_signed and self.company_representative_signed
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage based on checklist items."""
        checklist_data = self.get_checklist_data()
        if not checklist_data:
            return 0
        
        total_items = len(self.get_checklist_fields())
        completed_items = sum(1 for value in checklist_data.values() if value is True)
        
        return round((completed_items / total_items) * 100, 1) if total_items > 0 else 0
    
    def get_checklist_data(self):
        """Get checklist data from document instance."""
        return self.document_instance.filled_data.get('checklist', {})
    
    def get_signature_data(self):
        """Get signature data from document instance."""
        return self.document_instance.filled_data.get('signatures', {})
    
    def get_project_reference_data(self):
        """Get project reference data from document instance."""
        return self.document_instance.filled_data.get('project_reference', {})
    
    @classmethod
    def get_checklist_fields(cls):
        """Get list of all checklist field names."""
        return [
            'digital_gateway_live',
            'mobile_friendly',
            'pages_present',
            'portals_linked',
            'social_media_embedded',
            'logo_colors_correct',
            'photos_content_displayed',
            'layout_design_ok',
            'staff_training_completed',
            'training_materials_provided',
            'no_critical_errors',
            'minor_issues_resolved',
        ]
    
    def update_checklist_item(self, field_name, value):
        """Update a specific checklist item."""
        if field_name not in self.get_checklist_fields():
            raise ValueError(f"Invalid checklist field: {field_name}")
        
        filled_data = self.document_instance.filled_data.copy()
        if 'checklist' not in filled_data:
            filled_data['checklist'] = {}
        
        filled_data['checklist'][field_name] = value
        self.document_instance.filled_data = filled_data
        self.document_instance.save(update_fields=['filled_data', 'updated_at'])
    
    def sign_acceptance(self, user, signature_data):
        """
        Sign the acceptance document.
        
        Args:
            user: User signing the document
            signature_data: Dictionary containing signature information
        """
        filled_data = self.document_instance.filled_data.copy()
        if 'signatures' not in filled_data:
            filled_data['signatures'] = {}
        
        # Determine if this is school or company representative
        user_role = getattr(user, 'role', None)
        is_school_rep = user_role and user_role.codename == 'client_contact'
        
        if is_school_rep:
            self.school_representative_signed = True
            self.school_representative_signed_at = timezone.now()
            filled_data['signatures']['school_representative'] = signature_data
        else:
            self.company_representative_signed = True
            self.company_representative_signed_at = timezone.now()
            filled_data['signatures']['company_representative'] = signature_data
        
        # Update document instance
        self.document_instance.filled_data = filled_data
        self.document_instance.save(update_fields=['filled_data', 'updated_at'])
        
        # Save acceptance record
        self.save()
    
    def can_be_signed_by(self, user):
        """Check if user can sign this acceptance."""
        user_role = getattr(user, 'role', None)
        if not user_role:
            return False
        
        if user_role.codename == 'client_contact':
            # School representative can sign if not already signed
            return not self.school_representative_signed
        elif user_role.codename in ['staff', 'superadmin']:
            # Company representative can sign if not already signed
            return not self.company_representative_signed
        
        return False
    
    def generate_acceptance_certificate(self, user):
        """
        Generate acceptance certificate PDF.
        
        Args:
            user: User generating the certificate
        """
        from apps.core.services.pdf_service import PDFGenerationService
        
        # Prepare data for PDF generation
        pdf_data = self._prepare_pdf_data()
        
        # Generate PDF using unified document system
        document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
            template_name='Pilot Acceptance Certificate',
            data=pdf_data,
            user=user,
            project=self.project
        )
        
        return document_instance, pdf_bytes
    
    def _prepare_pdf_data(self):
        """Prepare data for PDF generation."""
        project = self.project
        checklist_data = self.get_checklist_data()
        signature_data = self.get_signature_data()
        
        return {
            # Project Reference
            'school_name': project.client.organization.name,
            'pilot_start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
            'completion_date': self.completion_date.strftime('%Y-%m-%d'),
            'token_payment': str(self.token_payment) if self.token_payment else '0',
            
            # Acceptance Status
            'acceptance_status': self.get_acceptance_status_display(),
            'issues_to_resolve': self.issues_to_resolve,
            
            # Checklist Items
            'digital_gateway_live': 'Yes' if checklist_data.get('digital_gateway_live') else 'No',
            'mobile_friendly': 'Yes' if checklist_data.get('mobile_friendly') else 'No',
            'pages_present': 'Yes' if checklist_data.get('pages_present') else 'No',
            'portals_linked': 'Yes' if checklist_data.get('portals_linked') else 'No',
            'social_media_embedded': 'Yes' if checklist_data.get('social_media_embedded') else 'No',
            'logo_colors_correct': 'Yes' if checklist_data.get('logo_colors_correct') else 'No',
            'photos_content_displayed': 'Yes' if checklist_data.get('photos_content_displayed') else 'No',
            'layout_design_ok': 'Yes' if checklist_data.get('layout_design_ok') else 'No',
            'staff_training_completed': 'Yes' if checklist_data.get('staff_training_completed') else 'No',
            'training_materials_provided': 'Yes' if checklist_data.get('training_materials_provided') else 'No',
            'no_critical_errors': 'Yes' if checklist_data.get('no_critical_errors') else 'No',
            'minor_issues_resolved': 'Yes' if checklist_data.get('minor_issues_resolved') else 'No',
            
            # Signatures
            'school_representative_name': signature_data.get('school_representative', {}).get('name', ''),
            'school_representative_title': signature_data.get('school_representative', {}).get('title', ''),
            'school_representative_signed_date': signature_data.get('school_representative', {}).get('date', ''),
            
            'company_rep_name': signature_data.get('company_representative', {}).get('name', ''),
            'company_rep_title': signature_data.get('company_representative', {}).get('title', ''),
            'company_rep_signed_date': signature_data.get('company_representative', {}).get('date', ''),
            
            # System Information
            'generation_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'completion_percentage': f"{self.completion_percentage}%",
        }
