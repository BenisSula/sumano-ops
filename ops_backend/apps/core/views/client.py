"""
Client views for the Sumano Operations Management System.

This module provides API endpoints for client management including
intake functionality for school pilot projects.
"""

import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Client, Organization, Contact
from apps.core.serializers.client import (
    ClientSerializer, ClientCreateSerializer, ClientIntakeUpdateSerializer, OrganizationSerializer
)
from apps.core.authentication.permissions import (
    IsAuthenticatedUser, CanViewClients, CanManageClients, IsStaff
)
from apps.core.services.pdf_service import PDFGenerationService
from apps.core.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Client model with intake functionality.
    
    Provides CRUD operations for clients and specialized endpoints
    for intake form management and PDF generation.
    """
    
    queryset = Client.objects.select_related('organization', 'billing_contact').all()
    permission_classes = [IsAuthenticatedUser, CanViewClients]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return ClientCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ClientIntakeUpdateSerializer
        return ClientSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticatedUser, CanManageClients]
        elif self.action in ['generate_intake_pdf', 'complete_intake']:
            permission_classes = [IsAuthenticatedUser, IsStaff]
        else:
            permission_classes = [IsAuthenticatedUser, CanViewClients]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user permissions and query parameters."""
        queryset = super().get_queryset()
        
        # Filter by intake completion status
        intake_complete = self.request.query_params.get('intake_complete')
        if intake_complete is not None:
            if intake_complete.lower() == 'true':
                # Filter for clients with complete intake forms
                queryset = queryset.exclude(
                    Q(school_name='') | Q(contact_person='') | Q(email='') |
                    Q(project_type__isnull=True) | Q(project_type=[]) |
                    Q(project_purpose__isnull=True) | Q(project_purpose=[]) |
                    Q(pilot_scope_features__isnull=True) | Q(pilot_scope_features=[])
                )
            elif intake_complete.lower() == 'false':
                # Filter for clients with incomplete intake forms
                queryset = queryset.filter(
                    Q(school_name='') | Q(contact_person='') | Q(email='') |
                    Q(project_type__isnull=True) | Q(project_type=[]) |
                    Q(project_purpose__isnull=True) | Q(project_purpose=[]) |
                    Q(pilot_scope_features__isnull=True) | Q(pilot_scope_features=[])
                )
        
        # Filter by relationship status
        relationship_status = self.request.query_params.get('relationship_status')
        if relationship_status:
            queryset = queryset.filter(relationship_status=relationship_status)
        
        # Filter by school name (search)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(school_name__icontains=search) |
                Q(contact_person__icontains=search) |
                Q(email__icontains=search) |
                Q(organization__name__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Create a new client with intake data."""
        try:
            # Extract organization data from request
            organization_data = request.data.get('organization', {})
            if not organization_data.get('name'):
                return Response(
                    {'error': 'Organization name is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create organization
            organization_serializer = OrganizationSerializer(data=organization_data)
            if organization_serializer.is_valid():
                organization = organization_serializer.save()
            else:
                return Response(
                    {'error': 'Invalid organization data.', 'details': organization_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create client with organization relationship
            client_data = request.data.copy()
            client_data['organization'] = organization.id
            client_data['client_since'] = client_data.get('client_since', timezone.now().date())
            client_data['relationship_status'] = client_data.get('relationship_status', 'prospect')
            
            serializer = self.get_serializer(data=client_data)
            if serializer.is_valid():
                client = serializer.save(organization=organization)
                
                # Log security event
                SecurityService.log_security_event(
                    event_type='client_created',
                    user=request.user,
                    ip_address=SecurityService.get_client_ip(request),
                    details={
                        'client_id': str(client.id),
                        'school_name': client.school_name,
                        'organization_id': str(organization.id)
                    },
                    severity='low'
                )
                
                return Response(
                    ClientSerializer(client).data,
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {'error': 'Invalid client data.', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Error creating client: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to create client.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='complete-intake')
    def complete_intake(self, request, pk=None):
        """Mark client intake as complete and generate PDF."""
        client = self.get_object()
        
        try:
            # Validate intake completion
            serializer = ClientIntakeUpdateSerializer(data=request.data)
            if serializer.is_valid():
                # Update client with intake data
                for field, value in serializer.validated_data.items():
                    setattr(client, field, value)
                
                client.save()
                
                # Generate intake PDF
                pdf_data = {
                    'school_name': client.school_name,
                    'contact_person': client.contact_person,
                    'role_position': client.role_position,
                    'email': client.email,
                    'phone_whatsapp': client.phone_whatsapp,
                    'address': client.address,
                    'number_of_students': client.number_of_students,
                    'number_of_staff': client.number_of_staff,
                    'project_type': ', '.join(client.project_type) if client.project_type else '',
                    'project_purpose': ', '.join(client.project_purpose) if client.project_purpose else '',
                    'pilot_scope_features': ', '.join(client.pilot_scope_features) if client.pilot_scope_features else '',
                    'pilot_start_date': client.pilot_start_date.strftime('%Y-%m-%d') if client.pilot_start_date else '',
                    'pilot_end_date': client.pilot_end_date.strftime('%Y-%m-%d') if client.pilot_end_date else '',
                    'timeline_preference': client.get_timeline_preference_display(),
                    'additional_notes': client.additional_notes,
                    'submission_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Generate PDF using unified document system
                document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
                    template_name='Client Intake Form',
                    data=pdf_data,
                    user=request.user,
                    project=None  # No project associated yet
                )
                
                # Log security event
                SecurityService.log_security_event(
                    event_type='intake_completed',
                    user=request.user,
                    ip_address=SecurityService.get_client_ip(request),
                    details={
                        'client_id': str(client.id),
                        'school_name': client.school_name,
                        'document_id': str(document_instance.id)
                    },
                    severity='medium'
                )
                
                return Response({
                    'message': 'Intake completed successfully.',
                    'client': ClientSerializer(client).data,
                    'document': {
                        'id': str(document_instance.id),
                        'title': document_instance.document_title,
                        'pdf_url': document_instance.get_pdf_url(),
                        'generated_at': document_instance.created_at
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Invalid intake data.', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Error completing intake for client {client.id}: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to complete intake.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='generate-intake-pdf')
    def generate_intake_pdf(self, request, pk=None):
        """Generate PDF for client intake form."""
        client = self.get_object()
        
        try:
            # Prepare data for PDF generation
            pdf_data = {
                'school_name': client.school_name or 'Not provided',
                'contact_person': client.contact_person or 'Not provided',
                'role_position': client.role_position or 'Not provided',
                'email': client.email or 'Not provided',
                'phone_whatsapp': client.phone_whatsapp or 'Not provided',
                'address': client.address or 'Not provided',
                'current_website': client.current_website or 'Not provided',
                'number_of_students': client.number_of_students or 'Not provided',
                'number_of_staff': client.number_of_staff or 'Not provided',
                'project_type': ', '.join(client.project_type) if client.project_type else 'Not provided',
                'project_purpose': ', '.join(client.project_purpose) if client.project_purpose else 'Not provided',
                'pilot_scope_features': ', '.join(client.pilot_scope_features) if client.pilot_scope_features else 'Not provided',
                'pilot_start_date': client.pilot_start_date.strftime('%Y-%m-%d') if client.pilot_start_date else 'Not provided',
                'pilot_end_date': client.pilot_end_date.strftime('%Y-%m-%d') if client.pilot_end_date else 'Not provided',
                'timeline_preference': client.get_timeline_preference_display() if client.timeline_preference else 'Not provided',
                'content_availability': 'Yes' if client.content_availability else 'No',
                'token_commitment_fee': str(client.token_commitment_fee) if client.token_commitment_fee else 'Not provided',
                'additional_notes': client.additional_notes or 'None',
                'generation_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Generate PDF using unified document system
            document_instance, pdf_bytes = PDFGenerationService.generate_from_template(
                template_name='Client Intake Form',
                data=pdf_data,
                user=request.user,
                project=None
            )
            
            # Log security event
            SecurityService.log_security_event(
                event_type='intake_pdf_generated',
                user=request.user,
                ip_address=SecurityService.get_client_ip(request),
                details={
                    'client_id': str(client.id),
                    'school_name': client.school_name,
                    'document_id': str(document_instance.id)
                },
                severity='low'
            )
            
            return Response({
                'message': 'PDF generated successfully.',
                'document': {
                    'id': str(document_instance.id),
                    'title': document_instance.document_title,
                    'pdf_url': document_instance.get_pdf_url(),
                    'generated_at': document_instance.created_at,
                    'file_size': len(pdf_bytes)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating PDF for client {client.id}: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to generate PDF.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='intake-statistics')
    def intake_statistics(self, request):
        """Get statistics about client intake forms."""
        try:
            total_clients = Client.objects.count()
            complete_intakes = Client.objects.exclude(
                Q(school_name='') | Q(contact_person='') | Q(email='') |
                Q(project_type__isnull=True) | Q(project_type=[]) |
                Q(project_purpose__isnull=True) | Q(project_purpose=[]) |
                Q(pilot_scope_features__isnull=True) | Q(pilot_scope_features=[])
            ).count()
            incomplete_intakes = total_clients - complete_intakes
            
            # Project type distribution
            project_types = {}
            for client in Client.objects.exclude(project_type__isnull=True).exclude(project_type=[]):
                for project_type in client.project_type:
                    project_types[project_type] = project_types.get(project_type, 0) + 1
            
            # Timeline preference distribution
            timeline_preferences = {}
            for client in Client.objects.exclude(timeline_preference=''):
                pref = client.timeline_preference
                timeline_preferences[pref] = timeline_preferences.get(pref, 0) + 1
            
            return Response({
                'total_clients': total_clients,
                'complete_intakes': complete_intakes,
                'incomplete_intakes': incomplete_intakes,
                'completion_rate': round((complete_intakes / total_clients * 100), 1) if total_clients > 0 else 0,
                'project_type_distribution': project_types,
                'timeline_preference_distribution': timeline_preferences,
                'generated_at': timezone.now()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating intake statistics: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to generate statistics.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
