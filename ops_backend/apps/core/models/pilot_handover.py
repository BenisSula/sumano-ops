"""
Pilot Handover models for the Sumano Operations Management System.

This module provides models for internal handover workflows for completed pilot projects,
leveraging the unified document system for internal handover documentation.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from .base import TimeStampedModel
from .project import Project
from .document import DocumentInstance


class PilotHandover(TimeStampedModel):
    """
    Pilot Handover model for tracking internal handover processes for completed pilot projects.
    
    This model stores handover data in DocumentInstance.filled_data and
    provides business logic for internal handover processes.
    """
    
    APPROVAL_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('ready_for_review', 'Ready for Review'),
        ('approved', 'Approved'),
        ('hold', 'Hold'),
        ('completed', 'Completed'),
    ]
    
    GO_NO_GO_CHOICES = [
        ('approved', 'Approved - Ready for Handover'),
        ('hold', 'Hold - Issues to Resolve'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Project relationship
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='pilot_handovers',
        help_text="The pilot project being handed over"
    )
    
    # Document instance relationship (stores the actual handover data)
    document_instance = models.OneToOneField(
        DocumentInstance,
        on_delete=models.CASCADE,
        related_name='pilot_handover_record',
        help_text="Document instance containing handover data and PDF"
    )
    
    # Handover metadata
    expected_delivery_date = models.DateField(
        help_text="Expected delivery date for the handover"
    )
    
    assigned_team_members = models.JSONField(
        default=list,
        help_text="List of team members assigned to this handover"
    )
    
    # Handover status tracking
    status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='draft',
        help_text="Current status of the handover process"
    )
    
    # Final approval decision
    final_go_no_go = models.CharField(
        max_length=10,
        choices=GO_NO_GO_CHOICES,
        null=True,
        blank=True,
        help_text="Final go/no-go decision for handover"
    )
    
    # Signature tracking
    team_lead_signed = models.BooleanField(
        default=False,
        help_text="Whether team lead has signed off on the handover"
    )
    team_lead_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When team lead signed off"
    )
    
    # Audit information
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        related_name='created_pilot_handovers',
        help_text="User who created this handover record"
    )
    
    reviewed_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_pilot_handovers',
        help_text="User who reviewed this handover"
    )
    
    class Meta:
        verbose_name = "Pilot Handover"
        verbose_name_plural = "Pilot Handovers"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['status', 'expected_delivery_date']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['reviewed_by', 'status']),
        ]
    
    def __str__(self):
        return f"Handover - {self.project.project_name} ({self.get_status_display()})"
    
    @property
    def is_ready_for_handover(self):
        """Check if handover is ready for final approval."""
        return self.status == 'ready_for_review' and self.team_lead_signed
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage based on checklist items."""
        checklist_data = self.get_checklist_data()
        if not checklist_data:
            return 0
        
        total_items = 0
        completed_items = 0
        
        for section, items in checklist_data.items():
            if isinstance(items, dict):
                for item, value in items.items():
                    total_items += 1
                    if value:
                        completed_items += 1
        
        return int((completed_items / total_items * 100)) if total_items > 0 else 0
    
    def get_project_reference_data(self):
        """Get project reference data from document instance."""
        return self.document_instance.filled_data.get('project_reference', {})
    
    def get_checklist_data(self):
        """Get checklist data from document instance."""
        return self.document_instance.filled_data.get('checklist', {})
    
    def get_handover_approval_data(self):
        """Get handover approval data from document instance."""
        return self.document_instance.filled_data.get('handover_approval', {})
    
    def get_signature_data(self):
        """Get signature data from document instance."""
        return self.document_instance.filled_data.get('signatures', {})
    
    @classmethod
    def get_checklist_sections(cls):
        """Get list of checklist sections and their items."""
        return {
            'technical_setup': [
                'domain_configured', 'ssl_active', 'site_load_ok', 
                'responsive_design', 'no_broken_links'
            ],
            'core_pages': [
                'home_completed', 'about_news_added', 'contact_correct',
                'portal_links_ok', 'social_media_tested'
            ],
            'content_accuracy': [
                'logo_correct', 'photos_optimized', 'text_proofread',
                'info_matches_official'
            ],
            'security_compliance': [
                'admin_created', 'restricted_access', 'privacy_statement_included'
            ],
            'training_handover_prep': [
                'training_scheduled', 'training_materials_ready',
                'howto_instructions', 'support_contact_added'
            ],
            'final_test_run': [
                'browsers_tested', 'forms_tested', 'backup_taken',
                'screenshots_captured'
            ]
        }
    
    def update_checklist_section(self, section_name, section_data):
        """Update a specific checklist section."""
        if section_name not in self.get_checklist_sections():
            raise ValueError(f"Invalid checklist section: {section_name}")
        
        filled_data = self.document_instance.filled_data.copy()
        if 'checklist' not in filled_data:
            filled_data['checklist'] = {}
        
        filled_data['checklist'][section_name] = section_data
        self.document_instance.filled_data = filled_data
        self.document_instance.save(update_fields=['filled_data', 'updated_at'])
    
    def update_project_reference(self, reference_data):
        """Update project reference data."""
        filled_data = self.document_instance.filled_data.copy()
        filled_data['project_reference'] = reference_data
        self.document_instance.filled_data = filled_data
        self.document_instance.save(update_fields=['filled_data', 'updated_at'])
    
    def sign_handover(self, user, signature_data):
        """
        Sign the handover document.
        
        Args:
            user: User signing the document
            signature_data: Dictionary containing signature information
        """
        filled_data = self.document_instance.filled_data.copy()
        if 'signatures' not in filled_data:
            filled_data['signatures'] = {}
        
        # Only team leads can sign handovers
        user_role = getattr(user, 'role', None)
        if not user_role or user_role.codename not in ['staff', 'superadmin']:
            raise ValueError("Only staff members can sign handover documents.")
        
        self.team_lead_signed = True
        self.team_lead_signed_at = timezone.now()
        # Convert datetime objects to ISO strings for JSON serialization
        serialized_signature_data = {}
        for key, value in signature_data.items():
            if hasattr(value, 'isoformat'):  # datetime object
                serialized_signature_data[key] = value.isoformat()
            else:
                serialized_signature_data[key] = value
        
        filled_data['signatures']['team_lead'] = serialized_signature_data
        
        # Update document instance
        self.document_instance.filled_data = filled_data
        self.document_instance.save(update_fields=['filled_data', 'updated_at'])
        
        # Save handover record
        self.save()
    
    def can_be_signed_by(self, user):
        """Check if user can sign this handover document."""
        user_role = getattr(user, 'role', None)
        if not user_role:
            return False
        
        # Only staff can sign handovers, and only if not already signed
        return user_role.codename in ['staff', 'superadmin'] and not self.team_lead_signed
    
    def can_be_reviewed_by(self, user):
        """Check if user can review this handover."""
        user_role = getattr(user, 'role', None)
        if not user_role:
            return False
        
        # Only staff can review handovers
        return user_role.codename in ['staff', 'superadmin']
    
    def generate_handover_document(self, user):
        """
        Generate internal handover PDF.
        
        Args:
            user: User generating the document
        """
        from apps.core.services.pdf_service import PDFGenerationService
        
        # Prepare data for PDF generation
        pdf_data = self._prepare_pdf_data()
        
        # Generate PDF using unified document system
        document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
            template_name='Internal Pilot Handover',
            data=pdf_data,
            user=user,
            project=self.project
        )
        
        return document_instance, pdf_bytes
    
    def _prepare_pdf_data(self):
        """Prepare data for PDF generation."""
        project = self.project
        project_ref = self.get_project_reference_data()
        checklist_data = self.get_checklist_data()
        approval_data = self.get_handover_approval_data()
        signature_data = self.get_signature_data()
        
        return {
            # Project Reference
            'client_school_name': project.client.organization.name,
            'pilot_start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else 'N/A',
            'expected_delivery_date': self.expected_delivery_date.strftime('%Y-%m-%d'),
            'assigned_team_members': ', '.join(self.assigned_team_members),
            
            # Checklist sections
            'technical_setup': checklist_data.get('technical_setup', {}),
            'core_pages': checklist_data.get('core_pages', {}),
            'content_accuracy': checklist_data.get('content_accuracy', {}),
            'security_compliance': checklist_data.get('security_compliance', {}),
            'training_handover_prep': checklist_data.get('training_handover_prep', {}),
            'final_test_run': checklist_data.get('final_test_run', {}),
            
            # Handover Approval
            'final_go_no_go': self.get_final_go_no_go_display() if self.final_go_no_go else 'Pending',
            'team_lead_name': signature_data.get('team_lead', {}).get('name', ''),
            'team_lead_signature_date': signature_data.get('team_lead', {}).get('date', ''),
            
            # System Information
            'generation_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.get_status_display(),
            'completion_percentage': f"{self.completion_percentage}%",
            'handover_id': str(self.id),
        }
