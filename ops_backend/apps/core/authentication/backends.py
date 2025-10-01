"""
Authentication backends for Sumano OMS.

This module provides custom authentication backends that integrate
with our RBAC system and security event logging.
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.core.models import SecurityEvent
from apps.core.services.security_service import SecurityService

User = get_user_model()


class RBACAuthenticationBackend(ModelBackend):
    """
    Custom authentication backend that integrates with RBAC system.
    
    This backend extends Django's default ModelBackend to include
    role-based access control and security event logging.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with RBAC integration and security logging.
        
        Args:
            request: HTTP request object
            username: Username or email
            password: User password
            **kwargs: Additional authentication parameters
            
        Returns:
            User instance if authentication successful, None otherwise
        """
        # Get client IP and user agent for security logging
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        # Log login attempt
        SecurityService.log_security_event(
            event_type='login_attempt',
            user=None,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request.path if request else '',
            request_method=request.method if request else '',
            details={'username': username}
        )
        
        # Check if account is locked
        if username:
            try:
                user = User.objects.get(username=username)
                if user.is_account_locked():
                    SecurityService.log_security_event(
                        event_type='login_failure',
                        user=user,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_path=request.path if request else '',
                        request_method=request.method if request else '',
                        details={
                            'reason': 'account_locked',
                            'locked_until': user.account_locked_until.isoformat() if user.account_locked_until else None
                        },
                        severity='high'
                    )
                    return None
            except User.DoesNotExist:
                pass
        
        # Perform standard authentication
        user = super().authenticate(request, username, password, **kwargs)
        
        if user:
            # Reset failed login attempts on successful login
            user.reset_failed_login_attempts()
            
            # Log successful login
            SecurityService.log_security_event(
                event_type='login_success',
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path if request else '',
                request_method=request.method if request else '',
                details={'role': user.role.codename if user.role else None}
            )
        else:
            # Log failed login attempt
            if username:
                try:
                    user = User.objects.get(username=username)
                    user.increment_failed_login_attempts()
                    
                    SecurityService.log_security_event(
                        event_type='login_failure',
                        user=user,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_path=request.path if request else '',
                        request_method=request.method if request else '',
                        details={
                            'reason': 'invalid_password',
                            'failed_attempts': user.failed_login_attempts
                        },
                        severity='medium'
                    )
                except User.DoesNotExist:
                    SecurityService.log_security_event(
                        event_type='login_failure',
                        user=None,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_path=request.path if request else '',
                        request_method=request.method if request else '',
                        details={'reason': 'user_not_found'},
                        severity='medium'
                    )
        
        return user
    
    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        if not request:
            return '127.0.0.1'
        
        # Check for forwarded IP first
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        return ip


class JWTAuthenticationBackend(RBACAuthenticationBackend):
    """
    JWT authentication backend that extends RBAC backend.
    
    This backend handles JWT token authentication while maintaining
    RBAC functionality and security event logging.
    """
    
    def authenticate(self, request, token=None, **kwargs):
        """
        Authenticate user using JWT token.
        
        Args:
            request: HTTP request object
            token: JWT token string
            **kwargs: Additional authentication parameters
            
        Returns:
            User instance if authentication successful, None otherwise
        """
        if not token:
            return None
        
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
            
            # Validate JWT token
            access_token = AccessToken(token)
            user_id = access_token.get('user_id')
            
            if not user_id:
                return None
            
            # Get user and verify they're still active
            user = User.objects.get(id=user_id, is_active=True)
            
            # Log token validation
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
            
            SecurityService.log_security_event(
                event_type='permission_check',
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path if request else '',
                request_method=request.method if request else '',
                details={'auth_method': 'jwt_token'}
            )
            
            return user
            
        except (InvalidToken, TokenError, User.DoesNotExist):
            # Log invalid token attempt
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
            
            SecurityService.log_security_event(
                event_type='access_denied',
                user=None,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path if request else '',
                request_method=request.method if request else '',
                details={'reason': 'invalid_jwt_token'},
                severity='medium'
            )
            
            return None
