"""
Client serializers for the Sumano Operations Management System.

This module provides serializers for client-related models including
the enhanced Client model with intake functionality.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.core.models import Client, Organization, Contact

User = get_user_model()
# Note: UserProfileSerializer not available, using basic user representation


class UserSerializer(serializers.ModelSerializer):
    """Basic User serializer for client relationships."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model."""
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'legal_name', 'organization_type', 'industry',
            'website', 'description', 'phone', 'email', 'address_line1',
            'address_line2', 'city', 'state_province', 'postal_code',
            'country', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContactSerializer(serializers.ModelSerializer):
    """Serializer for Contact model."""
    
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = Contact
        fields = [
            'id', 'organization', 'organization_name', 'first_name', 'last_name',
            'title', 'department', 'email', 'phone', 'mobile', 'role_type',
            'is_primary_contact', 'status', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization_name', 'created_at', 'updated_at']


class ClientSerializer(serializers.ModelSerializer):
    """Serializer for Client model with intake functionality."""
    
    # Related object serializers
    organization = OrganizationSerializer(read_only=True)
    billing_contact = ContactSerializer(read_only=True)
    primary_contact = serializers.SerializerMethodField()
    
    # Display fields for choices
    relationship_status_display = serializers.CharField(source='get_relationship_status_display', read_only=True)
    contract_type_display = serializers.CharField(source='get_contract_type_display', read_only=True)
    timeline_preference_display = serializers.CharField(source='get_timeline_preference_display', read_only=True)
    
    # Intake-specific computed fields
    is_intake_complete = serializers.SerializerMethodField()
    intake_completion_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = [
            # Basic client information
            'id', 'organization', 'client_since', 'relationship_status', 'relationship_status_display',
            'contract_type', 'contract_type_display', 'billing_contact', 'primary_contact',
            'notes', 'internal_rating', 'created_at', 'updated_at',
            
            # Intake fields - School Information
            'school_name', 'address', 'contact_person', 'role_position',
            'phone_whatsapp', 'email', 'current_website',
            
            # Intake fields - School Statistics
            'number_of_students', 'number_of_staff',
            
            # Intake fields - Project Information
            'project_type', 'project_purpose', 'pilot_scope_features',
            
            # Intake fields - Timeline
            'pilot_start_date', 'pilot_end_date', 'timeline_preference', 'timeline_preference_display',
            
            # Intake fields - Design Preferences
            'design_preferences', 'logo_colors',
            
            # Intake fields - Content and Maintenance
            'content_availability', 'maintenance_plan',
            
            # Intake fields - Financial Commitment
            'token_commitment_fee',
            
            # Intake fields - Additional Information
            'additional_notes', 'acknowledgment',
            
            # Computed fields
            'is_intake_complete', 'intake_completion_percentage',
        ]
        read_only_fields = [
            'id', 'organization', 'primary_contact', 'relationship_status_display',
            'contract_type_display', 'timeline_preference_display',
            'is_intake_complete', 'intake_completion_percentage',
            'created_at', 'updated_at'
        ]
    
    def get_primary_contact(self, obj):
        """Get the primary contact for this client."""
        if obj.primary_contact:
            return ContactSerializer(obj.primary_contact).data
        return None
    
    def get_is_intake_complete(self, obj):
        """Check if intake form is complete."""
        required_fields = [
            'school_name', 'contact_person', 'email', 'project_type',
            'project_purpose', 'pilot_scope_features', 'timeline_preference'
        ]
        
        for field in required_fields:
            value = getattr(obj, field, None)
            if not value or (isinstance(value, list) and len(value) == 0):
                return False
        return True
    
    def get_intake_completion_percentage(self, obj):
        """Calculate intake form completion percentage."""
        intake_fields = [
            'school_name', 'address', 'contact_person', 'role_position',
            'phone_whatsapp', 'email', 'current_website', 'number_of_students',
            'number_of_staff', 'project_type', 'project_purpose',
            'pilot_scope_features', 'pilot_start_date', 'pilot_end_date',
            'timeline_preference', 'design_preferences', 'logo_colors',
            'content_availability', 'maintenance_plan', 'token_commitment_fee',
            'additional_notes', 'acknowledgment'
        ]
        
        completed_fields = 0
        total_fields = len(intake_fields)
        
        for field in intake_fields:
            value = getattr(obj, field, None)
            if value is not None:
                if isinstance(value, (list, dict)):
                    if len(value) > 0:
                        completed_fields += 1
                elif value != '':
                    completed_fields += 1
        
        return round((completed_fields / total_fields) * 100, 1)


class ClientCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new clients with intake data."""
    
    class Meta:
        model = Client
        fields = [
            # Organization relationship (will be created separately)
            'client_since', 'relationship_status', 'contract_type',
            'billing_contact', 'notes', 'internal_rating',
            
            # Intake fields
            'school_name', 'address', 'contact_person', 'role_position',
            'phone_whatsapp', 'email', 'current_website',
            'number_of_students', 'number_of_staff',
            'project_type', 'project_purpose', 'pilot_scope_features',
            'pilot_start_date', 'pilot_end_date', 'timeline_preference',
            'design_preferences', 'logo_colors', 'content_availability',
            'maintenance_plan', 'token_commitment_fee',
            'additional_notes', 'acknowledgment'
        ]
    
    def validate_project_type(self, value):
        """Validate project type selections."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Project type must be a list.")
        
        valid_types = [
            'website_development', 'mobile_app', 'student_portal',
            'parent_portal', 'teacher_portal', 'admin_portal',
            'learning_management_system', 'communication_system',
            'assessment_tools', 'reporting_system', 'other'
        ]
        
        for project_type in value:
            if project_type not in valid_types:
                raise serializers.ValidationError(
                    f"Invalid project type: {project_type}"
                )
        
        return value
    
    def validate_project_purpose(self, value):
        """Validate project purpose selections."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Project purpose must be a list.")
        
        valid_purposes = [
            'improve_student_engagement', 'enhance_communication',
            'streamline_administration', 'modernize_technology',
            'improve_parent_involvement', 'enhance_learning_experience',
            'reduce_manual_processes', 'improve_data_management',
            'increase_accessibility', 'other'
        ]
        
        for purpose in value:
            if purpose not in valid_purposes:
                raise serializers.ValidationError(
                    f"Invalid project purpose: {purpose}"
                )
        
        return value
    
    def validate_pilot_scope_features(self, value):
        """Validate pilot scope feature selections."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Pilot scope features must be a list.")
        
        valid_features = [
            'user_authentication', 'student_management', 'class_management',
            'gradebook', 'attendance_tracking', 'parent_communication',
            'teacher_tools', 'admin_dashboard', 'reporting_analytics',
            'mobile_responsive', 'multi_language', 'integration_apis',
            'data_export', 'backup_recovery', 'security_features'
        ]
        
        for feature in value:
            if feature not in valid_features:
                raise serializers.ValidationError(
                    f"Invalid pilot scope feature: {feature}"
                )
        
        return value


class ClientIntakeUpdateSerializer(serializers.ModelSerializer):
    """Serializer specifically for updating client intake information."""
    
    class Meta:
        model = Client
        fields = [
            'school_name', 'address', 'contact_person', 'role_position',
            'phone_whatsapp', 'email', 'current_website',
            'number_of_students', 'number_of_staff',
            'project_type', 'project_purpose', 'pilot_scope_features',
            'pilot_start_date', 'pilot_end_date', 'timeline_preference',
            'design_preferences', 'logo_colors', 'content_availability',
            'maintenance_plan', 'token_commitment_fee',
            'additional_notes', 'acknowledgment'
        ]
    
    def validate(self, attrs):
        """Validate intake data."""
        # Ensure required fields are provided for intake completion
        required_fields = ['school_name', 'contact_person', 'email']
        
        for field in required_fields:
            if field in attrs and not attrs[field]:
                raise serializers.ValidationError(
                    f"{field} is required for intake completion."
                )
        
        return attrs
