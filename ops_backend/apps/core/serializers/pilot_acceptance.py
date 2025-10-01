"""
Pilot Acceptance serializers for the Sumano Operations Management System.

This module provides serializers for pilot acceptance workflows,
including validation for acceptance checklists and signature data.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import PilotAcceptance, Project, DocumentInstance, DocumentTemplate

User = get_user_model()


class ChecklistSerializer(serializers.Serializer):
    """Serializer for acceptance checklist items."""
    
    digital_gateway_live = serializers.BooleanField(default=False)
    mobile_friendly = serializers.BooleanField(default=False)
    pages_present = serializers.BooleanField(default=False)
    portals_linked = serializers.BooleanField(default=False)
    social_media_embedded = serializers.BooleanField(default=False)
    logo_colors_correct = serializers.BooleanField(default=False)
    photos_content_displayed = serializers.BooleanField(default=False)
    layout_design_ok = serializers.BooleanField(default=False)
    staff_training_completed = serializers.BooleanField(default=False)
    training_materials_provided = serializers.BooleanField(default=False)
    no_critical_errors = serializers.BooleanField(default=False)
    minor_issues_resolved = serializers.BooleanField(default=False)


class SignatureSerializer(serializers.Serializer):
    """Serializer for signature data."""
    
    name = serializers.CharField(max_length=100)
    title = serializers.CharField(max_length=100)
    signature = serializers.CharField(help_text="Base64 encoded signature image")
    date = serializers.DateTimeField(default=serializers.CreateOnlyDefault(timezone.now))


class SignaturesSerializer(serializers.Serializer):
    """Serializer for all signatures."""
    
    school_representative = SignatureSerializer(required=False, allow_null=True)
    company_representative = SignatureSerializer(required=False, allow_null=True)


class ProjectReferenceSerializer(serializers.Serializer):
    """Serializer for project reference data."""
    
    school_name = serializers.CharField(read_only=True)
    pilot_start_date = serializers.DateField(read_only=True)
    completion_date = serializers.DateField()
    token_payment = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)


class PilotAcceptanceSerializer(serializers.ModelSerializer):
    """
    Main serializer for PilotAcceptance model.
    """
    
    # Nested serializers for complex data
    checklist = ChecklistSerializer(required=False)
    signatures = SignaturesSerializer(required=False)
    project_reference = ProjectReferenceSerializer(required=False)
    
    # Computed fields
    is_fully_signed = serializers.BooleanField(read_only=True)
    completion_percentage = serializers.FloatField(read_only=True)
    acceptance_status_display = serializers.CharField(source='get_acceptance_status_display', read_only=True)
    
    # Project information
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    project_id = serializers.UUIDField(source='project.id', read_only=True)
    
    # Document information
    document_id = serializers.UUIDField(source='document_instance.id', read_only=True)
    document_status = serializers.CharField(source='document_instance.status', read_only=True)
    
    class Meta:
        model = PilotAcceptance
        fields = [
            'id', 'project', 'project_id', 'project_name', 'document_instance', 'document_id', 'document_status',
            'acceptance_status', 'acceptance_status_display', 'completion_date', 'token_payment',
            'issues_to_resolve', 'checklist', 'signatures', 'project_reference',
            'school_representative_signed', 'school_representative_signed_at',
            'company_representative_signed', 'company_representative_signed_at',
            'is_fully_signed', 'completion_percentage', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'document_instance', 'school_representative_signed', 'school_representative_signed_at',
            'company_representative_signed', 'company_representative_signed_at', 'created_by', 'created_at', 'updated_at'
        ]
    
    def validate_project(self, value):
        """Validate that project exists and is in appropriate status."""
        if not value:
            raise serializers.ValidationError("Project is required.")
        
        # Check if project already has an acceptance record
        if hasattr(value, 'pilot_acceptance') and value.pilot_acceptance:
            raise serializers.ValidationError("This project already has an acceptance record.")
        
        # Check project status - should be completed or near completion
        if value.status not in ['testing', 'client_review', 'completed']:
            raise serializers.ValidationError(
                f"Project must be in 'testing', 'client_review', or 'completed' status to create acceptance. Current status: {value.status}"
            )
        
        return value
    
    def validate_acceptance_status(self, value):
        """Validate acceptance status."""
        valid_choices = [choice[0] for choice in PilotAcceptance.ACCEPTANCE_STATUS_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid acceptance status. Must be one of: {valid_choices}")
        return value
    
    def validate_completion_date(self, value):
        """Validate completion date."""
        if value > timezone.now().date():
            raise serializers.ValidationError("Completion date cannot be in the future.")
        
        # Check if completion date is after project start date
        project = self.initial_data.get('project')
        if project and hasattr(project, 'start_date') and project.start_date:
            if value < project.start_date:
                raise serializers.ValidationError("Completion date cannot be before project start date.")
        
        return value
    
    def validate_token_payment(self, value):
        """Validate token payment amount."""
        if value is not None and value < 0:
            raise serializers.ValidationError("Token payment cannot be negative.")
        return value
    
    def create(self, validated_data):
        """Create a new PilotAcceptance record with DocumentInstance."""
        # Extract nested data
        checklist_data = validated_data.pop('checklist', {})
        signatures_data = validated_data.pop('signatures', {})
        project_reference_data = validated_data.pop('project_reference', {})
        
        # Get the project
        project = validated_data['project']
        
        # Prepare filled_data for DocumentInstance
        filled_data = {
            'checklist': checklist_data,
            'signatures': signatures_data,
            'project_reference': project_reference_data,
            'acceptance_status': validated_data['acceptance_status'],
            'issues_to_resolve': validated_data.get('issues_to_resolve', ''),
            'completion_date': validated_data['completion_date'].isoformat(),
            'token_payment': str(validated_data.get('token_payment', 0)) if validated_data.get('token_payment') else '0',
        }
        
        # Create DocumentInstance
        document_instance = DocumentInstance.objects.create(
            template=DocumentTemplate.objects.get(template_type='ACCEPTANCE'),
            project=project,
            filled_data=filled_data,
            created_by=validated_data['created_by'],
            status='DRAFT'
        )
        
        # Create PilotAcceptance record
        validated_data['document_instance'] = document_instance
        pilot_acceptance = PilotAcceptance.objects.create(**validated_data)
        
        return pilot_acceptance
    
    def update(self, instance, validated_data):
        """Update PilotAcceptance record and associated DocumentInstance."""
        # Extract nested data
        checklist_data = validated_data.pop('checklist', {})
        signatures_data = validated_data.pop('signatures', {})
        project_reference_data = validated_data.pop('project_reference', {})
        
        # Update DocumentInstance filled_data
        filled_data = instance.document_instance.filled_data.copy()
        
        if checklist_data:
            filled_data['checklist'].update(checklist_data)
        
        if signatures_data:
            if 'signatures' not in filled_data:
                filled_data['signatures'] = {}
            filled_data['signatures'].update(signatures_data)
        
        if project_reference_data:
            if 'project_reference' not in filled_data:
                filled_data['project_reference'] = {}
            filled_data['project_reference'].update(project_reference_data)
        
        # Update other fields
        for field, value in validated_data.items():
            if field in ['acceptance_status', 'issues_to_resolve', 'completion_date', 'token_payment']:
                filled_data[field] = value
        
        # Save DocumentInstance
        instance.document_instance.filled_data = filled_data
        instance.document_instance.save(update_fields=['filled_data', 'updated_at'])
        
        # Update PilotAcceptance
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        
        return instance


class PilotAcceptanceCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new PilotAcceptance record.
    """
    
    project_id = serializers.UUIDField()
    acceptance_status = serializers.ChoiceField(choices=PilotAcceptance.ACCEPTANCE_STATUS_CHOICES)
    completion_date = serializers.DateField()
    token_payment = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    issues_to_resolve = serializers.CharField(required=False, allow_blank=True)
    checklist = ChecklistSerializer(required=False)
    signatures = SignaturesSerializer(required=False)
    
    def validate_project_id(self, value):
        """Validate project exists and is available for acceptance."""
        try:
            project = Project.objects.get(id=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project not found.")
        
        # Check if project already has acceptance
        if hasattr(project, 'pilot_acceptance') and project.pilot_acceptance:
            raise serializers.ValidationError("This project already has an acceptance record.")
        
        # Check project status
        if project.status not in ['testing', 'client_review', 'completed']:
            raise serializers.ValidationError(
                f"Project must be in 'testing', 'client_review', or 'completed' status. Current status: {project.status}"
            )
        
        return project
    
    def create(self, validated_data):
        """Create PilotAcceptance with proper relationships."""
        project = validated_data.pop('project_id')
        
        # Prepare filled_data
        filled_data = {
            'checklist': validated_data.get('checklist', {}),
            'signatures': validated_data.get('signatures', {}),
            'project_reference': {
                'school_name': project.client.organization.name,
                'pilot_start_date': project.start_date.isoformat() if project.start_date else '',
                'completion_date': validated_data['completion_date'].isoformat(),
                'token_payment': str(validated_data.get('token_payment', 0)) if validated_data.get('token_payment') else '0',
            },
            'acceptance_status': validated_data['acceptance_status'],
            'issues_to_resolve': validated_data.get('issues_to_resolve', ''),
        }
        
        # Create DocumentInstance
        document_instance = DocumentInstance.objects.create(
            template=DocumentTemplate.objects.get(template_type='ACCEPTANCE'),
            project=project,
            filled_data=filled_data,
            created_by=self.context['request'].user,
            status='DRAFT'
        )
        
        # Create PilotAcceptance
        pilot_acceptance = PilotAcceptance.objects.create(
            project=project,
            document_instance=document_instance,
            acceptance_status=validated_data['acceptance_status'],
            completion_date=validated_data['completion_date'],
            token_payment=validated_data.get('token_payment'),
            issues_to_resolve=validated_data.get('issues_to_resolve', ''),
            created_by=self.context['request'].user
        )
        
        return pilot_acceptance


class PilotAcceptanceSignatureSerializer(serializers.Serializer):
    """
    Serializer for signing acceptance documents.
    """
    
    signature_data = SignatureSerializer()
    
    def validate(self, data):
        """Validate signature data."""
        user = self.context['request'].user
        pilot_acceptance = self.context['pilot_acceptance']
        
        # Check if user can sign this acceptance
        if not pilot_acceptance.can_be_signed_by(user):
            user_role = getattr(user, 'role', None)
            role_name = user_role.codename if user_role else 'unknown'
            raise serializers.ValidationError(
                f"User with role '{role_name}' cannot sign this acceptance document."
            )
        
        return data
    
    def save(self, **kwargs):
        """Sign the acceptance document."""
        pilot_acceptance = self.context['pilot_acceptance']
        user = self.context['request'].user
        signature_data = self.validated_data['signature_data']
        
        # Sign the acceptance
        pilot_acceptance.sign_acceptance(user, signature_data)
        
        return pilot_acceptance
