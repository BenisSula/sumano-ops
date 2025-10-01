"""
Project status management service for Sumano OMS.

This service handles project status transitions, validation, and progress tracking
across all service lines.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import Project, StatusTransition


class ProjectStatusService:
    """
    Service for managing project status transitions and tracking.

    This service provides methods for:
    - Validating status transitions
    - Executing status changes with audit trail
    - Calculating project progress
    - Aggregating service type statistics
    """

    # Valid status transition paths
    VALID_TRANSITIONS = {
        "lead": ["quoted", "on_hold"],
        "quoted": ["lead", "approved", "on_hold"],
        "approved": ["quoted", "planning", "on_hold"],
        "planning": ["approved", "development", "on_hold"],
        "development": ["planning", "testing", "on_hold"],
        "testing": ["development", "client_review", "on_hold"],
        "client_review": ["testing", "completed", "on_hold"],
        "completed": ["client_review"],  # Can only go back to client_review
        "on_hold": [
            "lead",
            "quoted",
            "approved",
            "planning",
            "development",
            "testing",
            "client_review",
        ],
    }

    # Status to progress percentage mapping
    STATUS_PROGRESS_MAP = {
        "lead": 0,
        "quoted": 5,
        "approved": 10,
        "planning": 20,
        "development": 50,
        "testing": 80,
        "client_review": 95,
        "completed": 100,
        "on_hold": None,  # Progress remains unchanged
    }

    @classmethod
    def validate_status_transition(cls, current_status, new_status):
        """
        Validate if a status transition is allowed.

        Args:
            current_status (str): Current project status
            new_status (str): Desired new status

        Returns:
            bool: True if transition is valid, False otherwise

        Raises:
            ValidationError: If transition is invalid
        """
        if current_status == new_status:
            return True  # No change needed

        valid_next_statuses = cls.VALID_TRANSITIONS.get(current_status, [])

        if new_status not in valid_next_statuses:
            raise ValidationError(
                f"Invalid status transition from '{current_status}' to '{new_status}'. "
                f"Valid transitions: {valid_next_statuses}"
            )

        return True

    @classmethod
    @transaction.atomic
    def transition_status(cls, project, new_status, user=None, reason="", notes=""):
        """
        Transition a project to a new status with full audit trail.

        Args:
            project (Project): The project to transition
            new_status (str): The new status
            user (User, optional): User making the change
            reason (str): Reason for the status change
            notes (str): Additional notes

        Returns:
            StatusTransition: The created status transition record

        Raises:
            ValidationError: If transition is invalid
        """
        old_status = project.status

        # Validate the transition
        cls.validate_status_transition(old_status, new_status)

        # Update project status
        project.status = new_status

        # Update progress percentage if applicable
        progress = cls.STATUS_PROGRESS_MAP.get(new_status)
        if progress is not None:
            project.progress_percentage = progress

        # Update status timestamp
        project.status_updated_at = timezone.now()

        # Save the project
        project.save(
            update_fields=["status", "progress_percentage", "status_updated_at"]
        )

        # Create audit trail
        transition = StatusTransition.objects.create(
            project=project,
            from_status=old_status,
            to_status=new_status,
            user=user,
            reason=reason,
            notes=notes,
        )

        return transition

    @classmethod
    def calculate_progress(cls, project):
        """
        Calculate project progress based on phases and documents.

        Args:
            project (Project): The project to calculate progress for

        Returns:
            int: Progress percentage (0-100)
        """
        # Get all project phases
        phases = project.phases.all()
        if not phases.exists():
            # No phases, use status-based progress
            return cls.STATUS_PROGRESS_MAP.get(project.status, 0)

        # Calculate progress based on completed phases
        total_phases = phases.count()
        completed_phases = phases.filter(status="completed").count()

        if total_phases == 0:
            return 0

        phase_progress = (completed_phases / total_phases) * 100

        # Get document completion status
        documents = project.documents.all()
        if documents.exists():
            total_docs = documents.count()
            completed_docs = documents.filter(
                status__in=["final", "client_approved"]
            ).count()
            doc_progress = (completed_docs / total_docs) * 100

            # Weight phases 70% and documents 30%
            overall_progress = (phase_progress * 0.7) + (doc_progress * 0.3)
        else:
            overall_progress = phase_progress

        return min(100, max(0, int(overall_progress)))

    @classmethod
    def update_progress(cls, project):
        """
        Update project progress percentage based on current state.

        Args:
            project (Project): The project to update
        """
        new_progress = cls.calculate_progress(project)
        if new_progress != project.progress_percentage:
            project.progress_percentage = new_progress
            project.status_updated_at = timezone.now()
            project.save(update_fields=["progress_percentage", "status_updated_at"])

    @classmethod
    def get_service_type_stats(cls):
        """
        Get aggregated statistics by service type.

        Returns:
            dict: Statistics for each service type
        """
        from django.db.models import Avg, Sum

        stats = {}

        # Get all projects grouped by service type
        service_types = Project._meta.get_field("service_type").choices

        for service_code, service_name in service_types:
            projects = Project.objects.filter(service_type=service_code)

            stats[service_code] = {
                "name": service_name,
                "total_projects": projects.count(),
                "active_projects": projects.filter(
                    status__in=[
                        "lead",
                        "quoted",
                        "approved",
                        "planning",
                        "development",
                        "testing",
                        "client_review",
                    ]
                ).count(),
                "completed_projects": projects.filter(status="completed").count(),
                "on_hold_projects": projects.filter(status="on_hold").count(),
                "avg_progress": projects.aggregate(avg=Avg("progress_percentage"))[
                    "avg"
                ]
                or 0,
                "total_estimated_hours": projects.aggregate(
                    total=Sum("estimated_hours")
                )["total"]
                or 0,
                "total_actual_hours": projects.aggregate(total=Sum("actual_hours"))[
                    "total"
                ]
                or 0,
            }

        return stats

    @classmethod
    def get_status_distribution(cls):
        """
        Get distribution of projects by status.

        Returns:
            dict: Count of projects for each status
        """
        distribution = {}

        for status_code, status_name in Project._meta.get_field("status").choices:
            count = Project.objects.filter(status=status_code).count()
            distribution[status_code] = {"name": status_name, "count": count}

        return distribution

    @classmethod
    def get_priority_distribution(cls):
        """
        Get distribution of projects by priority.

        Returns:
            dict: Count of projects for each priority level
        """
        distribution = {}

        for priority_code, priority_name in Project._meta.get_field("priority").choices:
            count = Project.objects.filter(priority=priority_code).count()
            distribution[priority_code] = {"name": priority_name, "count": count}

        return distribution

    @classmethod
    def get_overdue_projects(cls):
        """
        Get list of projects that are overdue.

        Returns:
            QuerySet: Projects that are overdue
        """
        from django.utils import timezone

        today = timezone.now().date()

        return Project.objects.filter(
            target_end_date__lt=today,
            status__in=["planning", "development", "testing", "client_review"],
        ).order_by("target_end_date")

    @classmethod
    def get_project_timeline(cls, project):
        """
        Get timeline of status transitions for a project.

        Args:
            project (Project): The project to get timeline for

        Returns:
            QuerySet: Status transitions ordered by timestamp
        """
        return project.status_transitions.all().order_by("timestamp")
