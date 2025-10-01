"""
Pilot Handover views for the Sumano Operations Management System.

This module provides API endpoints for managing internal handover workflows,
including checklist management, team approval, and document generation.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg
from django.utils import timezone

from apps.core.models import PilotHandover, Project, DocumentInstance
from apps.core.serializers.pilot_handover import (
    PilotHandoverSerializer, PilotHandoverCreateSerializer, 
    PilotHandoverSignatureSerializer, ChecklistSectionUpdateSerializer
)
from apps.core.authentication.permissions import (
    IsAuthenticatedUser, CanViewProjects, CanManageProjects, IsStaff
)
from apps.core.services.pdf_service import PDFGenerationService
from apps.core.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class PilotHandoverViewSet(viewsets.ModelViewSet):
    """
    API endpoint for internal pilot handover workflows.
    Supports checklist management, team approval, and document generation.
    Internal use only - no client access.
    """
    
    queryset = PilotHandover.objects.all().select_related(
        'project', 'project__client', 'project__client__organization',
        'document_instance', 'created_by', 'reviewed_by'
    ).prefetch_related('project__phases')
    
    serializer_class = PilotHandoverSerializer
    permission_classes = [IsAuthenticatedUser, IsStaff]  # Internal use only
    
    filterset_fields = ['status', 'project__status', 'project__service_type', 'final_go_no_go']
    search_fields = [
        'project__project_name', 'project__client__organization__name',
        'assigned_team_members', 'document_instance__filled_data'
    ]
    ordering_fields = ['created_at', 'expected_delivery_date', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PilotHandoverCreateSerializer
        elif self.action == 'sign_handover':
            return PilotHandoverSignatureSerializer
        elif self.action.startswith('update_checklist_'):
            return ChecklistSectionUpdateSerializer
        return PilotHandoverSerializer
    
    def get_permissions(self):
        # All actions require staff permissions (internal use only)
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'generate_handover_document']:
            self.permission_classes = [IsAuthenticatedUser, CanManageProjects]
        elif self.action in ['list', 'retrieve', 'sign_handover']:
            self.permission_classes = [IsAuthenticatedUser, IsStaff]
        elif self.action.startswith('update_checklist_'):
            self.permission_classes = [IsAuthenticatedUser, IsStaff]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        """Create handover record with security logging."""
        pilot_handover = serializer.save(created_by=self.request.user)
        
        SecurityService.log_security_event(
            event_type='pilot_handover_created',
            user=self.request.user,
            details={
                'handover_id': str(pilot_handover.id),
                'project_id': str(pilot_handover.project.id),
                'project_name': pilot_handover.project.project_name,
                'status': pilot_handover.status,
                'team_members': pilot_handover.assigned_team_members
            },
            severity='low'
        )
    
    def perform_update(self, serializer):
        """Update handover with security logging."""
        pilot_handover = serializer.save()
        
        SecurityService.log_security_event(
            event_type='pilot_handover_updated',
            user=self.request.user,
            details={
                'handover_id': str(pilot_handover.id),
                'project_id': str(pilot_handover.project.id),
                'status': pilot_handover.status
            },
            severity='low'
        )
    
    def perform_destroy(self, instance):
        """Delete handover with security logging."""
        project_name = instance.project.project_name
        project_id = str(instance.project.id)
        handover_id = str(instance.id)
        
        instance.delete()
        
        SecurityService.log_security_event(
            event_type='pilot_handover_deleted',
            user=self.request.user,
            details={
                'handover_id': handover_id,
                'project_id': project_id,
                'project_name': project_name
            },
            severity='medium'
        )
    
    @action(detail=True, methods=['post'])
    def sign_handover(self, request, pk=None):
        """
        Sign the handover document.
        """
        pilot_handover = self.get_object()
        
        serializer = PilotHandoverSignatureSerializer(
            data=request.data,
            context={'request': request, 'pilot_handover': pilot_handover}
        )
        
        if serializer.is_valid():
            pilot_handover = serializer.save()
            
            SecurityService.log_security_event(
                event_type='pilot_handover_signed',
                user=request.user,
                details={
                    'handover_id': str(pilot_handover.id),
                    'project_id': str(pilot_handover.project.id),
                    'signer': request.user.username
                },
                severity='medium'
            )
            
            return Response(
                {
                    'detail': 'Handover document signed successfully.',
                    'is_ready_for_handover': pilot_handover.is_ready_for_handover
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_checklist_technical_setup(self, request, pk=None):
        """Update technical setup checklist section."""
        return self._update_checklist_section(request, pk, 'technical_setup')
    
    @action(detail=True, methods=['post'])
    def update_checklist_core_pages(self, request, pk=None):
        """Update core pages checklist section."""
        return self._update_checklist_section(request, pk, 'core_pages')
    
    @action(detail=True, methods=['post'])
    def update_checklist_content_accuracy(self, request, pk=None):
        """Update content accuracy checklist section."""
        return self._update_checklist_section(request, pk, 'content_accuracy')
    
    @action(detail=True, methods=['post'])
    def update_checklist_security_compliance(self, request, pk=None):
        """Update security and compliance checklist section."""
        return self._update_checklist_section(request, pk, 'security_compliance')
    
    @action(detail=True, methods=['post'])
    def update_checklist_training_handover_prep(self, request, pk=None):
        """Update training and handover prep checklist section."""
        return self._update_checklist_section(request, pk, 'training_handover_prep')
    
    @action(detail=True, methods=['post'])
    def update_checklist_final_test_run(self, request, pk=None):
        """Update final test run checklist section."""
        return self._update_checklist_section(request, pk, 'final_test_run')
    
    def _update_checklist_section(self, request, pk, section_name):
        """Helper method to update checklist sections."""
        pilot_handover = self.get_object()
        
        serializer = ChecklistSectionUpdateSerializer(
            data=request.data,
            context={'request': request, 'pilot_handover': pilot_handover, 'section_name': section_name}
        )
        
        if serializer.is_valid():
            pilot_handover = serializer.save()
            
            SecurityService.log_security_event(
                event_type='pilot_handover_checklist_updated',
                user=request.user,
                details={
                    'handover_id': str(pilot_handover.id),
                    'project_id': str(pilot_handover.project.id),
                    'section': section_name,
                    'completion_percentage': pilot_handover.completion_percentage
                },
                severity='low'
            )
            
            return Response(
                {
                    'detail': f'{section_name.replace("_", " ").title()} checklist updated successfully.',
                    'completion_percentage': pilot_handover.completion_percentage,
                    'section': section_name
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def generate_handover_document(self, request, pk=None):
        """
        Generate internal handover PDF.
        """
        pilot_handover = self.get_object()
        
        try:
            # Prepare data for PDF generation
            pdf_data = pilot_handover._prepare_pdf_data()
            
            # Generate PDF using unified document system
            document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
                template_name='Internal Pilot Handover',
                data=pdf_data,
                user=request.user,
                project=pilot_handover.project
            )
            
            SecurityService.log_security_event(
                event_type='pilot_handover_document_generated',
                user=request.user,
                details={
                    'handover_id': str(pilot_handover.id),
                    'project_id': str(pilot_handover.project.id),
                    'document_id': str(document_instance.id)
                },
                severity='low'
            )
            
            # Return PDF as response
            response = Response(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Internal_Handover_{pilot_handover.project.project_name}.pdf"'
            return response
            
        except ValueError as e:
            logger.error(f"Error generating handover document for {pilot_handover.id}: {e}")
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.exception(f"Unexpected error generating handover document for {pilot_handover.id}: {e}")
            return Response(
                {'detail': 'An unexpected error occurred during document generation.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'])
    def submit_for_review(self, request, pk=None):
        """
        Submit handover for review.
        """
        pilot_handover = self.get_object()
        
        if pilot_handover.status not in ['draft', 'in_progress']:
            return Response(
                {'detail': 'Only draft or in-progress handovers can be submitted for review.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if checklist is complete enough
        if pilot_handover.completion_percentage < 80:
            return Response(
                {'detail': f'Checklist must be at least 80% complete before review. Current: {pilot_handover.completion_percentage}%'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status to ready for review
        pilot_handover.status = 'ready_for_review'
        pilot_handover.reviewed_by = request.user
        pilot_handover.save(update_fields=['status', 'reviewed_by'])
        
        SecurityService.log_security_event(
            event_type='pilot_handover_submitted_for_review',
            user=request.user,
            details={
                'handover_id': str(pilot_handover.id),
                'project_id': str(pilot_handover.project.id),
                'completion_percentage': pilot_handover.completion_percentage
            },
            severity='low'
        )
        
        return Response(
            {'detail': 'Handover submitted for review successfully.'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['patch'])
    def make_approval_decision(self, request, pk=None):
        """
        Make final approval decision on handover.
        """
        pilot_handover = self.get_object()
        
        if pilot_handover.status != 'ready_for_review':
            return Response(
                {'detail': 'Handover must be in review status before approval decision.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        decision = request.data.get('final_go_no_go')
        if decision not in [choice[0] for choice in PilotHandover.GO_NO_GO_CHOICES]:
            return Response(
                {'detail': f'Invalid decision. Must be one of: {[choice[0] for choice in PilotHandover.GO_NO_GO_CHOICES]}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update final decision
        pilot_handover.final_go_no_go = decision
        pilot_handover.status = 'approved' if decision == 'approved' else 'hold'
        pilot_handover.save(update_fields=['final_go_no_go', 'status'])
        
        SecurityService.log_security_event(
            event_type='pilot_handover_approval_decision',
            user=request.user,
            details={
                'handover_id': str(pilot_handover.id),
                'project_id': str(pilot_handover.project.id),
                'decision': decision
            },
            severity='medium'
        )
        
        return Response(
            {'detail': f'Approval decision recorded: {pilot_handover.get_final_go_no_go_display()}'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get handover statistics.
        """
        queryset = self.get_queryset()
        
        # Basic statistics
        total_handovers = queryset.count()
        draft_count = queryset.filter(status='draft').count()
        in_progress_count = queryset.filter(status='in_progress').count()
        ready_for_review_count = queryset.filter(status='ready_for_review').count()
        approved_count = queryset.filter(status='approved').count()
        hold_count = queryset.filter(status='hold').count()
        completed_count = queryset.filter(status='completed').count()
        
        # Approval statistics
        approved_decisions = queryset.filter(final_go_no_go='approved').count()
        hold_decisions = queryset.filter(final_go_no_go='hold').count()
        
        # Completion statistics - calculate manually since completion_percentage is a property
        avg_completion = 0
        if total_handovers > 0:
            total_completion = sum(h.completion_percentage for h in queryset)
            avg_completion = total_completion / total_handovers
        
        return Response({
            'total_handovers': total_handovers,
            'status_breakdown': {
                'draft': draft_count,
                'in_progress': in_progress_count,
                'ready_for_review': ready_for_review_count,
                'approved': approved_count,
                'hold': hold_count,
                'completed': completed_count,
            },
            'approval_breakdown': {
                'approved': approved_decisions,
                'hold': hold_decisions,
            },
            'average_completion_percentage': f"{avg_completion:.1f}%",
            'approval_rate': f"{(approved_decisions / total_handovers * 100):.1f}%" if total_handovers > 0 else "0.0%"
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        """
        Get handovers pending review.
        """
        queryset = self.get_queryset()
        pending = queryset.filter(status='ready_for_review')
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def my_handovers(self, request):
        """
        Get handovers assigned to the current user.
        """
        user = request.user
        queryset = self.get_queryset()
        
        # Filter by assigned team members or created by user
        my_handovers = queryset.filter(
            Q(assigned_team_members__contains=[user.username]) |
            Q(created_by=user) |
            Q(reviewed_by=user)
        ).distinct()
        
        serializer = self.get_serializer(my_handovers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def overdue_handovers(self, request):
        """
        Get handovers that are overdue based on expected delivery date.
        """
        queryset = self.get_queryset()
        overdue = queryset.filter(
            expected_delivery_date__lt=timezone.now().date(),
            status__in=['draft', 'in_progress', 'ready_for_review']
        )
        
        serializer = self.get_serializer(overdue, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
