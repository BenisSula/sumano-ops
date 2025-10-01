"""
Base models for the Sumano Operations Management System.

This module provides common base model classes that are used across
all other model modules in the system.
"""

import uuid
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides created_at and updated_at timestamps.
    
    This model should be inherited by all models that need automatic
    timestamp tracking for creation and modification times.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Override save to ensure updated_at is always set."""
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
