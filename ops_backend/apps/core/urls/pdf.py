"""
PDF test URL patterns for the Sumano OMS.
"""
from django.urls import path
from ..views.pdf_test import pdf_test, pdf_status

urlpatterns = [
    path('test/', pdf_test, name='pdf_test'),
    path('status/', pdf_status, name='pdf_status'),
]
