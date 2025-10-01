"""
Core models package for Sumano OMS.

This package contains all the normalized data models for the operations management system.
Models are organized by domain to maintain clear separation of concerns.
"""

# Import all models for easy access
from .base import TimeStampedModel
from .client import Client, Organization, Contact
from .project import Project, ProjectPhase, StatusTransition
from .document import DocumentTemplate, DocumentInstance
from .pilot_acceptance import PilotAcceptance
from .change_request import ChangeRequest
from .pilot_handover import PilotHandover
from .attachment import Attachment
from .system import User, Role, Permission, SecurityEvent

__all__ = [
    # Base models
    'TimeStampedModel',
    # Client domain
    'Client',
    'Organization', 
    'Contact',
    # Project domain
    'Project',
    'ProjectPhase',
    'StatusTransition',
    # Document domain
    'DocumentTemplate',
    'DocumentInstance',
    # Pilot Acceptance domain
    'PilotAcceptance',
    # Change Request domain
    'ChangeRequest',
    # Pilot Handover domain
    'PilotHandover',
    # File Management domain
    'Attachment',
    # System domain
    'User',
    'Role',
    'Permission',
    'SecurityEvent',
]
