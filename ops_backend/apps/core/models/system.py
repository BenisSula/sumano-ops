"""
System domain models for Sumano OMS.

This module contains models related to user management, roles, and permissions
for the internal system access control.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator, RegexValidator

from .base import TimeStampedModel


class Permission(TimeStampedModel):
    """
    Represents a specific permission or action that can be performed in the system.
    
    This model defines granular permissions for controlling access to various
    system features and operations.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Permission identification
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique name for this permission (e.g., 'view_projects')"
    )
    codename = models.CharField(
        max_length=100,
        unique=True,
        help_text="Code name for this permission (e.g., 'view_project')"
    )
    
    # Permission details
    description = models.TextField(
        help_text="Description of what this permission allows"
    )
    category = models.CharField(
        max_length=50,
        choices=[
            ('client', 'Client Management'),
            ('project', 'Project Management'),
            ('document', 'Document Management'),
            ('user', 'User Management'),
            ('system', 'System Administration'),
            ('reporting', 'Reporting'),
            ('financial', 'Financial'),
        ],
        help_text="Category this permission belongs to"
    )
    
    # Permission scope
    resource_type = models.CharField(
        max_length=50,
        choices=[
            ('global', 'Global'),
            ('organization', 'Organization'),
            ('project', 'Project'),
            ('document', 'Document'),
            ('user', 'User'),
        ],
        default='global',
        help_text="Type of resource this permission applies to"
    )
    
    # Permission status
    is_active = models.BooleanField(
        default=True,
        help_text="Is this permission currently active?"
    )
    
    class Meta:
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['codename']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.codename})"


class Role(TimeStampedModel):
    """
    Represents a role that can be assigned to users.
    
    This model defines roles with associated permissions for role-based
    access control (RBAC) in the system.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Role identification
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of this role (e.g., 'Project Manager')"
    )
    codename = models.CharField(
        max_length=50,
        unique=True,
        help_text="Code name for this role (e.g., 'project_manager')"
    )
    
    # Role details
    description = models.TextField(
        help_text="Description of this role and its responsibilities"
    )
    
    # Role hierarchy
    level = models.PositiveIntegerField(
        default=1,
        help_text="Hierarchy level (higher number = more permissions)"
    )
    parent_role = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_roles',
        help_text="Parent role in the hierarchy"
    )
    
    # Role configuration
    is_system_role = models.BooleanField(
        default=False,
        help_text="Is this a system-defined role that cannot be modified?"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is this role currently active?"
    )
    
    # Permissions
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='roles',
        help_text="Permissions assigned to this role"
    )
    
    # Usage tracking
    user_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of users currently assigned this role"
    )
    
    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ['level', 'name']
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['codename']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def get_all_permissions(self):
        """Get all permissions for this role, including inherited ones."""
        permissions = set(self.permissions.all())
        if self.parent_role:
            permissions.update(self.parent_role.get_all_permissions())
        return permissions

    def has_permission(self, permission_codename):
        """Check if this role has a specific permission."""
        return permission_codename in [p.codename for p in self.get_all_permissions()]


class User(AbstractUser):
    """
    Extended user model for Sumano Tech team members.
    
    This model extends Django's built-in User model to include additional
    fields specific to our operations management system.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Employee ID number"
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
        help_text="Primary phone number"
    )
    mobile = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        help_text="Mobile phone number"
    )
    
    # Professional information
    title = models.CharField(
        max_length=100,
        blank=True,
        help_text="Job title or position"
    )
    department = models.CharField(
        max_length=100,
        choices=[
            ('development', 'Development'),
            ('design', 'Design'),
            ('project_management', 'Project Management'),
            ('business_development', 'Business Development'),
            ('operations', 'Operations'),
            ('finance', 'Finance'),
            ('hr', 'Human Resources'),
            ('admin', 'Administration'),
        ],
        blank=True,
        help_text="Department within Sumano Tech"
    )
    
    # Role and permissions
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Primary role assigned to this user"
    )
    additional_roles = models.ManyToManyField(
        Role,
        blank=True,
        related_name='additional_users',
        help_text="Additional roles assigned to this user"
    )
    
    # Employment information
    hire_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when this employee was hired"
    )
    employment_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('on_leave', 'On Leave'),
            ('terminated', 'Terminated'),
        ],
        default='active',
        help_text="Current employment status"
    )
    
    # System preferences
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="User's timezone"
    )
    language = models.CharField(
        max_length=10,
        default='en',
        help_text="Preferred language"
    )
    
    # Profile information
    bio = models.TextField(
        blank=True,
        help_text="Brief biography or description"
    )
    skills = models.JSONField(
        default=list,
        help_text="List of technical skills (JSON array)"
    )
    
    # System metadata
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of last login"
    )
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of failed login attempts"
    )
    account_locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Account locked until this date/time"
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        help_text="User who created this account"
    )
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['department']),
            models.Index(fields=['employment_status']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}"

    def get_all_roles(self):
        """Get all roles assigned to this user."""
        roles = []
        if self.role:
            roles.append(self.role)
        roles.extend(self.additional_roles.all())
        return roles

    def get_all_permissions(self):
        """Get all permissions for this user across all their roles."""
        permissions = set()
        for role in self.get_all_roles():
            permissions.update(role.get_all_permissions())
        return permissions

    def has_permission(self, permission_codename):
        """Check if this user has a specific permission."""
        if self.is_superuser:
            return True
        return permission_codename in [p.codename for p in self.get_all_permissions()]

    def is_account_locked(self):
        """Check if the user's account is currently locked."""
        if not self.account_locked_until:
            return False
        from django.utils import timezone
        return timezone.now() < self.account_locked_until

    def lock_account(self, duration_minutes=30):
        """Lock the user's account for a specified duration."""
        from django.utils import timezone
        from datetime import timedelta
        self.account_locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked_until'])

    def unlock_account(self):
        """Unlock the user's account."""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['account_locked_until', 'failed_login_attempts'])
    
    def reset_failed_login_attempts(self):
        """Reset failed login attempts counter."""
        self.failed_login_attempts = 0
        self.save(update_fields=['failed_login_attempts'])
    
    def increment_failed_login_attempts(self):
        """Increment failed login attempts counter."""
        self.failed_login_attempts += 1
        self.save(update_fields=['failed_login_attempts'])
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account()


class SecurityEvent(TimeStampedModel):
    """
    Security event logging model for authentication and authorization tracking.
    
    This model logs all security-related events including login attempts,
    permission checks, and access violations for audit and monitoring purposes.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Event identification
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('login_attempt', 'Login Attempt'),
            ('login_success', 'Login Success'),
            ('login_failure', 'Login Failure'),
            ('logout', 'Logout'),
            ('permission_check', 'Permission Check'),
            ('access_denied', 'Access Denied'),
            ('token_refresh', 'Token Refresh'),
            ('password_change', 'Password Change'),
            ('account_lockout', 'Account Lockout'),
            ('suspicious_activity', 'Suspicious Activity'),
        ],
        help_text="Type of security event"
    )
    
    # User and session information
    user = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_events',
        help_text="User associated with this event (null for anonymous events)"
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        help_text="Django session key"
    )
    
    # Request information
    ip_address = models.GenericIPAddressField(
        help_text="IP address of the request"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string from the request"
    )
    request_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Requested URL path"
    )
    request_method = models.CharField(
        max_length=10,
        blank=True,
        help_text="HTTP method (GET, POST, etc.)"
    )
    
    # Event details
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional event details in JSON format"
    )
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium',
        help_text="Severity level of this event"
    )
    
    # Resolution information
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether this security event has been resolved"
    )
    resolved_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_security_events',
        help_text="User who resolved this event"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this event was resolved"
    )
    resolution_notes = models.TextField(
        blank=True,
        help_text="Notes about how this event was resolved"
    )

    class Meta:
        verbose_name = "Security Event"
        verbose_name_plural = "Security Events"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['severity', 'created_at']),
            models.Index(fields=['is_resolved']),
        ]

    def __str__(self):
        user_info = self.user.username if self.user else "Anonymous"
        return f"{self.event_type} - {user_info} ({self.ip_address})"

    def resolve(self, resolved_by_user, notes=""):
        """Mark this security event as resolved."""
        from django.utils import timezone
        self.is_resolved = True
        self.resolved_by = resolved_by_user
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save()
