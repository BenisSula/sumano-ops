"""
Authentication views for Sumano OMS.

This module contains API views for authentication endpoints including
login, registration, profile management, and security monitoring.
"""

from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import login, logout
from django.utils import timezone
from apps.core.models import User, Role, SecurityEvent
from apps.core.serializers.auth import (
    LoginSerializer, UserRegistrationSerializer, UserProfileSerializer,
    ChangePasswordSerializer, RoleSerializer, SecurityEventSerializer
)
from apps.core.authentication.permissions import (
    IsAuthenticatedUser, IsSuperAdmin, CanViewUsers, CanManageUsers,
    CanViewSecurityEvents, CanManageSecurityEvents
)
from apps.core.services.security_service import SecurityService


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with security event logging.
    
    This view extends the standard JWT token view to include
    comprehensive security event logging and monitoring.
    """
    
    def post(self, request, *args, **kwargs):
        """Handle JWT token request with security logging."""
        # Log login attempt
        SecurityService.log_security_event(
            event_type='login_attempt',
            user=None,
            ip_address=SecurityService.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method,
            details={'auth_method': 'jwt_token'}
        )
        
        # Call parent method to get tokens
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Extract user from response data
            username = request.data.get('username')
            try:
                user = User.objects.get(username=username)
                
                # Log successful login
                SecurityService.log_security_event(
                    event_type='login_success',
                    user=user,
                    ip_address=SecurityService.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_path=request.path,
                    request_method=request.method,
                    details={'auth_method': 'jwt_token'}
                )
                
                # Reset failed login attempts
                user.reset_failed_login_attempts()
                
            except User.DoesNotExist:
                pass
        else:
            # Log failed login
            username = request.data.get('username')
            try:
                user = User.objects.get(username=username)
                user.increment_failed_login_attempts()
                
                SecurityService.log_security_event(
                    event_type='login_failure',
                    user=user,
                    ip_address=SecurityService.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_path=request.path,
                    request_method=request.method,
                    details={
                        'reason': 'invalid_credentials',
                        'auth_method': 'jwt_token',
                        'failed_attempts': user.failed_login_attempts
                    },
                    severity='medium'
                )
            except User.DoesNotExist:
                SecurityService.log_security_event(
                    event_type='login_failure',
                    user=None,
                    ip_address=SecurityService.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_path=request.path,
                    request_method=request.method,
                    details={
                        'reason': 'user_not_found',
                        'auth_method': 'jwt_token'
                    },
                    severity='medium'
                )
        
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom JWT token refresh view with security event logging.
    """
    
    def post(self, request, *args, **kwargs):
        """Handle JWT token refresh with security logging."""
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Log successful token refresh
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                SecurityService.log_security_event(
                    event_type='token_refresh',
                    user=user,
                    ip_address=SecurityService.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_path=request.path,
                    request_method=request.method,
                    details={'auth_method': 'jwt_refresh'}
                )
        
        return response


class LoginView(APIView):
    """
    Session-based login view.
    
    This view provides session-based authentication as an alternative
    to JWT tokens, with comprehensive security event logging.
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Handle login request."""
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Log user in with session
            login(request, user)
            
            # Generate JWT tokens for API access
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Login successful',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    Logout view for session-based authentication.
    
    This view handles user logout and security event logging.
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def post(self, request):
        """Handle logout request."""
        user = request.user
        
        # Log logout event
        SecurityService.log_security_event(
            event_type='logout',
            user=user,
            ip_address=SecurityService.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method
        )
        
        # Log user out
        logout(request)
        
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)


class UserRegistrationView(generics.CreateAPIView):
    """
    User registration view.
    
    This view handles new user registration with proper validation
    and security event logging.
    """
    
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Handle user registration."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        # Set default role (staff for now, should be configurable)
        try:
            default_role = Role.objects.get(codename='staff')
            user.role = default_role
            user.save()
        except Role.DoesNotExist:
            pass  # No default role available
        
        return Response({
            'message': 'User registered successfully',
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User profile view.
    
    This view allows users to view and update their own profile information.
    """
    
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticatedUser]
    
    def get_object(self):
        """Return the current user."""
        return self.request.user


class ChangePasswordView(APIView):
    """
    Password change view.
    
    This view allows users to change their password with proper validation
    and security event logging.
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def post(self, request):
        """Handle password change request."""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    """
    User list view for administrators.
    
    This view provides a list of all users for administrative purposes.
    """
    
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticatedUser, CanViewUsers]


class RoleListView(generics.ListAPIView):
    """
    Role list view.
    
    This view provides a list of all available roles.
    """
    
    queryset = Role.objects.filter(is_active=True)
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticatedUser]


class SecurityEventListView(generics.ListAPIView):
    """
    Security event list view.
    
    This view provides a list of security events for monitoring and auditing.
    """
    
    queryset = SecurityEvent.objects.all()
    serializer_class = SecurityEventSerializer
    permission_classes = [IsAuthenticatedUser, CanViewSecurityEvents]


class SecurityEventDetailView(generics.RetrieveUpdateAPIView):
    """
    Security event detail view.
    
    This view allows viewing and updating individual security events.
    """
    
    queryset = SecurityEvent.objects.all()
    serializer_class = SecurityEventSerializer
    permission_classes = [IsAuthenticatedUser, CanManageSecurityEvents]


@api_view(['POST'])
@permission_classes([IsAuthenticatedUser, CanManageSecurityEvents])
def resolve_security_events(request):
    """
    Resolve multiple security events.
    
    This endpoint allows administrators to resolve multiple security events at once.
    """
    event_ids = request.data.get('event_ids', [])
    notes = request.data.get('notes', '')
    
    if not event_ids:
        return Response({
            'error': 'event_ids is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    resolved_count = SecurityService.resolve_security_events(
        event_ids, request.user, notes
    )
    
    return Response({
        'message': f'{resolved_count} security events resolved successfully'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticatedUser, CanViewSecurityEvents])
def security_statistics(request):
    """
    Get security statistics.
    
    This endpoint provides security statistics for monitoring and reporting.
    """
    days = int(request.GET.get('days', 30))
    
    stats = SecurityService.get_security_statistics(days)
    
    return Response(stats, status=status.HTTP_200_OK)
