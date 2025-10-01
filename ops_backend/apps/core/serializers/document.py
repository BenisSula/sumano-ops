"""
Document serializers for the Sumano Operations Management System.

This module provides serializers for document templates and instances,
ensuring proper data validation and API responses.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.core.models import DocumentTemplate, DocumentInstance, Project

User = get_user_model()


class DocumentTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for DocumentTemplate model.
    """
    
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    
    class Meta:
        model = DocumentTemplate
        fields = [
            'id',
            'name',
            'description',
            'template_type',
            'content',
            'version',
            'status',
            'required_fields',
            'optional_fields',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_template_type(self, value):
        """Validate template type choice."""
        valid_types = [choice[0] for choice in DocumentTemplate._meta.get_field('template_type').choices]
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid template type. Must be one of: {', '.join(valid_types)}")
        return value
    
    def validate_status(self, value):
        """Validate status choice."""
        valid_statuses = [choice[0] for choice in DocumentTemplate._meta.get_field('status').choices]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value
    
    def validate_required_fields(self, value):
        """Validate required fields is a list of strings."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Required fields must be a list.")
        for field in value:
            if not isinstance(field, str):
                raise serializers.ValidationError("All required fields must be strings.")
        return value
    
    def validate_optional_fields(self, value):
        """Validate optional fields is a list of strings."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Optional fields must be a list.")
        for field in value:
            if not isinstance(field, str):
                raise serializers.ValidationError("All optional fields must be strings.")
        return value


class DocumentInstanceSerializer(serializers.ModelSerializer):
    """
    Serializer for DocumentInstance model.
    """
    
    template_name = serializers.CharField(
        source='template.name',
        read_only=True
    )
    template_type = serializers.CharField(
        source='template.template_type',
        read_only=True
    )
    project_name = serializers.CharField(
        source='project.name',
        read_only=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    signed_by_username = serializers.CharField(
        source='signed_by.username',
        read_only=True
    )
    file_url = serializers.CharField(
        source='get_file_url',
        read_only=True
    )
    file_size = serializers.IntegerField(
        source='get_file_size',
        read_only=True
    )
    
    class Meta:
        model = DocumentInstance
        fields = [
            'id',
            'template',
            'template_name',
            'template_type',
            'project',
            'project_name',
            'filled_data',
            'document_title',
            'document_number',
            'status',
            'generated_pdf',
            'file_url',
            'file_size',
            'signed_by',
            'signed_by_username',
            'signed_at',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'template_name',
            'template_type',
            'project_name',
            'document_number',
            'generated_pdf',
            'file_url',
            'file_size',
            'signed_by',
            'signed_by_username',
            'signed_at',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
    
    def validate_status(self, value):
        """Validate status choice."""
        valid_statuses = [choice[0] for choice in DocumentInstance._meta.get_field('status').choices]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value
    
    def validate_filled_data(self, value):
        """Validate filled data is a dictionary."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Filled data must be a dictionary.")
        return value


class DocumentGenerationSerializer(serializers.Serializer):
    """
    Serializer for document generation requests.
    """
    
    template_name = serializers.CharField(
        max_length=255,
        help_text="Name of the template to use for generation"
    )
    project_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="ID of the project this document belongs to"
    )
    data = serializers.DictField(
        help_text="Data to fill the template"
    )
    signature_context = serializers.DictField(
        required=False,
        allow_null=True,
        help_text="Additional context for document signing"
    )
    
    def validate_template_name(self, value):
        """Validate that the template exists and is published."""
        try:
            template = DocumentTemplate.objects.get(
                name=value,
                status='PUBLISHED'
            )
        except DocumentTemplate.DoesNotExist:
            raise serializers.ValidationError(
                f"Published template '{value}' not found."
            )
        return value
    
    def validate_project_id(self, value):
        """Validate that the project exists."""
        if value is not None:
            try:
                Project.objects.get(id=value)
            except Project.DoesNotExist:
                raise serializers.ValidationError(
                    f"Project with ID '{value}' not found."
                )
        return value
    
    def validate_data(self, value):
        """Validate that data is a dictionary."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Data must be a dictionary.")
        return value
    
    def validate_signature_context(self, value):
        """Validate signature context if provided."""
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Signature context must be a dictionary.")
        return value


class DocumentSignSerializer(serializers.Serializer):
    """
    Serializer for document signing requests.
    """
    
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional notes about the signing"
    )
