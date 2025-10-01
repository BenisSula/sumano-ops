"""
Change Request serializers for the Sumano Operations Management System.

This module provides serializers for change request workflows,
including validation for change details, impact assessment, and client decisions.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from apps.core.models import ChangeRequest, Project, DocumentInstance, DocumentTemplate

User = get_user_model()


class ChangeRequestDataSerializer(serializers.Serializer):
    """Serializer for change request details."""
    
    description = serializers.CharField(help_text="Detailed description of the requested change")
    reason = serializers.CharField(help_text="Business reason for the change")


class ImpactAssessmentSerializer(serializers.Serializer):
    """Serializer for impact assessment data."""
    
    no_additional_cost = serializers.BooleanField(default=False, help_text="No additional cost required")
    requires_additional_effort = serializers.BooleanField(default=False, help_text="Requires additional effort")
    estimated_time = serializers.IntegerField(
        required=False, 
        allow_null=True,
        validators=[MinValueValidator(0)],
        help_text="Estimated time in days"
    )
    estimated_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Estimated additional cost"
    )


class ClientDecisionSerializer(serializers.Serializer):
    """Serializer for client decision data."""
    
    decision = serializers.ChoiceField(
        choices=ChangeRequest.DECISION_CHOICES,
        help_text="Client's decision on the change request"
    )


class SignatureSerializer(serializers.Serializer):
    """Serializer for signature data."""
    
    name = serializers.CharField(max_length=100)
    signature = serializers.CharField(help_text="Base64 encoded signature image")
    date = serializers.DateTimeField(default=serializers.CreateOnlyDefault(timezone.now))


class SignaturesSerializer(serializers.Serializer):
    """Serializer for all signatures."""
    
    client_representative = SignatureSerializer(required=False, allow_null=True)
    provider_representative = SignatureSerializer(required=False, allow_null=True)


class ChangeRequestSerializer(serializers.ModelSerializer):
    """
    Main serializer for ChangeRequest model.
    """
    
    # Nested serializers for complex data
    change_request = ChangeRequestDataSerializer(required=False)
    impact_assessment = ImpactAssessmentSerializer(required=False)
    client_decision = ClientDecisionSerializer(required=False)
    signatures = SignaturesSerializer(required=False)
    
    # Computed fields
    is_fully_signed = serializers.BooleanField(read_only=True)
    is_ready_for_client_decision = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    client_decision_display = serializers.CharField(source='get_client_decision_display', read_only=True)
    
    # Project information
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    project_id = serializers.UUIDField(source='project.id', read_only=True)
    client_name = serializers.CharField(source='project.client.organization.name', read_only=True)
    
    # Document information
    document_id = serializers.UUIDField(source='document_instance.id', read_only=True)
    document_status = serializers.CharField(source='document_instance.status', read_only=True)
    
    class Meta:
        model = ChangeRequest
        fields = [
            'id', 'project', 'project_id', 'project_name', 'client_name', 'document_instance', 'document_id', 'document_status',
            'request_date', 'reference_agreement', 'status', 'status_display', 'client_decision', 'client_decision_display',
            'change_request', 'impact_assessment', 'signatures',
            'client_rep_signed', 'client_rep_signed_at', 'provider_signed', 'provider_signed_at',
            'is_fully_signed', 'is_ready_for_client_decision', 'created_by', 'assessed_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'document_instance', 'client_rep_signed', 'client_rep_signed_at',
            'provider_signed', 'provider_signed_at', 'created_by', 'assessed_by', 'created_at', 'updated_at'
        ]
    
    def validate_project(self, value):
        """Validate that project exists and is appropriate for change requests."""
        if not value:
            raise serializers.ValidationError("Project is required.")
        
        # Check project status - should be active project
        if value.status not in ['planning', 'development', 'testing', 'client_review']:
            raise serializers.ValidationError(
                f"Change requests can only be made for active projects. Current status: {value.status}"
            )
        
        return value
    
    def validate_request_date(self, value):
        """Validate request date."""
        if value > timezone.now().date():
            raise serializers.ValidationError("Request date cannot be in the future.")
        
        # Check if request date is after project start date
        project = self.initial_data.get('project')
        if project and hasattr(project, 'start_date') and project.start_date:
            if value < project.start_date:
                raise serializers.ValidationError("Request date cannot be before project start date.")
        
        return value
    
    def validate_impact_assessment(self, value):
        """Validate impact assessment data."""
        if value:
            # If requires additional effort is True, estimated_time should be provided
            if value.get('requires_additional_effort') and not value.get('estimated_time'):
                raise serializers.ValidationError("Estimated time is required when additional effort is needed.")
            
            # If no_additional_cost is False, estimated_cost should be provided
            if not value.get('no_additional_cost') and not value.get('estimated_cost'):
                raise serializers.ValidationError("Estimated cost is required when additional cost is expected.")
        
        return value
    
    def create(self, validated_data):
        """Create a new ChangeRequest record with DocumentInstance."""
        # Extract nested data
        change_request_data = validated_data.pop('change_request', {})
        impact_assessment_data = validated_data.pop('impact_assessment', {})
        client_decision_data = validated_data.pop('client_decision', {})
        signatures_data = validated_data.pop('signatures', {})
        
        # Get the project
        project = validated_data['project']
        
        # Prepare filled_data for DocumentInstance
        filled_data = {
            'change_request': change_request_data,
            'impact_assessment': impact_assessment_data,
            'client_decision': client_decision_data,
            'signatures': signatures_data,
            'project_reference': {
                'project_title': project.project_name,
                'client_name': project.client.organization.name,
                'request_date': validated_data['request_date'].isoformat(),
                'reference_agreement': validated_data.get('reference_agreement', ''),
            }
        }
        
        # Create DocumentInstance
        document_instance = DocumentInstance.objects.create(
            template=DocumentTemplate.objects.get(template_type='CHANGE'),
            project=project,
            filled_data=filled_data,
            created_by=validated_data['created_by'],
            status='DRAFT'
        )
        
        # Create ChangeRequest record
        validated_data['document_instance'] = document_instance
        change_request = ChangeRequest.objects.create(**validated_data)
        
        return change_request
    
    def update(self, instance, validated_data):
        """Update ChangeRequest record and associated DocumentInstance."""
        # Extract nested data
        change_request_data = validated_data.pop('change_request', {})
        impact_assessment_data = validated_data.pop('impact_assessment', {})
        client_decision_data = validated_data.pop('client_decision', {})
        signatures_data = validated_data.pop('signatures', {})
        
        # Update DocumentInstance filled_data
        filled_data = instance.document_instance.filled_data.copy()
        
        if change_request_data:
            if 'change_request' not in filled_data:
                filled_data['change_request'] = {}
            filled_data['change_request'].update(change_request_data)
        
        if impact_assessment_data:
            if 'impact_assessment' not in filled_data:
                filled_data['impact_assessment'] = {}
            filled_data['impact_assessment'].update(impact_assessment_data)
        
        if client_decision_data:
            if 'client_decision' not in filled_data:
                filled_data['client_decision'] = {}
            filled_data['client_decision'].update(client_decision_data)
        
        if signatures_data:
            if 'signatures' not in filled_data:
                filled_data['signatures'] = {}
            filled_data['signatures'].update(signatures_data)
        
        # Save DocumentInstance
        instance.document_instance.filled_data = filled_data
        instance.document_instance.save(update_fields=['filled_data', 'updated_at'])
        
        # Update ChangeRequest
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        
        return instance


class ChangeRequestCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new ChangeRequest record.
    """
    
    project_id = serializers.UUIDField()
    request_date = serializers.DateField()
    reference_agreement = serializers.CharField(required=False, allow_blank=True)
    change_request = ChangeRequestDataSerializer()
    
    def validate_project_id(self, value):
        """Validate project exists and is available for change requests."""
        try:
            project = Project.objects.get(id=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project not found.")
        
        # Check project status
        if project.status not in ['planning', 'development', 'testing', 'client_review']:
            raise serializers.ValidationError(
                f"Change requests can only be made for active projects. Current status: {project.status}"
            )
        
        return project
    
    def create(self, validated_data):
        """Create ChangeRequest with proper relationships."""
        project = validated_data.pop('project_id')
        change_request_data = validated_data.pop('change_request')
        
        # Prepare filled_data
        filled_data = {
            'change_request': change_request_data,
            'impact_assessment': {},
            'client_decision': {},
            'signatures': {},
            'project_reference': {
                'project_title': project.project_name,
                'client_name': project.client.organization.name,
                'request_date': validated_data['request_date'].isoformat(),
                'reference_agreement': validated_data.get('reference_agreement', ''),
            }
        }
        
        # Create DocumentInstance
        document_instance = DocumentInstance.objects.create(
            template=DocumentTemplate.objects.get(template_type='CHANGE'),
            project=project,
            filled_data=filled_data,
            created_by=self.context['request'].user,
            status='DRAFT'
        )
        
        # Create ChangeRequest
        change_request = ChangeRequest.objects.create(
            project=project,
            document_instance=document_instance,
            request_date=validated_data['request_date'],
            reference_agreement=validated_data.get('reference_agreement', ''),
            status='submitted',
            created_by=self.context['request'].user
        )
        
        return change_request


class ChangeRequestSignatureSerializer(serializers.Serializer):
    """
    Serializer for signing change request documents.
    """
    
    signature_data = SignatureSerializer()
    
    def validate(self, data):
        """Validate signature data."""
        user = self.context['request'].user
        change_request = self.context['change_request']
        
        # Check if user can sign this change request
        if not change_request.can_be_signed_by(user):
            user_role = getattr(user, 'role', None)
            role_name = user_role.codename if user_role else 'unknown'
            raise serializers.ValidationError(
                f"User with role '{role_name}' cannot sign this change request document."
            )
        
        return data
    
    def save(self, **kwargs):
        """Sign the change request document."""
        change_request = self.context['change_request']
        user = self.context['request'].user
        signature_data = self.validated_data['signature_data']
        
        # Sign the change request
        change_request.sign_change_request(user, signature_data)
        
        return change_request


class ImpactAssessmentUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating impact assessment.
    """
    
    impact_assessment = ImpactAssessmentSerializer()
    
    def save(self, **kwargs):
        """Update impact assessment."""
        change_request = self.context['change_request']
        user = self.context['request'].user
        
        # Check if user can assess this change request
        if not change_request.can_be_assessed_by(user):
            user_role = getattr(user, 'role', None)
            role_name = user_role.codename if user_role else 'unknown'
            raise serializers.ValidationError(
                f"User with role '{role_name}' cannot assess this change request."
            )
        
        # Update impact assessment
        change_request.update_impact_assessment(self.validated_data['impact_assessment'])
        change_request.assessed_by = user
        change_request.save(update_fields=['assessed_by'])
        
        return change_request
