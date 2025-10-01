"""
Authentication serializers for Sumano OMS.

This module contains serializers for authentication endpoints including
login, registration, and user profile management.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.models import User, Role, SecurityEvent
from apps.core.services.security_service import SecurityService


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    
    This serializer handles user authentication with security event logging.
    """
    
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate login credentials."""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Authenticate user
            user = authenticate(
                username=username,
                password=password,
                request=self.context.get('request')
            )
            
            if not user:
                raise serializers.ValidationError(
                    'Invalid username or password.',
                    code='invalid_credentials'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    'User account is disabled.',
                    code='account_disabled'
                )
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(
                'Must include username and password.',
                code='missing_credentials'
            )


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    
    This serializer handles new user creation with proper validation
    and security event logging.
    """
    
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password', 'password_confirm', 'phone', 'mobile',
            'title', 'department', 'employee_id'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        """Validate registration data."""
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        
        if password != password_confirm:
            raise serializers.ValidationError(
                'Passwords do not match.',
                code='password_mismatch'
            )
        
        # Remove password_confirm from attrs
        attrs.pop('password_confirm', None)
        
        return attrs
    
    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'A user with this email already exists.',
                code='email_exists'
            )
        return value
    
    def validate_username(self, value):
        """Validate username uniqueness."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'A user with this username already exists.',
                code='username_exists'
            )
        return value
    
    def create(self, validated_data):
        """Create new user."""
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Log user registration
        request = self.context.get('request')
        if request:
            SecurityService.log_security_event(
                event_type='login_attempt',  # Using login_attempt as closest match
                user=user,
                ip_address=SecurityService.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                details={'action': 'user_registration'},
                severity='low'
            )
        
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information.
    
    This serializer provides user profile data including role information.
    """
    
    role_name = serializers.CharField(source='role.name', read_only=True)
    role_codename = serializers.CharField(source='role.codename', read_only=True)
    additional_roles = serializers.StringRelatedField(many=True, read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'mobile', 'title', 'department', 'employee_id',
            'role_name', 'role_codename', 'additional_roles',
            'hire_date', 'employment_status', 'is_active',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'username', 'date_joined', 'last_login']


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change.
    
    This serializer handles password changes with proper validation
    and security event logging.
    """
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        """Validate old password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                'Current password is incorrect.',
                code='invalid_old_password'
            )
        return value
    
    def validate(self, attrs):
        """Validate password change data."""
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')
        
        if new_password != new_password_confirm:
            raise serializers.ValidationError(
                'New passwords do not match.',
                code='password_mismatch'
            )
        
        # Remove password_confirm from attrs
        attrs.pop('new_password_confirm', None)
        
        return attrs
    
    def save(self):
        """Update user password."""
        user = self.context['request'].user
        new_password = self.validated_data['new_password']
        
        user.set_password(new_password)
        user.save()
        
        # Log password change
        request = self.context['request']
        SecurityService.log_security_event(
            event_type='password_change',
            user=user,
            ip_address=SecurityService.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method,
            details={'action': 'password_changed'},
            severity='medium'
        )
        
        return user


class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer for role information.
    
    This serializer provides role data including permissions.
    """
    
    permissions = serializers.StringRelatedField(many=True, read_only=True)
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = [
            'id', 'name', 'codename', 'description',
            'level', 'parent_role', 'permissions',
            'is_system_role', 'is_active', 'user_count'
        ]
        read_only_fields = ['id', 'user_count']
    
    def get_user_count(self, obj):
        """Get number of users with this role."""
        return obj.users.count()


class SecurityEventSerializer(serializers.ModelSerializer):
    """
    Serializer for security events.
    
    This serializer provides security event data for monitoring and auditing.
    """
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    resolved_by_username = serializers.CharField(source='resolved_by.username', read_only=True)
    
    class Meta:
        model = SecurityEvent
        fields = [
            'id', 'event_type', 'user', 'user_username',
            'ip_address', 'user_agent', 'request_path', 'request_method',
            'details', 'severity', 'is_resolved', 'resolved_by',
            'resolved_by_username', 'resolved_at', 'resolution_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
