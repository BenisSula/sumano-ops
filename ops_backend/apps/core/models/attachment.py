"""
Attachment models for the Sumano Operations Management System.

This module provides models for file attachments and management,
leveraging the unified storage system for secure file handling.
"""

import uuid
import os
from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.files.storage import default_storage
from django.utils import timezone
from django.conf import settings

from .base import TimeStampedModel


class Attachment(TimeStampedModel):
    """
    Attachment model for file management and storage.
    
    This model handles file uploads, metadata storage, and provides
    secure access to files with proper permission controls.
    """
    
    # File type choices for validation
    ALLOWED_FILE_TYPES = [
        ('image', 'Image Files'),
        ('pdf', 'PDF Documents'),
        ('document', 'Document Files'),
        ('spreadsheet', 'Spreadsheet Files'),
        ('presentation', 'Presentation Files'),
        ('archive', 'Archive Files'),
        ('other', 'Other Files'),
    ]
    
    # Default file size limit (10MB)
    DEFAULT_SIZE_LIMIT = 10 * 1024 * 1024  # 10MB in bytes
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # File storage
    file = models.FileField(
        upload_to='attachments/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    # Images
                    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg',
                    # PDFs
                    'pdf',
                    # Documents
                    'doc', 'docx', 'txt', 'rtf', 'odt',
                    # Spreadsheets
                    'xls', 'xlsx', 'csv', 'ods',
                    # Presentations
                    'ppt', 'pptx', 'odp',
                    # Archives
                    'zip', 'rar', '7z', 'tar', 'gz',
                ]
            )
        ],
        help_text="Uploaded file with unified storage"
    )
    
    # File metadata
    file_name = models.CharField(
        max_length=255,
        help_text="Original filename of the uploaded file"
    )
    file_type = models.CharField(
        max_length=50,
        choices=ALLOWED_FILE_TYPES,
        help_text="Categorized file type for filtering and validation"
    )
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type of the file"
    )
    
    # File description
    description = models.TextField(
        blank=True,
        help_text="Optional description of the file"
    )
    
    # Relationships
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='attachments',
        help_text="Project this file is attached to"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_attachments',
        help_text="User who uploaded this file"
    )
    
    # Access tracking
    download_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this file has been downloaded"
    )
    last_downloaded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this file was last downloaded"
    )
    
    # File status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this file is active and accessible"
    )
    
    class Meta:
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'created_at']),
            models.Index(fields=['uploaded_by', 'created_at']),
            models.Index(fields=['file_type', 'created_at']),
            models.Index(fields=['is_active', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.file_name} - {self.project.project_name}"
    
    def save(self, *args, **kwargs):
        """Override save to automatically set file metadata."""
        if self.file and not self.file_name:
            self.file_name = os.path.basename(self.file.name)
        
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except (ValueError, OSError):
                self.file_size = 0
        
        if self.file and not self.mime_type:
            self.mime_type = self._get_mime_type()
        
        if self.file and not self.file_type:
            self.file_type = self._categorize_file_type()
        
        super().save(*args, **kwargs)
    
    def _get_mime_type(self):
        """Get MIME type from file extension."""
        if not self.file:
            return ''
        
        extension = os.path.splitext(self.file.name)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.rtf': 'application/rtf',
            '.odt': 'application/vnd.oasis.opendocument.text',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.csv': 'text/csv',
            '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.odp': 'application/vnd.oasis.opendocument.presentation',
            '.zip': 'application/zip',
            '.rar': 'application/vnd.rar',
            '.7z': 'application/x-7z-compressed',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip',
        }
        return mime_types.get(extension, 'application/octet-stream')
    
    def _categorize_file_type(self):
        """Categorize file type based on extension."""
        if not self.file:
            return 'other'
        
        extension = os.path.splitext(self.file.name)[1].lower()
        
        # Image files
        if extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            return 'image'
        
        # PDF files
        elif extension == '.pdf':
            return 'pdf'
        
        # Document files
        elif extension in ['.doc', '.docx', '.txt', '.rtf', '.odt']:
            return 'document'
        
        # Spreadsheet files
        elif extension in ['.xls', '.xlsx', '.csv', '.ods']:
            return 'spreadsheet'
        
        # Presentation files
        elif extension in ['.ppt', '.pptx', '.odp']:
            return 'presentation'
        
        # Archive files
        elif extension in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return 'archive'
        
        else:
            return 'other'
    
    def get_file_size_display(self):
        """Get human-readable file size."""
        if self.file_size == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(self.file_size)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def get_file_url(self):
        """Get the URL for downloading the file."""
        if self.file and hasattr(self.file, 'url'):
            return self.file.url
        return None
    
    def can_be_accessed_by(self, user):
        """Check if user can access this file."""
        if not user or not user.is_authenticated:
            return False
        
        # Check if file is active
        if not self.is_active:
            return False
        
        # Staff and superadmin can access all files
        if hasattr(user, 'role') and user.role.codename in ['staff', 'superadmin']:
            return True
        
        # Client contacts can access files from their projects
        if hasattr(user, 'role') and user.role.codename == 'client_contact':
            # For now, client contacts can access all files
            # In a real implementation, this would check project-specific permissions
            return True
        
        # Uploader can always access their files
        return self.uploaded_by == user
    
    def can_be_deleted_by(self, user):
        """Check if user can delete this file."""
        if not user or not user.is_authenticated:
            return False
        
        # Staff and superadmin can delete any file
        if hasattr(user, 'role') and user.role.codename in ['staff', 'superadmin']:
            return True
        
        # Client contacts can only delete files they uploaded
        if hasattr(user, 'role') and user.role.codename == 'client_contact':
            return self.uploaded_by == user
        
        # Uploader can delete their own files
        return self.uploaded_by == user
    
    def record_download(self, user):
        """Record that this file was downloaded by a user."""
        self.download_count += 1
        self.last_downloaded_at = timezone.now()
        self.save(update_fields=['download_count', 'last_downloaded_at', 'updated_at'])
    
    def get_file_extension(self):
        """Get file extension."""
        if not self.file_name:
            return ''
        return os.path.splitext(self.file_name)[1].lower()
    
    def is_image(self):
        """Check if file is an image."""
        return self.file_type == 'image'
    
    def is_document(self):
        """Check if file is a document."""
        return self.file_type in ['document', 'pdf']
    
    def is_spreadsheet(self):
        """Check if file is a spreadsheet."""
        return self.file_type == 'spreadsheet'
    
    def is_presentation(self):
        """Check if file is a presentation."""
        return self.file_type == 'presentation'
    
    def is_archive(self):
        """Check if file is an archive."""
        return self.file_type == 'archive'
