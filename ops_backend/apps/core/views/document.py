"""
Document API views for the Sumano Operations Management System.

This module provides API endpoints for document template management and
PDF generation, with full authentication and authorization support.
"""

import logging
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.auth import get_user_model

from apps.core.models import DocumentTemplate, DocumentInstance, Project
from apps.core.serializers.document import (
    DocumentTemplateSerializer,
    DocumentInstanceSerializer,
    DocumentGenerationSerializer
)
from apps.core.authentication.permissions import (
    IsAuthenticatedUser,
    CanViewDocuments,
    CanManageDocuments,
    CanApproveDocuments
)
from apps.core.services.pdf_service import PDFGenerationService
from apps.core.services.security_service import SecurityService

User = get_user_model()
logger = logging.getLogger(__name__)


class DocumentTemplateListView(generics.ListAPIView):
    """
    List document templates by type.
    
    GET /api/document-templates/
    """
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAuthenticatedUser, CanViewDocuments]
    
    def get_queryset(self):
        """Filter templates by type and status."""
        queryset = DocumentTemplate.objects.filter(status='PUBLISHED')
        
        template_type = self.request.query_params.get('type', None)
        if template_type:
            queryset = queryset.filter(template_type=template_type)
        
        return queryset.order_by('template_type', 'name')


class DocumentTemplateDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific document template.
    
    GET /api/document-templates/{id}/
    """
    queryset = DocumentTemplate.objects.filter(status='PUBLISHED')
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAuthenticatedUser, CanViewDocuments]


class DocumentTemplateCreateView(generics.CreateAPIView):
    """
    Create a new document template.
    
    POST /api/document-templates/
    """
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAuthenticatedUser, CanManageDocuments]
    
    def perform_create(self, serializer):
        """Set the creator of the template."""
        serializer.save(created_by=self.request.user)


class DocumentTemplateUpdateView(generics.UpdateAPIView):
    """
    Update a document template.
    
    PUT/PATCH /api/document-templates/{id}/
    """
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAuthenticatedUser, CanManageDocuments]
    
    def perform_update(self, serializer):
        """Update the template with audit information."""
        serializer.save()


class DocumentInstanceListView(generics.ListAPIView):
    """
    List document instances for a project.
    
    GET /api/documents/
    """
    serializer_class = DocumentInstanceSerializer
    permission_classes = [IsAuthenticatedUser, CanViewDocuments]
    
    def get_queryset(self):
        """Filter documents by project."""
        queryset = DocumentInstance.objects.select_related('template', 'project', 'created_by')
        
        project_id = self.request.query_params.get('project', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        template_type = self.request.query_params.get('type', None)
        if template_type:
            queryset = queryset.filter(template__template_type=template_type)
        
        return queryset.order_by('-created_at')


class DocumentInstanceDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific document instance.
    
    GET /api/documents/{id}/
    """
    queryset = DocumentInstance.objects.select_related('template', 'project', 'created_by')
    serializer_class = DocumentInstanceSerializer
    permission_classes = [IsAuthenticatedUser, CanViewDocuments]


@api_view(['POST'])
@permission_classes([IsAuthenticatedUser, CanManageDocuments])
def generate_document(request):
    """
    Generate a new document from a template.
    
    POST /api/documents/generate/
    """
    serializer = DocumentGenerationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get template and project
        template_name = serializer.validated_data['template_name']
        project_id = serializer.validated_data.get('project_id')
        data = serializer.validated_data['data']
        signature_context = serializer.validated_data.get('signature_context')
        
        # Get project if specified
        project = None
        if project_id:
            project = get_object_or_404(Project, id=project_id)
        
        # Generate document
        document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
            template_name=template_name,
            data=data,
            signature_context=signature_context,
            user=request.user,
            project=project
        )
        
        # Store audited copy
        audit_path = PDFGenerationService.store_audited_copy(
            pdf_bytes=pdf_bytes,
            metadata={
                'template_name': template_name,
                'template_type': document_instance.template.template_type,
                'project_id': str(project.id) if project else None,
                'user_id': str(request.user.id),
            },
            user=request.user
        )
        
        # Return document instance
        response_serializer = DocumentInstanceSerializer(document_instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Document generation failed: {str(e)}")
        return Response(
            {'error': 'Document generation failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticatedUser, CanViewDocuments])
def download_pdf(request, document_id):
    """
    Download a generated PDF document.
    
    GET /api/documents/{id}/pdf/
    """
    try:
        document = get_object_or_404(DocumentInstance, id=document_id)
        
        # Check if PDF file exists
        if not document.generated_pdf:
            return Response(
                {'error': 'PDF file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Log download event
        SecurityService.log_security_event(
            event_type='document_downloaded',
            user=request.user,
            ip_address=SecurityService.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method,
            details={
                'document_id': str(document.id),
                'template_type': document.template.template_type,
                'project_id': str(document.project.id) if document.project else None,
            },
            severity='low'
        )
        
        # Return PDF file
        response = HttpResponse(
            document.generated_pdf.read(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{document.document_number}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"PDF download failed: {str(e)}")
        return Response(
            {'error': 'PDF download failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticatedUser, CanApproveDocuments])
def sign_document(request, document_id):
    """
    Sign a document.
    
    POST /api/documents/{id}/sign/
    """
    try:
        document = get_object_or_404(DocumentInstance, id=document_id)
        
        # Check if document can be signed
        if not document.can_be_signed():
            return Response(
                {'error': 'Document cannot be signed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Sign the document
        document.sign(request.user)
        
        # Log signing event
        SecurityService.log_security_event(
            event_type='document_signed',
            user=request.user,
            ip_address=SecurityService.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method,
            details={
                'document_id': str(document.id),
                'template_type': document.template.template_type,
                'project_id': str(document.project.id) if document.project else None,
            },
            severity='medium'
        )
        
        # Return updated document
        serializer = DocumentInstanceSerializer(document)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Document signing failed: {str(e)}")
        return Response(
            {'error': 'Document signing failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticatedUser, CanViewDocuments])
def document_statistics(request):
    """
    Get document generation statistics.
    
    GET /api/documents/statistics/
    """
    try:
        stats = PDFGenerationService.get_performance_statistics()
        
        # Add additional statistics
        stats.update({
            'total_templates': DocumentTemplate.objects.filter(status='PUBLISHED').count(),
            'total_documents': DocumentInstance.objects.count(),
            'signed_documents': DocumentInstance.objects.filter(status='SIGNED').count(),
        })
        
        return Response(stats, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to get document statistics: {str(e)}")
        return Response(
            {'error': 'Failed to get statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
