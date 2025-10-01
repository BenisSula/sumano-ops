"""
URL patterns for the core app.
"""
from django.urls import path, include

urlpatterns = [
    path('health/', include('apps.core.urls.health')),
    path('auth/', include('apps.core.urls.auth.auth')),
    path('documents/', include('apps.core.urls.document')),
    path('', include('apps.core.urls.client')),
    path('', include('apps.core.urls.pilot_acceptance')),
    path('', include('apps.core.urls.change_request')),
    path('', include('apps.core.urls.pilot_handover')),
    path('', include('apps.core.urls.attachment')),
]
