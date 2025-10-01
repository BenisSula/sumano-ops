"""
URL patterns for client-related API endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.core.views.client import ClientViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')

urlpatterns = [
    path('', include(router.urls)),
]
