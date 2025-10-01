"""
Change Request models for the Sumano Operations Management System.

This module provides models for change request workflows during pilot projects,
leveraging the unified document system for change authorization documents.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from .base import TimeStampedModel
from .project import Project
from .document import DocumentInstance


class ChangeRequest(TimeStampedModel):
    """
    Change Request model for tracking formal change requests during pilot projects.
    
    This model stores change request data in DocumentInstance.filled_data and
    provides business logic for change request processes.
    """
    
    DECISION_CHOICES = [
        ('proceed', 'Proceed with Change'),
        ('defer', 'Defer Change'),
        ('withdraw', 'Withdraw Change'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('impact_assessed', 'Impact Assessed'),
        ('client_decision', 'Client Decision'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('implemented', 'Implemented'),
        ('closed', 'Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Project relationship
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='change_requests',
        help_text="The pilot project this change request belongs to"
    )
    
    # Document instance relationship (stores the actual change request data)
    document_instance = models.OneToOneField(
        DocumentInstance,
        on_delete=models.CASCADE,
        related_name='change_request_record',
        help_text="Document instance containing change request data and PDF"
    )
    
    # Change request metadata
    request_date = models.DateField(
        help_text="Date when the change was requested"
    )
    
    reference_agreement = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reference to original agreement or contract"
    )
    
    # Request status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current status of the change request"
    )
    
    # Client decision
    client_decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        null=True,
        blank=True,
        help_text="Client's decision on the change request"
    )
    
    # Signature tracking
    client_rep_signed = models.BooleanField(
        default=False,
        help_text="Whether client representative has signed"
    )
    client_rep_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When client representative signed"
    )
    
    provider_signed = models.BooleanField(
        default=False,
        help_text="Whether provider representative has signed"
    )
    provider_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When provider representative signed"
    )
    
    # Audit information
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        related_name='created_change_requests',
        help_text="User who created this change request"
    )
    
    assessed_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assessed_change_requests',
        help_text="User who assessed the change request impact"
    )
    
    class Meta:
        verbose_name = "Change Request"
        verbose_name_plural = "Change Requests"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['status', 'request_date']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['assessed_by', 'status']),
        ]
    
    def __str__(self):
        return f"Change Request - {self.project.project_name} ({self.get_status_display()})"
    
    @property
    def is_fully_signed(self):
        """Check if both parties have signed the change request."""
        return self.client_rep_signed and self.provider_signed
    
    
    @property
    def is_ready_for_client_decision(self):
        """Check if change request is ready for client decision."""
        return self.status == 'impact_assessed' and self.assessed_by is not None
    
    def get_change_request_data(self):
        """Get change request data from document instance."""
        return self.document_instance.filled_data.get('change_request', {})
    
    def get_impact_assessment_data(self):
        """Get impact assessment data from document instance."""
        return self.document_instance.filled_data.get('impact_assessment', {})
    
    def get_client_decision_data(self):
        """Get client decision data from document instance."""
        return self.document_instance.filled_data.get('client_decision', {})
    
    def get_signature_data(self):
        """Get signature data from document instance."""
        return self.document_instance.filled_data.get('signatures', {})
    
    @classmethod
    def get_required_change_fields(cls):
        """Get list of required change request field names."""
        return [
            'description',
            'reason',
        ]
    
    @classmethod
    def get_impact_assessment_fields(cls):
        """Get list of impact assessment field names."""
        return [
            'no_additional_cost',
            'requires_additional_effort',
            'estimated_time',
            'estimated_cost',
        ]
    
    def update_change_request_data(self, field_name, value):
        """Update a specific change request field."""
        if field_name not in self.get_required_change_fields():
            raise ValueError(f"Invalid change request field: {field_name}")
        
        filled_data = self.document_instance.filled_data.copy()
        if 'change_request' not in filled_data:
            filled_data['change_request'] = {}
        
        filled_data['change_request'][field_name] = value
        self.document_instance.filled_data = filled_data
        self.document_instance.save(update_fields=['filled_data', 'updated_at'])
    
    def update_impact_assessment(self, assessment_data):
        """Update impact assessment data."""
        filled_data = self.document_instance.filled_data.copy()
        filled_data['impact_assessment'] = assessment_data
        self.document_instance.filled_data = filled_data
        self.document_instance.save(update_fields=['filled_data', 'updated_at'])
        
        # Update status to impact_assessed
        self.status = 'impact_assessed'
        self.save(update_fields=['status'])
    
    def sign_change_request(self, user, signature_data):
        """
        Sign the change request document.
        
        Args:
            user: User signing the document
            signature_data: Dictionary containing signature information
        """
        filled_data = self.document_instance.filled_data.copy()
        if 'signatures' not in filled_data:
            filled_data['signatures'] = {}
        
        # Determine if this is client or provider representative
        user_role = getattr(user, 'role', None)
        is_client_rep = user_role and user_role.codename == 'client_contact'
        
        if is_client_rep:
            self.client_rep_signed = True
            self.client_rep_signed_at = timezone.now()
            filled_data['signatures']['client_representative'] = signature_data
        else:
            self.provider_signed = True
            self.provider_signed_at = timezone.now()
            filled_data['signatures']['provider_representative'] = signature_data
        
        # Update document instance
        self.document_instance.filled_data = filled_data
        self.document_instance.save(update_fields=['filled_data', 'updated_at'])
        
        # Save change request record
        self.save()
    
    def can_be_signed_by(self, user):
        """Check if user can sign this change request."""
        user_role = getattr(user, 'role', None)
        if not user_role:
            return False
        
        if user_role.codename == 'client_contact':
            # Client representative can sign if not already signed
            return not self.client_rep_signed
        elif user_role.codename in ['staff', 'superadmin']:
            # Provider representative can sign if not already signed
            return not self.provider_signed
        
        return False
    
    def can_be_assessed_by(self, user):
        """Check if user can assess this change request."""
        user_role = getattr(user, 'role', None)
        if not user_role:
            return False
        
        # Only staff can assess change requests
        return user_role.codename in ['staff', 'superadmin']
    
    def generate_change_authorization_document(self, user):
        """
        Generate change authorization PDF.
        
        Args:
            user: User generating the document
        """
        from apps.core.services.pdf_service import PDFGenerationService
        
        # Prepare data for PDF generation
        pdf_data = self._prepare_pdf_data()
        
        # Generate PDF using unified document system
        document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
            template_name='Change Request Authorization',
            data=pdf_data,
            user=user,
            project=self.project
        )
        
        return document_instance, pdf_bytes
    
    def _prepare_pdf_data(self):
        """Prepare data for PDF generation."""
        project = self.project
        change_data = self.get_change_request_data()
        impact_data = self.get_impact_assessment_data()
        decision_data = self.get_client_decision_data()
        signature_data = self.get_signature_data()
        
        return {
            # Project Reference
            'project_title': project.project_name,
            'client_name': project.client.organization.name,
            'request_date': self.request_date.strftime('%Y-%m-%d'),
            'reference_agreement': self.reference_agreement,
            
            # Requested Change
            'description': change_data.get('description', ''),
            'reason': change_data.get('reason', ''),
            
            # Provider Impact Assessment
            'no_additional_cost': 'Yes' if impact_data.get('no_additional_cost') else 'No',
            'requires_additional_effort': 'Yes' if impact_data.get('requires_additional_effort') else 'No',
            'estimated_time': impact_data.get('estimated_time', ''),
            'estimated_cost': str(impact_data.get('estimated_cost', '')) if impact_data.get('estimated_cost') else '',
            
            # Client Decision
            'decision': self.get_client_decision_display() if self.client_decision else 'Pending',
            'client_rep_name': signature_data.get('client_representative', {}).get('name', ''),
            'client_rep_signed_date': signature_data.get('client_representative', {}).get('date', ''),
            
            'provider_name': signature_data.get('provider_representative', {}).get('name', ''),
            'provider_signed_date': signature_data.get('provider_representative', {}).get('date', ''),
            
            # System Information
            'generation_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.get_status_display(),
            'change_request_id': str(self.id),
        }
