"""
Project domain models for Sumano OMS.

This module contains models related to project management and service delivery.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .client import Client, Contact
from .base import TimeStampedModel


class Project(TimeStampedModel):
    """
    Represents a service delivery project for a Sumano Tech client.

    This model tracks our service delivery projects across all service lines
    (web development, mobile apps, OMS, portals, audits).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="projects",
        help_text="Client organization this project is for",
    )

    # Project identification
    project_name = models.CharField(max_length=200, help_text="Name of the project")
    project_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Internal project code (e.g., PROJ-2024-001)",
    )

    # Service information
    service_type = models.CharField(
        max_length=50,
        choices=[
            ("web_development", "Website Development"),
            ("mobile_app", "Mobile Application"),
            ("operations_system", "Operations Management System"),
            ("portal", "Portal Development"),
            ("audit", "System Audit"),
        ],
        help_text="Type of service we are providing",
    )

    # Project details
    description = models.TextField(help_text="Detailed project description and scope")
    objectives = models.TextField(
        blank=True, help_text="Project objectives and success criteria"
    )

    # Timeline and scheduling
    start_date = models.DateField(help_text="Project start date")
    target_end_date = models.DateField(
        null=True, blank=True, help_text="Target project completion date"
    )
    actual_end_date = models.DateField(
        null=True, blank=True, help_text="Actual project completion date"
    )

    # Project management
    project_manager = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_projects",
        help_text="Sumano Tech project manager assigned to this project",
    )
    client_contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_contacts",
        help_text="Primary client contact for this project",
    )

    # Status and progress
    status = models.CharField(
        max_length=50,
        choices=[
            ("lead", "Lead"),
            ("quoted", "Quoted"),
            ("approved", "Approved"),
            ("planning", "Planning"),
            ("development", "Development"),
            ("testing", "Testing"),
            ("client_review", "Client Review"),
            ("completed", "Completed"),
            ("on_hold", "On Hold"),
        ],
        default="lead",
        help_text="Current status of the project",
    )
    progress_percentage = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0,
        help_text="Project completion percentage (0-100)",
    )

    # Priority and timing
    priority = models.CharField(
        max_length=20,
        choices=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        default="medium",
        help_text="Project priority level",
    )
    status_updated_at = models.DateTimeField(
        auto_now=True, help_text="Last time the project status was updated"
    )

    # Financial information
    estimated_hours = models.PositiveIntegerField(
        null=True, blank=True, help_text="Estimated total hours for this project"
    )
    actual_hours = models.PositiveIntegerField(
        default=0, help_text="Actual hours spent on this project"
    )
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Project budget in USD",
    )
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual project cost in USD",
    )

    # Risk assessment
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        default="medium",
        help_text="Project risk assessment",
    )

    # Notes and documentation
    notes = models.TextField(blank=True, help_text="Internal project notes and updates")
    deliverables = models.TextField(
        blank=True, help_text="List of project deliverables"
    )

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client"]),
            models.Index(fields=["status"]),
            models.Index(fields=["service_type"]),
            models.Index(fields=["start_date"]),
            models.Index(fields=["project_code"]),
        ]

    def __str__(self):
        return f"{self.project_name} - {self.client.organization.name}"

    @property
    def client_name(self):
        """Return the client organization name."""
        return self.client.organization.name

    @property
    def is_active(self):
        """Check if the project is currently active."""
        return self.status in [
            "planning",
            "in_progress",
            "review",
            "testing",
            "ongoing_support",
        ]

    @property
    def is_overdue(self):
        """Check if the project is overdue."""
        if not self.target_end_date:
            return False
        from django.utils import timezone

        return self.target_end_date < timezone.now().date() and self.status not in [
            "completed",
            "cancelled",
        ]


class ProjectPhase(TimeStampedModel):
    """
    Represents phases within a project for detailed project management.

    This model allows breaking down projects into manageable phases
    for better tracking and delivery.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="phases",
        help_text="Project this phase belongs to",
    )

    # Phase identification
    phase_name = models.CharField(
        max_length=200, help_text="Name of this project phase"
    )
    phase_number = models.PositiveIntegerField(
        help_text="Sequential number of this phase within the project"
    )

    # Phase details
    description = models.TextField(help_text="Description of what this phase entails")
    deliverables = models.TextField(
        blank=True, help_text="Specific deliverables for this phase"
    )

    # Timeline
    start_date = models.DateField(help_text="Phase start date")
    target_end_date = models.DateField(help_text="Target phase completion date")
    actual_end_date = models.DateField(
        null=True, blank=True, help_text="Actual phase completion date"
    )

    # Status and progress
    status = models.CharField(
        max_length=50,
        choices=[
            ("not_started", "Not Started"),
            ("in_progress", "In Progress"),
            ("review", "Under Review"),
            ("completed", "Completed"),
            ("on_hold", "On Hold"),
            ("cancelled", "Cancelled"),
        ],
        default="not_started",
        help_text="Current status of this phase",
    )
    progress_percentage = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0,
        help_text="Phase completion percentage (0-100)",
    )

    # Resource allocation
    estimated_hours = models.PositiveIntegerField(
        null=True, blank=True, help_text="Estimated hours for this phase"
    )
    actual_hours = models.PositiveIntegerField(
        null=True, blank=True, help_text="Actual hours spent on this phase"
    )

    # Dependencies
    depends_on = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="dependent_phases",
        help_text="Other phases that must be completed before this phase",
    )

    # Notes
    notes = models.TextField(blank=True, help_text="Phase-specific notes and updates")

    class Meta:
        verbose_name = "Project Phase"
        verbose_name_plural = "Project Phases"
        ordering = ["project", "phase_number"]
        unique_together = [
            [
                "project",
                "phase_number",
            ],  # Each project can have only one phase with a given number
        ]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["start_date"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return (
            f"{self.project.project_name} - Phase {self.phase_number}: "
            f"{self.phase_name}"
        )

    @property
    def is_active(self):
        """Check if this phase is currently active."""
        return self.status in ["in_progress", "review"]

    @property
    def is_overdue(self):
        """Check if this phase is overdue."""
        from django.utils import timezone

        return self.target_end_date < timezone.now().date() and self.status not in [
            "completed",
            "cancelled",
        ]


class StatusTransition(TimeStampedModel):
    """
    Audit trail for project status transitions.

    This model tracks all status changes for projects, providing
    a complete audit trail of project lifecycle progression.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="status_transitions",
        help_text="Project that underwent status change",
    )

    # Status transition details
    from_status = models.CharField(
        max_length=50, help_text="Previous status of the project"
    )
    to_status = models.CharField(max_length=50, help_text="New status of the project")

    # Audit information
    user = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changes",
        help_text="User who made the status change",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True, help_text="When the status change occurred"
    )

    # Additional context
    reason = models.TextField(blank=True, help_text="Reason for the status change")
    notes = models.TextField(
        blank=True, help_text="Additional notes about the status change"
    )

    class Meta:
        verbose_name = "Status Transition"
        verbose_name_plural = "Status Transitions"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["project", "timestamp"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["from_status", "to_status"]),
        ]

    def __str__(self):
        return f"{self.project.project_name}: {self.from_status} → {self.to_status}"
