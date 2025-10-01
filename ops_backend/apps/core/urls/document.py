"""
URL patterns for document-related endpoints.

This module defines URL patterns for document template management
and PDF generation functionality.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.core.views.document import (
    DocumentTemplateListView,
    DocumentTemplateDetailView,
    DocumentTemplateCreateView,
    DocumentTemplateUpdateView,
    DocumentInstanceListView,
    DocumentInstanceDetailView,
    generate_document,
    download_pdf,
    sign_document,
    document_statistics,
)

# Create router for viewset-based views
router = DefaultRouter()

urlpatterns = [
    # Document template endpoints
    path('templates/', DocumentTemplateListView.as_view(), name='document-template-list'),
    path('templates/<uuid:pk>/', DocumentTemplateDetailView.as_view(), name='document-template-detail'),
    path('templates/create/', DocumentTemplateCreateView.as_view(), name='document-template-create'),
    path('templates/<uuid:pk>/update/', DocumentTemplateUpdateView.as_view(), name='document-template-update'),
    
    # Document instance endpoints
    path('', DocumentInstanceListView.as_view(), name='document-instance-list'),
    path('<uuid:pk>/', DocumentInstanceDetailView.as_view(), name='document-instance-detail'),
    
    # Document generation and management endpoints
    path('generate/', generate_document, name='document-generate'),
    path('<uuid:document_id>/pdf/', download_pdf, name='document-download-pdf'),
    path('<uuid:document_id>/sign/', sign_document, name='document-sign'),
    path('statistics/', document_statistics, name='document-statistics'),
]
