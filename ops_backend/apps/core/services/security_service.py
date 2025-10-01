"""
Security service for Sumano OMS.

This service handles security event logging, authentication monitoring,
and security-related operations.
"""

from django.utils import timezone
from django.db import models
from apps.core.models import SecurityEvent, User


class SecurityService:
    """
    Service for managing security events and monitoring.
    
    This service provides methods for logging security events,
    monitoring authentication attempts, and managing security-related operations.
    """
    
    @classmethod
    def log_security_event(cls, event_type, user=None, ip_address=None, 
                          user_agent=None, request_path=None, request_method=None,
                          details=None, severity='medium'):
        """
        Log a security event.
        
        Args:
            event_type (str): Type of security event
            user (User, optional): User associated with the event
            ip_address (str, optional): IP address of the request
            user_agent (str, optional): User agent string
            request_path (str, optional): Requested URL path
            request_method (str, optional): HTTP method
            details (dict, optional): Additional event details
            severity (str): Severity level (low, medium, high, critical)
            
        Returns:
            SecurityEvent: The created security event record
        """
        # Create security event
        security_event = SecurityEvent.objects.create(
            event_type=event_type,
            user=user,
            ip_address=ip_address or '127.0.0.1',
            user_agent=user_agent or '',
            request_path=request_path or '',
            request_method=request_method or '',
            details=details or {},
            severity=severity
        )
        
        return security_event
    
    @classmethod
    def get_client_ip(cls, request):
        """Get the client IP address from the request."""
        if not request:
            return '127.0.0.1'
        
        # Check for forwarded IP first
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        return ip
    
    @classmethod
    def get_failed_login_attempts(cls, ip_address, hours=24):
        """
        Get number of failed login attempts from an IP in the last N hours.
        
        Args:
            ip_address (str): IP address to check
            hours (int): Number of hours to look back
            
        Returns:
            int: Number of failed login attempts
        """
        since = timezone.now() - timezone.timedelta(hours=hours)
        
        return SecurityEvent.objects.filter(
            event_type='login_failure',
            ip_address=ip_address,
            created_at__gte=since
        ).count()
    
    @classmethod
    def is_ip_blocked(cls, ip_address, max_attempts=5, hours=24):
        """
        Check if an IP address should be blocked due to too many failed attempts.
        
        Args:
            ip_address (str): IP address to check
            max_attempts (int): Maximum allowed attempts
            hours (int): Time window in hours
            
        Returns:
            bool: True if IP should be blocked
        """
        failed_attempts = cls.get_failed_login_attempts(ip_address, hours)
        return failed_attempts >= max_attempts
    
    @classmethod
    def get_user_login_history(cls, user, days=30):
        """
        Get login history for a user.
        
        Args:
            user (User): User to get history for
            days (int): Number of days to look back
            
        Returns:
            QuerySet: Security events for login attempts
        """
        since = timezone.now() - timezone.timedelta(days=days)
        
        return SecurityEvent.objects.filter(
            user=user,
            event_type__in=['login_success', 'login_failure'],
            created_at__gte=since
        ).order_by('-created_at')
    
    @classmethod
    def get_suspicious_activity(cls, days=7, severity_threshold='high'):
        """
        Get suspicious security activity.
        
        Args:
            days (int): Number of days to look back
            severity_threshold (str): Minimum severity level
            
        Returns:
            QuerySet: Security events above threshold
        """
        since = timezone.now() - timezone.timedelta(days=days)
        
        severity_levels = ['low', 'medium', 'high', 'critical']
        threshold_index = severity_levels.index(severity_threshold)
        allowed_severities = severity_levels[threshold_index:]
        
        return SecurityEvent.objects.filter(
            created_at__gte=since,
            severity__in=allowed_severities,
            is_resolved=False
        ).order_by('-created_at')
    
    @classmethod
    def resolve_security_events(cls, event_ids, resolved_by_user, notes=""):
        """
        Resolve multiple security events.
        
        Args:
            event_ids (list): List of security event IDs to resolve
            resolved_by_user (User): User resolving the events
            notes (str): Resolution notes
            
        Returns:
            int: Number of events resolved
        """
        events = SecurityEvent.objects.filter(id__in=event_ids, is_resolved=False)
        
        resolved_count = 0
        for event in events:
            event.resolve(resolved_by_user, notes)
            resolved_count += 1
        
        return resolved_count
    
    @classmethod
    def get_security_statistics(cls, days=30):
        """
        Get security statistics for the specified period.
        
        Args:
            days (int): Number of days to analyze
            
        Returns:
            dict: Security statistics
        """
        since = timezone.now() - timezone.timedelta(days=days)
        
        events = SecurityEvent.objects.filter(created_at__gte=since)
        
        stats = {
            'total_events': events.count(),
            'login_attempts': events.filter(event_type='login_attempt').count(),
            'login_successes': events.filter(event_type='login_success').count(),
            'login_failures': events.filter(event_type='login_failure').count(),
            'access_denied': events.filter(event_type='access_denied').count(),
            'suspicious_activity': events.filter(event_type='suspicious_activity').count(),
            'unresolved_events': events.filter(is_resolved=False).count(),
            'severity_breakdown': {
                'low': events.filter(severity='low').count(),
                'medium': events.filter(severity='medium').count(),
                'high': events.filter(severity='high').count(),
                'critical': events.filter(severity='critical').count(),
            },
            'top_ip_addresses': list(
                events.values('ip_address')
                .annotate(count=models.Count('id'))
                .order_by('-count')[:10]
            ),
            'top_users': list(
                events.filter(user__isnull=False)
                .values('user__username')
                .annotate(count=models.Count('id'))
                .order_by('-count')[:10]
            ),
        }
        
        return stats
    
    @classmethod
    def cleanup_old_events(cls, days=90):
        """
        Clean up old security events.
        
        Args:
            days (int): Number of days to keep events
            
        Returns:
            int: Number of events deleted
        """
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Only delete resolved events older than cutoff
        deleted_count, _ = SecurityEvent.objects.filter(
            created_at__lt=cutoff_date,
            is_resolved=True
        ).delete()
        
        return deleted_count
