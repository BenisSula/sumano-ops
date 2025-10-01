"""
Serializers for Attachment functionality.
"""
import os
from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ValidationError
from django.conf import settings

from apps.core.models import Attachment, Project
from apps.core.authentication.permissions import IsAuthenticatedUser


class AttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Attachment model.
    Includes file metadata and project information.
    """
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    project_code = serializers.CharField(source='project.project_code', read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    uploaded_by_email = serializers.CharField(source='uploaded_by.email', read_only=True)
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    file_extension = serializers.CharField(source='get_file_extension', read_only=True)
    file_url = serializers.CharField(source='get_file_url', read_only=True)
    can_be_deleted = serializers.SerializerMethodField()
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    
    class Meta:
        model = Attachment
        fields = [
            'id', 'file', 'file_name', 'file_type', 'file_type_display', 'file_size',
            'file_size_display', 'mime_type', 'description', 'project', 'project_name',
            'project_code', 'uploaded_by', 'uploaded_by_username', 'uploaded_by_email',
            'download_count', 'last_downloaded_at', 'is_active', 'file_extension',
            'file_url', 'can_be_deleted', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_name', 'file_type', 'file_size', 'mime_type', 'project_name',
            'project_code', 'uploaded_by', 'uploaded_by_username', 'uploaded_by_email',
            'download_count', 'last_downloaded_at', 'file_extension', 'file_url',
            'can_be_deleted', 'created_at', 'updated_at'
        ]
    
    def get_can_be_deleted(self, obj):
        """Check if the current user can delete this attachment."""
        request = self.context.get('request')
        if request and request.user:
            return obj.can_be_deleted_by(request.user)
        return False


class AttachmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new attachments.
    Handles file upload with validation and project context.
    """
    project_id = serializers.UUIDField(write_only=True, help_text="UUID of the project to attach this file to")
    
    class Meta:
        model = Attachment
        fields = [
            'id', 'file', 'project_id', 'description', 'file_name', 'file_type', 'file_size'
        ]
        read_only_fields = ['id', 'file_name', 'file_type', 'file_size']
    
    def validate_project_id(self, value):
        """Validate that the project exists and user has access."""
        try:
            project = Project.objects.get(id=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project with this ID does not exist.")
        
        # Check if user has access to this project
        request = self.context.get('request')
        if request and request.user:
            # For now, allow all authenticated users to upload to any project
            # In a real implementation, this would check project-specific permissions
            pass
        
        return value
    
    def validate_file(self, value):
        """Validate uploaded file."""
        if not value:
            raise serializers.ValidationError("No file provided.")
        
        # Check file size (default limit is 10MB)
        max_size = getattr(settings, 'MAX_FILE_SIZE', Attachment.DEFAULT_SIZE_LIMIT)
        if value.size > max_size:
            size_mb = max_size / (1024 * 1024)
            raise serializers.ValidationError(f"File size exceeds the maximum limit of {size_mb:.1f} MB.")
        
        # Check file extension
        file_extension = os.path.splitext(value.name)[1].lower()
        allowed_extensions = [
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg',
            # PDFs
            '.pdf',
            # Documents
            '.doc', '.docx', '.txt', '.rtf', '.odt',
            # Spreadsheets
            '.xls', '.xlsx', '.csv', '.ods',
            # Presentations
            '.ppt', '.pptx', '.odp',
            # Archives
            '.zip', '.rar', '.7z', '.tar', '.gz',
        ]
        
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(f"File type '{file_extension}' is not allowed.")
        
        # Check for potentially dangerous files
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js']
        if file_extension in dangerous_extensions:
            raise serializers.ValidationError("Executable files are not allowed for security reasons.")
        
        return value
    
    def create(self, validated_data):
        """Create new attachment with proper project context."""
        project_id = validated_data.pop('project_id')
        project = Project.objects.get(id=project_id)
        user = self.context['request'].user
        
        # Create attachment
        attachment = Attachment.objects.create(
            project=project,
            uploaded_by=user,
            **validated_data
        )
        
        # Return the created attachment with full data
        return attachment


class AttachmentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating attachment metadata.
    Only allows updating description and is_active status.
    """
    
    class Meta:
        model = Attachment
        fields = ['description', 'is_active']
    
    def validate(self, data):
        """Validate update permissions."""
        request = self.context.get('request')
        if request and request.user:
            if not self.instance.can_be_deleted_by(request.user):
                raise serializers.ValidationError("You don't have permission to modify this attachment.")
        return data


class AttachmentDownloadSerializer(serializers.Serializer):
    """
    Serializer for file download requests.
    Validates download permissions and records access.
    """
    attachment_id = serializers.UUIDField()
    
    def validate_attachment_id(self, value):
        """Validate that attachment exists and user can access it."""
        try:
            attachment = Attachment.objects.get(id=value)
        except Attachment.DoesNotExist:
            raise serializers.ValidationError("Attachment not found.")
        
        # Check access permissions
        request = self.context.get('request')
        if request and request.user:
            if not attachment.can_be_accessed_by(request.user):
                raise serializers.ValidationError("You don't have permission to download this file.")
        
        return value


class AttachmentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for attachment lists.
    Optimized for performance with minimal data.
    """
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    file_extension = serializers.CharField(source='get_file_extension', read_only=True)
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    
    class Meta:
        model = Attachment
        fields = [
            'id', 'file_name', 'file_type', 'file_type_display', 'file_size_display',
            'file_extension', 'description', 'project_name', 'uploaded_by_username',
            'download_count', 'is_active', 'created_at'
        ]


class FileUploadProgressSerializer(serializers.Serializer):
    """
    Serializer for tracking file upload progress.
    Used for real-time upload status updates.
    """
    upload_id = serializers.UUIDField()
    filename = serializers.CharField()
    progress = serializers.IntegerField(min_value=0, max_value=100)
    status = serializers.ChoiceField(choices=[
        ('uploading', 'Uploading'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    error_message = serializers.CharField(required=False, allow_blank=True)


class AttachmentStatsSerializer(serializers.Serializer):
    """
    Serializer for attachment statistics.
    Provides summary information about file usage.
    """
    total_files = serializers.IntegerField()
    total_size = serializers.IntegerField()
    total_size_display = serializers.CharField()
    files_by_type = serializers.DictField()
    recent_uploads = serializers.IntegerField()
    most_downloaded = serializers.ListField(child=serializers.DictField())
