"""
Change Request views for the Sumano Operations Management System.

This module provides API endpoints for managing change request workflows,
including change details, impact assessment, and client decisions.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from apps.core.models import ChangeRequest, Project, DocumentInstance
from apps.core.serializers.change_request import (
    ChangeRequestSerializer, ChangeRequestCreateSerializer, 
    ChangeRequestSignatureSerializer, ImpactAssessmentUpdateSerializer
)
from apps.core.authentication.permissions import (
    IsAuthenticatedUser, CanViewProjects, CanManageProjects, IsStaff
)
from apps.core.services.pdf_service import PDFGenerationService
from apps.core.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class ChangeRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for change request workflows.
    Supports change details, impact assessment, and client decisions.
    """
    
    queryset = ChangeRequest.objects.all().select_related(
        'project', 'project__client', 'project__client__organization',
        'document_instance', 'created_by', 'assessed_by'
    ).prefetch_related('project__phases')
    
    serializer_class = ChangeRequestSerializer
    permission_classes = [IsAuthenticatedUser, CanViewProjects]
    
    filterset_fields = ['status', 'project__status', 'project__service_type', 'client_decision']
    search_fields = [
        'project__project_name', 'project__client__organization__name',
        'reference_agreement', 'document_instance__filled_data'
    ]
    ordering_fields = ['created_at', 'request_date', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ChangeRequestCreateSerializer
        elif self.action == 'sign_change_request':
            return ChangeRequestSignatureSerializer
        elif self.action == 'update_impact_assessment':
            return ImpactAssessmentUpdateSerializer
        return ChangeRequestSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'update_impact_assessment', 'generate_authorization_document']:
            self.permission_classes = [IsAuthenticatedUser, CanManageProjects]
        elif self.action in ['list', 'retrieve', 'sign_change_request']:
            self.permission_classes = [IsAuthenticatedUser, CanViewProjects]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        """Create change request record with security logging."""
        change_request = serializer.save(created_by=self.request.user)
        
        SecurityService.log_security_event(
            event_type='change_request_created',
            user=self.request.user,
            details={
                'change_request_id': str(change_request.id),
                'project_id': str(change_request.project.id),
                'project_name': change_request.project.project_name,
                'status': change_request.status
            },
            severity='low'
        )
    
    def perform_update(self, serializer):
        """Update change request with security logging."""
        change_request = serializer.save()
        
        SecurityService.log_security_event(
            event_type='change_request_updated',
            user=self.request.user,
            details={
                'change_request_id': str(change_request.id),
                'project_id': str(change_request.project.id),
                'status': change_request.status
            },
            severity='low'
        )
    
    def perform_destroy(self, instance):
        """Delete change request with security logging."""
        project_name = instance.project.project_name
        project_id = str(instance.project.id)
        change_request_id = str(instance.id)
        
        instance.delete()
        
        SecurityService.log_security_event(
            event_type='change_request_deleted',
            user=self.request.user,
            details={
                'change_request_id': change_request_id,
                'project_id': project_id,
                'project_name': project_name
            },
            severity='medium'
        )
    
    @action(detail=True, methods=['post'])
    def update_impact_assessment(self, request, pk=None):
        """
        Update impact assessment for a change request.
        """
        change_request = self.get_object()
        
        serializer = ImpactAssessmentUpdateSerializer(
            data=request.data,
            context={'request': request, 'change_request': change_request}
        )
        
        if serializer.is_valid():
            change_request = serializer.save()
            
            SecurityService.log_security_event(
                event_type='change_request_impact_assessed',
                user=request.user,
                details={
                    'change_request_id': str(change_request.id),
                    'project_id': str(change_request.project.id),
                    'assessed_by': request.user.username
                },
                severity='medium'
            )
            
            return Response(
                {
                    'detail': 'Impact assessment updated successfully.',
                    'is_ready_for_client_decision': change_request.is_ready_for_client_decision
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def sign_change_request(self, request, pk=None):
        """
        Sign the change request document.
        """
        change_request = self.get_object()
        
        serializer = ChangeRequestSignatureSerializer(
            data=request.data,
            context={'request': request, 'change_request': change_request}
        )
        
        if serializer.is_valid():
            change_request = serializer.save()
            
            SecurityService.log_security_event(
                event_type='change_request_signed',
                user=request.user,
                details={
                    'change_request_id': str(change_request.id),
                    'project_id': str(change_request.project.id),
                    'signature_type': 'client_representative' if change_request.client_rep_signed else 'provider_representative'
                },
                severity='medium'
            )
            
            return Response(
                {
                    'detail': 'Change request document signed successfully.',
                    'is_fully_signed': change_request.is_fully_signed
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def generate_authorization_document(self, request, pk=None):
        """
        Generate change authorization PDF.
        """
        change_request = self.get_object()
        
        try:
            # Prepare data for PDF generation
            pdf_data = change_request._prepare_pdf_data()
            
            # Generate PDF using unified document system
            document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
                template_name='Change Request Authorization',
                data=pdf_data,
                user=request.user,
                project=change_request.project
            )
            
            SecurityService.log_security_event(
                event_type='change_request_authorization_generated',
                user=request.user,
                details={
                    'change_request_id': str(change_request.id),
                    'project_id': str(change_request.project.id),
                    'document_id': str(document_instance.id)
                },
                severity='low'
            )
            
            # Return PDF as response
            response = Response(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Change_Request_{change_request.project.project_name}.pdf"'
            return response
            
        except ValueError as e:
            logger.error(f"Error generating authorization document for change request {change_request.id}: {e}")
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.exception(f"Unexpected error generating authorization document for change request {change_request.id}: {e}")
            return Response(
                {'detail': 'An unexpected error occurred during document generation.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'])
    def submit_for_review(self, request, pk=None):
        """
        Submit change request for review.
        """
        change_request = self.get_object()
        
        if change_request.status != 'draft':
            return Response(
                {'detail': 'Only draft change requests can be submitted for review.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status to submitted
        change_request.status = 'submitted'
        change_request.save(update_fields=['status'])
        
        SecurityService.log_security_event(
            event_type='change_request_submitted',
            user=request.user,
            details={
                'change_request_id': str(change_request.id),
                'project_id': str(change_request.project.id)
            },
            severity='low'
        )
        
        return Response(
            {'detail': 'Change request submitted for review successfully.'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['patch'])
    def make_client_decision(self, request, pk=None):
        """
        Record client decision on change request.
        """
        change_request = self.get_object()
        
        if not change_request.is_ready_for_client_decision:
            return Response(
                {'detail': 'Change request must be impact assessed before client decision.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        decision = request.data.get('decision')
        if decision not in [choice[0] for choice in ChangeRequest.DECISION_CHOICES]:
            return Response(
                {'detail': f'Invalid decision. Must be one of: {[choice[0] for choice in ChangeRequest.DECISION_CHOICES]}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update client decision
        change_request.client_decision = decision
        change_request.status = 'client_decision'
        change_request.save(update_fields=['client_decision', 'status'])
        
        SecurityService.log_security_event(
            event_type='change_request_client_decision',
            user=request.user,
            details={
                'change_request_id': str(change_request.id),
                'project_id': str(change_request.project.id),
                'decision': decision
            },
            severity='medium'
        )
        
        return Response(
            {'detail': f'Client decision recorded: {change_request.get_client_decision_display()}'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get change request statistics.
        """
        queryset = self.get_queryset()
        
        # Basic statistics
        total_requests = queryset.count()
        draft_count = queryset.filter(status='draft').count()
        submitted_count = queryset.filter(status='submitted').count()
        under_review_count = queryset.filter(status='under_review').count()
        impact_assessed_count = queryset.filter(status='impact_assessed').count()
        client_decision_count = queryset.filter(status='client_decision').count()
        approved_count = queryset.filter(status='approved').count()
        rejected_count = queryset.filter(status='rejected').count()
        
        # Decision statistics
        proceed_count = queryset.filter(client_decision='proceed').count()
        defer_count = queryset.filter(client_decision='defer').count()
        withdraw_count = queryset.filter(client_decision='withdraw').count()
        
        # Fully signed statistics
        fully_signed_count = queryset.filter(
            client_rep_signed=True,
            provider_signed=True
        ).count()
        
        return Response({
            'total_requests': total_requests,
            'status_breakdown': {
                'draft': draft_count,
                'submitted': submitted_count,
                'under_review': under_review_count,
                'impact_assessed': impact_assessed_count,
                'client_decision': client_decision_count,
                'approved': approved_count,
                'rejected': rejected_count,
            },
            'decision_breakdown': {
                'proceed': proceed_count,
                'defer': defer_count,
                'withdraw': withdraw_count,
            },
            'fully_signed_count': fully_signed_count,
            'approval_rate': f"{(approved_count / total_requests * 100):.1f}%" if total_requests > 0 else "0.0%"
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def pending_assessment(self, request):
        """
        Get change requests pending impact assessment.
        """
        user = request.user
        user_role = getattr(user, 'role', None)
        
        if not user_role or user_role.codename not in ['staff', 'superadmin']:
            return Response(
                {'detail': 'Access denied. Only staff can view pending assessments.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        pending = queryset.filter(status__in=['submitted', 'under_review'])
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def pending_client_decision(self, request):
        """
        Get change requests pending client decision.
        """
        user = request.user
        user_role = getattr(user, 'role', None)
        
        if not user_role or user_role.codename not in ['client_contact', 'staff', 'superadmin']:
            return Response(
                {'detail': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        pending = queryset.filter(status='impact_assessed')
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
