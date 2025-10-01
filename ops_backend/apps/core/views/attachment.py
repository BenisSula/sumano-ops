"""
Views for Attachment functionality.
"""
import logging
import mimetypes
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.db.models import Q, Sum, Count
from django.utils import timezone

from apps.core.models import Attachment, Project
from apps.core.serializers.attachment import (
    AttachmentSerializer, AttachmentCreateSerializer, AttachmentUpdateSerializer,
    AttachmentDownloadSerializer, AttachmentListSerializer, AttachmentStatsSerializer
)
from apps.core.authentication.permissions import (
    IsAuthenticatedUser, IsStaff
)
from apps.core.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class AttachmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing file attachments.
    Supports upload, download, list, and delete operations with proper security.
    """
    queryset = Attachment.objects.all().select_related(
        'project__client__organization', 'uploaded_by__role'
    )
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticatedUser]
    filterset_fields = ['project', 'file_type', 'uploaded_by', 'is_active']
    search_fields = ['file_name', 'description', 'project__project_name']
    ordering_fields = ['created_at', 'file_name', 'file_size', 'download_count']
    ordering = ['-created_at']
    parser_classes = [MultiPartParser, FormParser]  # Support file uploads

    def get_serializer_class(self):
        if self.action == 'create':
            return AttachmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AttachmentUpdateSerializer
        elif self.action == 'list':
            return AttachmentListSerializer
        elif self.action == 'download':
            return AttachmentDownloadSerializer
        elif self.action == 'stats':
            return AttachmentStatsSerializer
        return AttachmentSerializer

    def get_permissions(self):
        # Different permissions for different actions
        if self.action in ['create', 'upload']:
            # Users can upload files to projects they have access to
            self.permission_classes = [IsAuthenticatedUser]
        elif self.action in ['destroy', 'update', 'partial_update']:
            # Only file owners or staff can modify/delete
            self.permission_classes = [IsAuthenticatedUser]
        elif self.action in ['list', 'retrieve', 'download']:
            # Users can view/download files they have access to
            self.permission_classes = [IsAuthenticatedUser]
        elif self.action in ['stats']:
            # Only staff can view statistics
            self.permission_classes = [IsAuthenticatedUser, IsStaff]
        
        return super().get_permissions()

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Staff and superadmin can see all files
        if hasattr(user, 'role') and user.role.codename in ['staff', 'superadmin']:
            return queryset
        
        # Client contacts can only see files from their projects
        if hasattr(user, 'role') and user.role.codename == 'client_contact':
            # For now, client contacts can see all files
            # In a real implementation, this would filter by project access
            return queryset
        
        # Regular users can only see their own uploaded files
        return queryset.filter(uploaded_by=user)

    def perform_create(self, serializer):
        """Create attachment with security logging."""
        attachment = serializer.save()
        SecurityService.log_security_event(
            event_type='file_uploaded',
            user=self.request.user,
            details={
                'attachment_id': str(attachment.id),
                'project_id': str(attachment.project.id),
                'file_name': attachment.file_name,
                'file_size': attachment.file_size
            },
            severity='low'
        )

    def perform_update(self, serializer):
        """Update attachment with security logging."""
        attachment = serializer.save()
        SecurityService.log_security_event(
            event_type='file_updated',
            user=self.request.user,
            details={
                'attachment_id': str(attachment.id),
                'project_id': str(attachment.project.id),
                'file_name': attachment.file_name
            },
            severity='low'
        )

    def perform_destroy(self, instance):
        """Delete attachment with security logging."""
        # Check if user can delete this attachment
        if not instance.can_be_deleted_by(self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to delete this file.")
        
        attachment_id = str(instance.id)
        project_id = str(instance.project.id)
        file_name = instance.file_name
        
        # Delete the actual file
        if instance.file:
            try:
                instance.file.delete(save=False)
            except Exception as e:
                logger.warning(f"Failed to delete file {instance.file.name}: {e}")
        
        instance.delete()
        SecurityService.log_security_event(
            event_type='file_deleted',
            user=self.request.user,
            details={
                'attachment_id': attachment_id,
                'project_id': project_id,
                'file_name': file_name
            },
            severity='medium'
        )

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticatedUser])
    def download(self, request, pk=None):
        """
        Download a file attachment.
        Validates permissions and records download access.
        """
        attachment = self.get_object()
        
        # Check if user can access this file
        if not attachment.can_be_accessed_by(request.user):
            return Response(
                {'detail': 'You do not have permission to download this file.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if file exists
        if not attachment.file or not attachment.file.name:
            return Response(
                {'detail': 'File not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Record download access
            attachment.record_download(request.user)
            
            # Get file content
            file_path = attachment.file.path
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            # Determine content type
            content_type = mimetypes.guess_type(attachment.file_name)[0] or 'application/octet-stream'
            
            # Create response
            response = HttpResponse(file_content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{attachment.file_name}"'
            response['Content-Length'] = len(file_content)
            
            # Log download
            SecurityService.log_security_event(
                event_type='file_downloaded',
                user=request.user,
                details={
                    'attachment_id': str(attachment.id),
                    'project_id': str(attachment.project.id),
                    'file_name': attachment.file_name
                },
                severity='low'
            )
            
            return response
            
        except FileNotFoundError:
            return Response(
                {'detail': 'File not found on server.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error downloading file {attachment.id}: {e}")
            return Response(
                {'detail': 'Error downloading file.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedUser])
    def by_project(self, request):
        """
        Get all attachments for a specific project.
        Query parameter: project_id
        """
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response(
                {'detail': 'project_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {'detail': 'Project not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check project access
        # For now, allow all authenticated users to access any project
        # In a real implementation, this would check project-specific permissions
        pass
        
        # Get project attachments
        attachments = self.get_queryset().filter(project=project)
        
        # Apply filters and pagination
        attachments = self.filter_queryset(attachments)
        page = self.paginate_queryset(attachments)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(attachments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedUser, IsStaff])
    def stats(self, request):
        """
        Get attachment statistics.
        Only accessible by staff members.
        """
        queryset = self.get_queryset()
        
        # Basic stats
        total_files = queryset.count()
        total_size = queryset.aggregate(total=Sum('file_size'))['total'] or 0
        
        # Files by type
        files_by_type = queryset.values('file_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Recent uploads (last 7 days)
        week_ago = timezone.now() - timezone.timedelta(days=7)
        recent_uploads = queryset.filter(created_at__gte=week_ago).count()
        
        # Most downloaded files
        most_downloaded = queryset.order_by('-download_count')[:10].values(
            'id', 'file_name', 'download_count', 'project__project_name'
        )
        
        # Format total size
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(total_size)
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        total_size_display = f"{size:.1f} {size_names[i]}"
        
        stats_data = {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_display': total_size_display,
            'files_by_type': {item['file_type']: item['count'] for item in files_by_type},
            'recent_uploads': recent_uploads,
            'most_downloaded': list(most_downloaded)
        }
        
        return Response(stats_data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedUser])
    def my_uploads(self, request):
        """
        Get files uploaded by the current user.
        """
        user_uploads = self.get_queryset().filter(uploaded_by=request.user)
        
        # Apply filters and pagination
        user_uploads = self.filter_queryset(user_uploads)
        page = self.paginate_queryset(user_uploads)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(user_uploads, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedUser])
    def recent_downloads(self, request):
        """
        Get recently downloaded files by the current user.
        """
        # This would require a separate model to track user-specific downloads
        # For now, return files that have been downloaded recently
        recent_downloads = self.get_queryset().filter(
            last_downloaded_at__isnull=False
        ).order_by('-last_downloaded_at')[:20]
        
        serializer = self.get_serializer(recent_downloads, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedUser])
    def toggle_active(self, request, pk=None):
        """
        Toggle the active status of an attachment.
        Only the uploader or staff can do this.
        """
        attachment = self.get_object()
        
        if not attachment.can_be_deleted_by(request.user):
            return Response(
                {'detail': 'You do not have permission to modify this attachment.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        attachment.is_active = not attachment.is_active
        attachment.save(update_fields=['is_active', 'updated_at'])
        
        action = 'activated' if attachment.is_active else 'deactivated'
        SecurityService.log_security_event(
            event_type=f'file_{action}',
            user=request.user,
            details={
                'attachment_id': str(attachment.id),
                'project_id': str(attachment.project.id),
                'file_name': attachment.file_name
            },
            severity='low'
        )
        
        return Response({
            'detail': f'File {action} successfully.',
            'is_active': attachment.is_active
        })
