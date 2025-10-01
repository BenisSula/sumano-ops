"""
Security middleware for Sumano OMS.

This middleware provides security monitoring and logging for all requests,
ensuring comprehensive security event tracking across the application.
"""

from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.urls import resolve, Resolver404
from apps.core.services.security_service import SecurityService


class SecurityMiddleware(MiddlewareMixin):
    """
    Security middleware that logs and monitors all requests.
    
    This middleware provides comprehensive security monitoring by:
    - Logging all requests and responses
    - Detecting suspicious patterns
    - Enforcing security policies
    - Providing audit trails
    """
    
    def __init__(self, get_response):
        """Initialize the security middleware."""
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming requests for security monitoring."""
        # Get client information
        ip_address = SecurityService.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check for suspicious patterns
        if self._is_suspicious_request(request, ip_address):
            SecurityService.log_security_event(
                event_type='suspicious_activity',
                user=getattr(request, 'user', None),
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path,
                request_method=request.method,
                details={
                    'reason': 'suspicious_pattern_detected',
                    'query_params': dict(request.GET),
                },
                severity='high'
            )
        
        # Store request info for response processing
        request._security_start_time = timezone.now()
        request._security_ip_address = ip_address
        request._security_user_agent = user_agent
        
        return None
    
    def process_response(self, request, response):
        """Process outgoing responses for security monitoring."""
        # Get stored request info
        start_time = getattr(request, '_security_start_time', None)
        ip_address = getattr(request, '_security_ip_address', '127.0.0.1')
        user_agent = getattr(request, '_security_user_agent', '')
        
        # Calculate response time
        if start_time:
            response_time = (timezone.now() - start_time).total_seconds() * 1000
        else:
            response_time = 0
        
        # Log security events based on response
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            user = user
        else:
            user = None
            
        if response.status_code == 401:
            SecurityService.log_security_event(
                event_type='access_denied',
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path,
                request_method=request.method,
                details={
                    'reason': 'unauthorized',
                    'response_code': response.status_code
                },
                severity='medium'
            )
        elif response.status_code == 403:
            SecurityService.log_security_event(
                event_type='access_denied',
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path,
                request_method=request.method,
                details={
                    'reason': 'forbidden',
                    'response_code': response.status_code
                },
                severity='medium'
            )
        elif response.status_code >= 500:
            SecurityService.log_security_event(
                event_type='suspicious_activity',
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path,
                request_method=request.method,
                details={
                    'reason': 'server_error',
                    'response_code': response.status_code
                },
                severity='high'
            )
        
        # Log slow responses (potential DoS attempts)
        if response_time > 5000:  # 5 seconds
            SecurityService.log_security_event(
                event_type='suspicious_activity',
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path,
                request_method=request.method,
                details={
                    'reason': 'slow_response',
                    'response_time_ms': response_time
                },
                severity='medium'
            )
        
        return response
    
    def _is_suspicious_request(self, request, ip_address):
        """
        Detect suspicious request patterns.
        
        Args:
            request: HTTP request object
            ip_address: Client IP address
            
        Returns:
            bool: True if request appears suspicious
        """
        # Check for SQL injection patterns
        suspicious_patterns = [
            'union select', 'drop table', 'delete from', 'insert into',
            'update set', 'exec(', 'script>', '<script', 'javascript:',
            '../', '..\\', '/etc/passwd', '/proc/version'
        ]
        
        request_string = f"{request.path} {request.META.get('QUERY_STRING', '')}"
        request_string = request_string.lower()
        
        for pattern in suspicious_patterns:
            if pattern in request_string:
                return True
        
        # Check for rapid requests from same IP
        if SecurityService.is_ip_blocked(ip_address, max_attempts=10, hours=1):
            return True
        
        # Check for unusual user agents
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if not user_agent or len(user_agent) < 10:
            return True
        
        # Check for missing or suspicious headers
        if not request.META.get('HTTP_ACCEPT'):
            return True
        
        return False


class IPBlockingMiddleware(MiddlewareMixin):
    """
    Middleware that blocks requests from suspicious IP addresses.
    
    This middleware provides automatic IP blocking based on
    security event patterns and failed authentication attempts.
    """
    
    def __init__(self, get_response):
        """Initialize the IP blocking middleware."""
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Check if IP should be blocked."""
        ip_address = SecurityService.get_client_ip(request)
        
        # Check if IP is blocked
        if SecurityService.is_ip_blocked(ip_address):
            # Log blocking event
            SecurityService.log_security_event(
                event_type='access_denied',
                user=None,
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                details={'reason': 'ip_blocked'},
                severity='high'
            )
            
            return HttpResponseForbidden(
                "Access denied: IP address has been temporarily blocked due to suspicious activity."
            )
        
        return None
