"""
Pilot Handover serializers for the Sumano Operations Management System.

This module provides serializers for internal handover workflows,
including validation for checklist sections, team assignments, and approval processes.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import PilotHandover, Project, DocumentInstance, DocumentTemplate

User = get_user_model()


class ProjectReferenceSerializer(serializers.Serializer):
    """Serializer for project reference data."""
    
    client_school_name = serializers.CharField(help_text="Client school name")
    pilot_start_date = serializers.DateField(help_text="Pilot start date")
    expected_delivery_date = serializers.DateField(help_text="Expected delivery date")
    assigned_team_members = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of assigned team members"
    )


class ChecklistSectionSerializer(serializers.Serializer):
    """Serializer for individual checklist sections."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically add fields based on the section
        section_name = kwargs.get('context', {}).get('section_name', '')
        if section_name:
            section_items = PilotHandover.get_checklist_sections().get(section_name, [])
            for item in section_items:
                self.fields[item] = serializers.BooleanField(default=False)


class TechnicalSetupSerializer(ChecklistSectionSerializer):
    """Serializer for technical setup checklist section."""
    
    domain_configured = serializers.BooleanField(default=False)
    ssl_active = serializers.BooleanField(default=False)
    site_load_ok = serializers.BooleanField(default=False)
    responsive_design = serializers.BooleanField(default=False)
    no_broken_links = serializers.BooleanField(default=False)


class CorePagesSerializer(ChecklistSectionSerializer):
    """Serializer for core pages checklist section."""
    
    home_completed = serializers.BooleanField(default=False)
    about_news_added = serializers.BooleanField(default=False)
    contact_correct = serializers.BooleanField(default=False)
    portal_links_ok = serializers.BooleanField(default=False)
    social_media_tested = serializers.BooleanField(default=False)


class ContentAccuracySerializer(ChecklistSectionSerializer):
    """Serializer for content accuracy checklist section."""
    
    logo_correct = serializers.BooleanField(default=False)
    photos_optimized = serializers.BooleanField(default=False)
    text_proofread = serializers.BooleanField(default=False)
    info_matches_official = serializers.BooleanField(default=False)


class SecurityComplianceSerializer(ChecklistSectionSerializer):
    """Serializer for security and compliance checklist section."""
    
    admin_created = serializers.BooleanField(default=False)
    restricted_access = serializers.BooleanField(default=False)
    privacy_statement_included = serializers.BooleanField(default=False)


class TrainingHandoverPrepSerializer(ChecklistSectionSerializer):
    """Serializer for training and handover prep checklist section."""
    
    training_scheduled = serializers.BooleanField(default=False)
    training_materials_ready = serializers.BooleanField(default=False)
    howto_instructions = serializers.BooleanField(default=False)
    support_contact_added = serializers.BooleanField(default=False)


class FinalTestRunSerializer(ChecklistSectionSerializer):
    """Serializer for final test run checklist section."""
    
    browsers_tested = serializers.BooleanField(default=False)
    forms_tested = serializers.BooleanField(default=False)
    backup_taken = serializers.BooleanField(default=False)
    screenshots_captured = serializers.BooleanField(default=False)


class ChecklistSerializer(serializers.Serializer):
    """Serializer for complete checklist data."""
    
    technical_setup = TechnicalSetupSerializer(required=False)
    core_pages = CorePagesSerializer(required=False)
    content_accuracy = ContentAccuracySerializer(required=False)
    security_compliance = SecurityComplianceSerializer(required=False)
    training_handover_prep = TrainingHandoverPrepSerializer(required=False)
    final_test_run = FinalTestRunSerializer(required=False)


class HandoverApprovalSerializer(serializers.Serializer):
    """Serializer for handover approval data."""
    
    final_go_no_go = serializers.ChoiceField(
        choices=PilotHandover.GO_NO_GO_CHOICES,
        help_text="Final go/no-go decision"
    )


class SignatureSerializer(serializers.Serializer):
    """Serializer for signature data."""
    
    name = serializers.CharField(max_length=100)
    signature = serializers.CharField(help_text="Base64 encoded signature image")
    date = serializers.DateTimeField(default=serializers.CreateOnlyDefault(timezone.now))


class SignaturesSerializer(serializers.Serializer):
    """Serializer for all signatures."""
    
    team_lead = SignatureSerializer(required=False, allow_null=True)


class PilotHandoverSerializer(serializers.ModelSerializer):
    """
    Main serializer for PilotHandover model.
    """
    
    # Nested serializers for complex data
    project_reference = ProjectReferenceSerializer(required=False)
    checklist = ChecklistSerializer(required=False)
    handover_approval = HandoverApprovalSerializer(required=False)
    signatures = SignaturesSerializer(required=False)
    
    # Computed fields
    is_ready_for_handover = serializers.BooleanField(read_only=True)
    completion_percentage = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    final_go_no_go_display = serializers.CharField(source='get_final_go_no_go_display', read_only=True)
    
    # Project information
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    project_id = serializers.UUIDField(source='project.id', read_only=True)
    client_school_name = serializers.CharField(source='project.client.organization.name', read_only=True)
    
    # Document information
    document_id = serializers.UUIDField(source='document_instance.id', read_only=True)
    document_status = serializers.CharField(source='document_instance.status', read_only=True)
    
    class Meta:
        model = PilotHandover
        fields = [
            'id', 'project', 'project_id', 'project_name', 'client_school_name', 
            'document_instance', 'document_id', 'document_status',
            'expected_delivery_date', 'assigned_team_members', 'status', 'status_display',
            'final_go_no_go', 'final_go_no_go_display', 'project_reference', 'checklist',
            'handover_approval', 'signatures', 'team_lead_signed', 'team_lead_signed_at',
            'is_ready_for_handover', 'completion_percentage', 'created_by', 'reviewed_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'document_instance', 'team_lead_signed', 'team_lead_signed_at',
            'created_by', 'reviewed_by', 'created_at', 'updated_at'
        ]
    
    def validate_project(self, value):
        """Validate that project exists and is appropriate for handover."""
        if not value:
            raise serializers.ValidationError("Project is required.")
        
        # Check project status - should be completed or near completion
        if value.status not in ['testing', 'client_review', 'completed']:
            raise serializers.ValidationError(
                f"Handovers can only be created for projects in testing or completed status. Current status: {value.status}"
            )
        
        return value
    
    def validate_expected_delivery_date(self, value):
        """Validate expected delivery date."""
        if value < timezone.now().date():
            raise serializers.ValidationError("Expected delivery date cannot be in the past.")
        
        return value
    
    def validate_assigned_team_members(self, value):
        """Validate assigned team members."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Assigned team members must be a list.")
        
        if len(value) == 0:
            raise serializers.ValidationError("At least one team member must be assigned.")
        
        return value
    
    def create(self, validated_data):
        """Create a new PilotHandover record with DocumentInstance."""
        # Extract nested data
        project_reference_data = validated_data.pop('project_reference', {})
        checklist_data = validated_data.pop('checklist', {})
        handover_approval_data = validated_data.pop('handover_approval', {})
        signatures_data = validated_data.pop('signatures', {})
        
        # Get the project
        project = validated_data['project']
        
        # Prepare filled_data for DocumentInstance
        filled_data = {
            'project_reference': {
                'client_school_name': project.client.organization.name,
                'pilot_start_date': project.start_date.isoformat() if project.start_date else None,
                'expected_delivery_date': validated_data['expected_delivery_date'].isoformat(),
                'assigned_team_members': validated_data['assigned_team_members'],
            },
            'checklist': checklist_data,
            'handover_approval': handover_approval_data,
            'signatures': signatures_data,
        }
        
        # Create DocumentInstance - use first HANDOVER template
        handover_template = DocumentTemplate.objects.filter(template_type='HANDOVER').first()
        if not handover_template:
            # Create a default template if none exists
            handover_template = DocumentTemplate.objects.create(
                name='Internal Pilot Handover',
                template_type='HANDOVER',
                content='<html><body><h1>Internal Handover Document</h1></body></html>',
                status='PUBLISHED'
            )
        
        document_instance = DocumentInstance.objects.create(
            template=handover_template,
            project=project,
            filled_data=filled_data,
            created_by=validated_data['created_by'],
            status='DRAFT'
        )
        
        # Create PilotHandover record
        validated_data['document_instance'] = document_instance
        pilot_handover = PilotHandover.objects.create(**validated_data)
        
        return pilot_handover
    
    def update(self, instance, validated_data):
        """Update PilotHandover record and associated DocumentInstance."""
        # Extract nested data
        project_reference_data = validated_data.pop('project_reference', {})
        checklist_data = validated_data.pop('checklist', {})
        handover_approval_data = validated_data.pop('handover_approval', {})
        signatures_data = validated_data.pop('signatures', {})
        
        # Update DocumentInstance filled_data
        filled_data = instance.document_instance.filled_data.copy()
        
        if project_reference_data:
            if 'project_reference' not in filled_data:
                filled_data['project_reference'] = {}
            filled_data['project_reference'].update(project_reference_data)
        
        if checklist_data:
            if 'checklist' not in filled_data:
                filled_data['checklist'] = {}
            filled_data['checklist'].update(checklist_data)
        
        if handover_approval_data:
            if 'handover_approval' not in filled_data:
                filled_data['handover_approval'] = {}
            filled_data['handover_approval'].update(handover_approval_data)
        
        if signatures_data:
            if 'signatures' not in filled_data:
                filled_data['signatures'] = {}
            filled_data['signatures'].update(signatures_data)
        
        # Save DocumentInstance
        instance.document_instance.filled_data = filled_data
        instance.document_instance.save(update_fields=['filled_data', 'updated_at'])
        
        # Update PilotHandover
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        
        return instance


class PilotHandoverCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new PilotHandover record.
    """
    
    project_id = serializers.UUIDField()
    expected_delivery_date = serializers.DateField()
    assigned_team_members = serializers.ListField(
        child=serializers.CharField(),
        min_length=1
    )
    
    def validate_project_id(self, value):
        """Validate project exists and is available for handover."""
        try:
            project = Project.objects.get(id=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project not found.")
        
        # Check project status
        if project.status not in ['testing', 'client_review', 'completed']:
            raise serializers.ValidationError(
                f"Handovers can only be created for projects in testing or completed status. Current status: {project.status}"
            )
        
        return project
    
    def create(self, validated_data):
        """Create PilotHandover with proper relationships."""
        project = validated_data.pop('project_id')
        
        # Prepare filled_data
        filled_data = {
            'project_reference': {
                'client_school_name': project.client.organization.name,
                'pilot_start_date': project.start_date.isoformat() if project.start_date else None,
                'expected_delivery_date': validated_data['expected_delivery_date'].isoformat(),
                'assigned_team_members': validated_data['assigned_team_members'],
            },
            'checklist': {},
            'handover_approval': {},
            'signatures': {},
        }
        
        # Create DocumentInstance - use first HANDOVER template
        handover_template = DocumentTemplate.objects.filter(template_type='HANDOVER').first()
        if not handover_template:
            # Create a default template if none exists
            handover_template = DocumentTemplate.objects.create(
                name='Internal Pilot Handover',
                template_type='HANDOVER',
                content='<html><body><h1>Internal Handover Document</h1></body></html>',
                status='PUBLISHED'
            )
        
        document_instance = DocumentInstance.objects.create(
            template=handover_template,
            project=project,
            filled_data=filled_data,
            created_by=self.context['request'].user,
            status='DRAFT'
        )
        
        # Create PilotHandover
        pilot_handover = PilotHandover.objects.create(
            project=project,
            document_instance=document_instance,
            expected_delivery_date=validated_data['expected_delivery_date'],
            assigned_team_members=validated_data['assigned_team_members'],
            status='draft',
            created_by=self.context['request'].user
        )
        
        return pilot_handover


class PilotHandoverSignatureSerializer(serializers.Serializer):
    """
    Serializer for signing handover documents.
    """
    
    signature_data = SignatureSerializer()
    
    def validate(self, data):
        """Validate signature data."""
        user = self.context['request'].user
        pilot_handover = self.context['pilot_handover']
        
        # Check if user can sign this handover
        if not pilot_handover.can_be_signed_by(user):
            user_role = getattr(user, 'role', None)
            role_name = user_role.codename if user_role else 'unknown'
            raise serializers.ValidationError(
                f"User with role '{role_name}' cannot sign this handover document."
            )
        
        return data
    
    def save(self, **kwargs):
        """Sign the handover document."""
        pilot_handover = self.context['pilot_handover']
        user = self.context['request'].user
        signature_data = self.validated_data['signature_data']
        
        # Sign the handover
        pilot_handover.sign_handover(user, signature_data)
        
        return pilot_handover


class ChecklistSectionUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating individual checklist sections.
    """
    
    section_data = serializers.DictField()
    
    def validate_section_data(self, value):
        """Validate section data."""
        section_name = self.context.get('section_name')
        if not section_name:
            raise serializers.ValidationError("Section name is required.")
        
        expected_items = PilotHandover.get_checklist_sections().get(section_name, [])
        if not expected_items:
            raise serializers.ValidationError(f"Invalid section name: {section_name}")
        
        # Validate that all items are boolean
        for item, item_value in value.items():
            if item not in expected_items:
                raise serializers.ValidationError(f"Invalid checklist item: {item}")
            if not isinstance(item_value, bool):
                raise serializers.ValidationError(f"Checklist item '{item}' must be a boolean.")
        
        return value
    
    def save(self, **kwargs):
        """Update checklist section."""
        pilot_handover = self.context['pilot_handover']
        section_name = self.context['section_name']
        section_data = self.validated_data['section_data']
        
        # Update checklist section
        pilot_handover.update_checklist_section(section_name, section_data)
        
        return pilot_handover
