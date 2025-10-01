"""
Client domain models for Sumano OMS.

This module contains models related to client management and organization structure.
"""

import uuid
from django.db import models
from django.core.validators import EmailValidator, RegexValidator

from .base import TimeStampedModel


class Organization(TimeStampedModel):
    """
    Represents a client organization that contracts with Sumano Tech.
    
    This model stores organizational information for clients who contract
    our services (web development, mobile apps, OMS, portals, audits).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=200,
        help_text="Official organization name"
    )
    legal_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Legal entity name if different from organization name"
    )
    organization_type = models.CharField(
        max_length=50,
        choices=[
            ('business', 'Business'),
            ('nonprofit', 'Non-Profit Organization'),
            ('educational', 'Educational Institution'),
            ('government', 'Government Agency'),
            ('healthcare', 'Healthcare Organization'),
            ('other', 'Other'),
        ],
        default='business',
        help_text="Type of organization"
    )
    industry = models.CharField(
        max_length=100,
        blank=True,
        help_text="Industry or sector the organization operates in"
    )
    website = models.URLField(
        blank=True,
        help_text="Organization's website URL"
    )
    description = models.TextField(
        blank=True,
        help_text="Brief description of the organization"
    )
    
    # Contact information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        help_text="Primary contact phone number"
    )
    email = models.EmailField(
        blank=True,
        help_text="Primary contact email address"
    )
    
    # Address information
    address_line1 = models.CharField(
        max_length=200,
        blank=True,
        help_text="Street address line 1"
    )
    address_line2 = models.CharField(
        max_length=200,
        blank=True,
        help_text="Street address line 2"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text="City"
    )
    state_province = models.CharField(
        max_length=100,
        blank=True,
        help_text="State or Province"
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Postal/ZIP code"
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        default='United States',
        help_text="Country"
    )
    
    # Business status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('prospect', 'Prospect'),
            ('former', 'Former Client'),
        ],
        default='prospect',
        help_text="Current relationship status with Sumano Tech"
    )
    
    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['status']),
            models.Index(fields=['organization_type']),
        ]

    def __str__(self):
        return self.name


class Contact(TimeStampedModel):
    """
    Represents individual contacts within client organizations.
    
    This model stores contact information for people we work with
    at client organizations (project managers, decision makers, etc.).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='contacts',
        help_text="Organization this contact belongs to"
    )
    
    # Personal information
    first_name = models.CharField(
        max_length=100,
        help_text="Contact's first name"
    )
    last_name = models.CharField(
        max_length=100,
        help_text="Contact's last name"
    )
    title = models.CharField(
        max_length=100,
        blank=True,
        help_text="Job title or position"
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text="Department within the organization"
    )
    
    # Contact information
    email = models.EmailField(
        help_text="Primary email address"
    )
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        help_text="Primary phone number"
    )
    mobile = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        help_text="Mobile phone number"
    )
    
    # Role information
    role_type = models.CharField(
        max_length=50,
        choices=[
            ('decision_maker', 'Decision Maker'),
            ('project_manager', 'Project Manager'),
            ('technical_lead', 'Technical Lead'),
            ('stakeholder', 'Stakeholder'),
            ('end_user', 'End User'),
            ('billing', 'Billing Contact'),
            ('other', 'Other'),
        ],
        default='stakeholder',
        help_text="Type of role in project relationship"
    )
    is_primary_contact = models.BooleanField(
        default=False,
        help_text="Is this the primary contact for the organization?"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('former', 'Former'),
        ],
        default='active',
        help_text="Current status of this contact"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this contact"
    )

    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        ordering = ['organization', 'last_name', 'first_name']
        indexes = [
            models.Index(fields=['organization', 'is_primary_contact']),
            models.Index(fields=['email']),
            models.Index(fields=['role_type']),
        ]
        unique_together = [
            ['organization', 'email'],  # Each email should be unique per organization
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.organization.name})"

    @property
    def full_name(self):
        """Return the contact's full name."""
        return f"{self.first_name} {self.last_name}"


class Client(TimeStampedModel):
    """
    Represents a client relationship with Sumano Tech.
    
    This model serves as the main entry point for client relationships,
    linking organizations to our service delivery projects.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='client_profile',
        help_text="Organization this client profile represents"
    )
    
    # Client relationship information
    client_since = models.DateField(
        help_text="Date when this organization became a client"
    )
    relationship_status = models.CharField(
        max_length=20,
        choices=[
            ('prospect', 'Prospect'),
            ('active', 'Active Client'),
            ('on_hold', 'On Hold'),
            ('former', 'Former Client'),
        ],
        default='prospect',
        help_text="Current relationship status"
    )
    
    # Business information
    contract_type = models.CharField(
        max_length=50,
        choices=[
            ('project_based', 'Project-Based'),
            ('retainer', 'Retainer Agreement'),
            ('hourly', 'Hourly Consulting'),
            ('fixed_price', 'Fixed Price'),
            ('milestone', 'Milestone-Based'),
        ],
        blank=True,
        help_text="Type of contract or engagement model"
    )
    
    # Financial information
    billing_contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_clients',
        help_text="Primary billing contact for this client"
    )
    
    # Notes and metadata
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this client relationship"
    )
    internal_rating = models.IntegerField(
        choices=[
            (1, 'Poor'),
            (2, 'Fair'),
            (3, 'Good'),
            (4, 'Very Good'),
            (5, 'Excellent'),
        ],
        null=True,
        blank=True,
        help_text="Internal rating of client relationship (1-5)"
    )
    
    # === CLIENT INTAKE FIELDS (School Pilot Project) ===
    
    # School Information
    school_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of the school or educational institution"
    )
    address = models.TextField(
        blank=True,
        help_text="Complete address of the school"
    )
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary contact person at the school"
    )
    role_position = models.CharField(
        max_length=100,
        blank=True,
        help_text="Role or position of the contact person"
    )
    phone_whatsapp = models.CharField(
        max_length=20,
        blank=True,
        help_text="Phone number or WhatsApp contact"
    )
    email = models.EmailField(
        blank=True,
        help_text="Primary email address"
    )
    current_website = models.URLField(
        blank=True,
        help_text="Current website URL if any"
    )
    
    # School Statistics
    number_of_students = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total number of students"
    )
    number_of_staff = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total number of staff members"
    )
    
    # Project Information
    project_type = models.JSONField(
        default=list,
        blank=True,
        help_text="Selected project types (multiple choice)"
    )
    project_purpose = models.JSONField(
        default=list,
        blank=True,
        help_text="Project purposes and goals (multiple choice)"
    )
    pilot_scope_features = models.JSONField(
        default=list,
        blank=True,
        help_text="Selected pilot scope features and modules"
    )
    
    # Timeline
    pilot_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Preferred pilot project start date"
    )
    pilot_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected pilot project end date"
    )
    timeline_preference = models.CharField(
        max_length=50,
        choices=[
            ('asap', 'ASAP'),
            ('1_month', 'Within 1 Month'),
            ('3_months', 'Within 3 Months'),
            ('6_months', 'Within 6 Months'),
            ('flexible', 'Flexible'),
        ],
        blank=True,
        help_text="Timeline preference for project start"
    )
    
    # Design Preferences
    design_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Design preferences and requirements"
    )
    logo_colors = models.JSONField(
        default=dict,
        blank=True,
        help_text="Preferred logo colors and branding"
    )
    
    # Content and Maintenance
    content_availability = models.BooleanField(
        default=False,
        help_text="Whether content is readily available"
    )
    maintenance_plan = models.JSONField(
        default=dict,
        blank=True,
        help_text="Maintenance and support plan preferences"
    )
    
    # Financial Commitment
    token_commitment_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Token commitment fee amount"
    )
    
    # Additional Information
    additional_notes = models.TextField(
        blank=True,
        help_text="Additional notes and requirements"
    )
    acknowledgment = models.JSONField(
        default=dict,
        blank=True,
        help_text="Acknowledgment and signature data"
    )
    
    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['-created_at']
    
    @property
    def is_intake_complete(self):
        """Check if intake form is complete."""
        required_fields = [
            'school_name', 'contact_person', 'email', 'project_type',
            'project_purpose', 'pilot_scope_features', 'timeline_preference'
        ]
        
        for field in required_fields:
            value = getattr(self, field, None)
            if not value or (isinstance(value, list) and len(value) == 0):
                return False
        return True
    
    @property
    def intake_completion_percentage(self):
        """Calculate intake form completion percentage."""
        intake_fields = [
            'school_name', 'address', 'contact_person', 'role_position',
            'phone_whatsapp', 'email', 'current_website', 'number_of_students',
            'number_of_staff', 'project_type', 'project_purpose',
            'pilot_scope_features', 'pilot_start_date', 'pilot_end_date',
            'timeline_preference', 'design_preferences', 'logo_colors',
            'content_availability', 'maintenance_plan', 'token_commitment_fee',
            'additional_notes', 'acknowledgment'
        ]
        
        completed_fields = 0
        total_fields = len(intake_fields)
        
        for field in intake_fields:
            value = getattr(self, field, None)
            if value is not None:
                if isinstance(value, (list, dict)):
                    if len(value) > 0:
                        completed_fields += 1
                elif value != '':
                    completed_fields += 1
        
        return round((completed_fields / total_fields) * 100, 1)

    def __str__(self):
        return f"{self.organization.name} (Client since {self.client_since})"

    @property
    def primary_contact(self):
        """Return the primary contact for this client."""
        try:
            return self.organization.contacts.filter(is_primary_contact=True).first()
        except Contact.DoesNotExist:
            return None

    @property
    def is_active(self):
        """Check if this client is currently active."""
        return self.relationship_status == 'active'
