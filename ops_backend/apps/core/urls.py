"""
Main URL patterns for the core app.
"""
from django.urls import path, include

urlpatterns = [
    path('health/', include('apps.core.urls.health')),
    path('pdf/', include('apps.core.urls.pdf')),
]
