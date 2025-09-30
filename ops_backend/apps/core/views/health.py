"""
Health check views for the Sumano OMS.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint that returns the status of the application.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'Sumano OMS Backend',
        'version': '0.1.0'
    })


@csrf_exempt
@require_http_methods(["GET"])
def health_detailed(request):
    """
    Detailed health check endpoint with system information.
    """
    import sys
    import django
    from django.conf import settings
    
    return JsonResponse({
        'status': 'healthy',
        'service': 'Sumano OMS Backend',
        'version': '0.1.0',
        'python_version': sys.version,
        'django_version': django.get_version(),
        'debug': settings.DEBUG,
        'database': settings.DATABASES['default']['ENGINE'].split('.')[-1]
    })
