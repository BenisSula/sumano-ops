"""
Pilot Acceptance views for the Sumano Operations Management System.

This module provides API endpoints for managing pilot acceptance workflows,
including checklist management, signature capture, and PDF generation.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from apps.core.models import PilotAcceptance, Project, DocumentInstance
from apps.core.serializers.pilot_acceptance import (
    PilotAcceptanceSerializer, PilotAcceptanceCreateSerializer, PilotAcceptanceSignatureSerializer
)
from apps.core.authentication.permissions import (
    IsAuthenticatedUser, CanViewProjects, CanManageProjects, IsStaff
)
from apps.core.services.pdf_service import PDFGenerationService
from apps.core.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class PilotAcceptanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for pilot acceptance workflows.
    Supports checklist management, signature capture, and PDF generation.
    """
    
    queryset = PilotAcceptance.objects.all().select_related(
        'project', 'project__client', 'project__client__organization',
        'document_instance', 'created_by'
    ).prefetch_related('project__phases')
    
    serializer_class = PilotAcceptanceSerializer
    permission_classes = [IsAuthenticatedUser, CanViewProjects]
    
    filterset_fields = ['acceptance_status', 'project__status', 'project__service_type']
    search_fields = [
        'project__project_name', 'project__client__organization__name',
        'issues_to_resolve', 'project__client__school_name'
    ]
    ordering_fields = ['created_at', 'completion_date', 'acceptance_status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PilotAcceptanceCreateSerializer
        elif self.action == 'sign_acceptance':
            return PilotAcceptanceSignatureSerializer
        return PilotAcceptanceSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'generate_certificate']:
            self.permission_classes = [IsAuthenticatedUser, CanManageProjects]
        elif self.action in ['list', 'retrieve', 'sign_acceptance']:
            self.permission_classes = [IsAuthenticatedUser, CanViewProjects]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        """Create pilot acceptance record with security logging."""
        pilot_acceptance = serializer.save(created_by=self.request.user)
        
        SecurityService.log_security_event(
            event_type='pilot_acceptance_created',
            user=self.request.user,
            details={
                'pilot_acceptance_id': str(pilot_acceptance.id),
                'project_id': str(pilot_acceptance.project.id),
                'project_name': pilot_acceptance.project.project_name,
                'acceptance_status': pilot_acceptance.acceptance_status
            },
            severity='low'
        )
    
    def perform_update(self, serializer):
        """Update pilot acceptance with security logging."""
        pilot_acceptance = serializer.save()
        
        SecurityService.log_security_event(
            event_type='pilot_acceptance_updated',
            user=self.request.user,
            details={
                'pilot_acceptance_id': str(pilot_acceptance.id),
                'project_id': str(pilot_acceptance.project.id),
                'acceptance_status': pilot_acceptance.acceptance_status
            },
            severity='low'
        )
    
    def perform_destroy(self, instance):
        """Delete pilot acceptance with security logging."""
        project_name = instance.project.project_name
        project_id = str(instance.project.id)
        acceptance_id = str(instance.id)
        
        instance.delete()
        
        SecurityService.log_security_event(
            event_type='pilot_acceptance_deleted',
            user=self.request.user,
            details={
                'pilot_acceptance_id': acceptance_id,
                'project_id': project_id,
                'project_name': project_name
            },
            severity='medium'
        )
    
    @action(detail=True, methods=['post'])
    def sign_acceptance(self, request, pk=None):
        """
        Sign the pilot acceptance document.
        """
        pilot_acceptance = self.get_object()
        
        serializer = PilotAcceptanceSignatureSerializer(
            data=request.data,
            context={'request': request, 'pilot_acceptance': pilot_acceptance}
        )
        
        if serializer.is_valid():
            pilot_acceptance = serializer.save()
            
            SecurityService.log_security_event(
                event_type='pilot_acceptance_signed',
                user=request.user,
                details={
                    'pilot_acceptance_id': str(pilot_acceptance.id),
                    'project_id': str(pilot_acceptance.project.id),
                    'signature_type': 'school_representative' if pilot_acceptance.school_representative_signed else 'company_representative'
                },
                severity='medium'
            )
            
            return Response(
                {
                    'detail': 'Acceptance document signed successfully.',
                    'is_fully_signed': pilot_acceptance.is_fully_signed
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def generate_certificate(self, request, pk=None):
        """
        Generate acceptance certificate PDF.
        """
        pilot_acceptance = self.get_object()
        
        try:
            # Prepare data for PDF generation
            pdf_data = pilot_acceptance._prepare_pdf_data()
            
            # Generate PDF using unified document system
            document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
                template_name='Pilot Acceptance Certificate',
                data=pdf_data,
                user=request.user,
                project=pilot_acceptance.project
            )
            
            SecurityService.log_security_event(
                event_type='pilot_acceptance_certificate_generated',
                user=request.user,
                details={
                    'pilot_acceptance_id': str(pilot_acceptance.id),
                    'project_id': str(pilot_acceptance.project.id),
                    'document_id': str(document_instance.id)
                },
                severity='low'
            )
            
            # Return PDF as response
            response = Response(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Pilot_Acceptance_{pilot_acceptance.project.project_name}.pdf"'
            return response
            
        except ValueError as e:
            logger.error(f"Error generating certificate for pilot acceptance {pilot_acceptance.id}: {e}")
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.exception(f"Unexpected error generating certificate for pilot acceptance {pilot_acceptance.id}: {e}")
            return Response(
                {'detail': 'An unexpected error occurred during certificate generation.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'])
    def update_checklist(self, request, pk=None):
        """
        Update specific checklist items.
        """
        pilot_acceptance = self.get_object()
        checklist_data = request.data.get('checklist', {})
        
        if not checklist_data:
            return Response(
                {'detail': 'Checklist data is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validate checklist fields
            valid_fields = PilotAcceptance.get_checklist_fields()
            invalid_fields = [field for field in checklist_data.keys() if field not in valid_fields]
            
            if invalid_fields:
                return Response(
                    {'detail': f'Invalid checklist fields: {invalid_fields}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update checklist items
            for field_name, value in checklist_data.items():
                pilot_acceptance.update_checklist_item(field_name, value)
            
            SecurityService.log_security_event(
                event_type='pilot_acceptance_checklist_updated',
                user=request.user,
                details={
                    'pilot_acceptance_id': str(pilot_acceptance.id),
                    'project_id': str(pilot_acceptance.project.id),
                    'updated_fields': list(checklist_data.keys())
                },
                severity='low'
            )
            
            # Return updated data
            serializer = self.get_serializer(pilot_acceptance)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error updating checklist for pilot acceptance {pilot_acceptance.id}: {e}")
            return Response(
                {'detail': 'An error occurred while updating checklist.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get pilot acceptance statistics.
        """
        queryset = self.get_queryset()
        
        # Basic statistics
        total_acceptances = queryset.count()
        accepted_count = queryset.filter(acceptance_status='accepted').count()
        accepted_with_conditions_count = queryset.filter(acceptance_status='accepted_with_conditions').count()
        not_accepted_count = queryset.filter(acceptance_status='not_accepted').count()
        
        # Fully signed statistics
        fully_signed_count = queryset.filter(
            school_representative_signed=True,
            company_representative_signed=True
        ).count()
        
        # Completion statistics
        completed_projects = queryset.filter(
            project__status='completed'
        ).count()
        
        return Response({
            'total_acceptances': total_acceptances,
            'accepted_count': accepted_count,
            'accepted_with_conditions_count': accepted_with_conditions_count,
            'not_accepted_count': not_accepted_count,
            'fully_signed_count': fully_signed_count,
            'completed_projects': completed_projects,
            'acceptance_rate': f"{(accepted_count / total_acceptances * 100):.1f}%" if total_acceptances > 0 else "0.0%"
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def pending_signatures(self, request):
        """
        Get acceptances pending signatures.
        """
        user = request.user
        user_role = getattr(user, 'role', None)
        
        if not user_role:
            return Response(
                {'detail': 'User role not found.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset()
        
        if user_role.codename == 'client_contact':
            # School representative - show acceptances they can sign
            pending = queryset.filter(school_representative_signed=False)
        elif user_role.codename in ['staff', 'superadmin']:
            # Company representative - show acceptances they can sign
            pending = queryset.filter(company_representative_signed=False)
        else:
            pending = queryset.none()
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
