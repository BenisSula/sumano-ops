"""
PDF Generation Service for the Sumano Operations Management System.

This module provides a unified PDF generation service that handles all document
types across the system, ensuring consistent formatting and branding.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, Tuple
from io import BytesIO

from django.conf import settings
from django.template import Template, Context
from django.template.loader import get_template
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django.contrib.auth import get_user_model

# from weasyprint import HTML, CSS
# from weasyprint.text.fonts import FontConfiguration

from apps.core.models import DocumentTemplate, DocumentInstance, Project
from apps.core.services.security_service import SecurityService

User = get_user_model()
logger = logging.getLogger(__name__)


class PDFGenerationService:
    """
    Unified PDF generation service for all document types.
    
    This service handles PDF generation from HTML templates with consistent
    formatting, performance monitoring, and error handling.
    """
    
    # Performance thresholds (in seconds)
    PERFORMANCE_THRESHOLDS = {
        'simple': 3,      # 1-2 pages, text-only
        'standard': 5,    # 3-5 pages with basic formatting
        'complex': 8,     # 5+ pages with images, tables
        'low_end': 12,    # Complex documents on low-end hardware
    }
    
    @classmethod
    def generate_from_template(
        cls,
        template_name: str,
        data: Dict[str, Any],
        signature_context: Optional[Dict[str, Any]] = None,
        user: Optional[User] = None,
        project: Optional[Project] = None
    ) -> Tuple[DocumentInstance, bytes]:
        """
        Generate a PDF document from a template with provided data.
        
        Args:
            template_name (str): Name of the document template
            data (dict): Data to fill the template
            signature_context (dict, optional): Additional context for signatures
            user (User, optional): User generating the document
            project (Project, optional): Project this document belongs to
            
        Returns:
            tuple: (DocumentInstance, pdf_bytes)
            
        Raises:
            ValueError: If template not found or data validation fails
            Exception: If PDF generation fails
        """
        start_time = time.time()
        
        try:
            # Get the template
            template = cls._get_template(template_name)
            
            # Validate data
            is_valid, missing_fields = cls.validate_required_fields(template, data)
            if not is_valid:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Prepare template context
            context = cls._prepare_template_context(data, signature_context, user, project)
            
            # Generate PDF
            pdf_bytes = cls._generate_pdf(template, context)
            
            # Create document instance
            document_instance = cls._create_document_instance(
                template, data, pdf_bytes, user, project
            )
            
            # Log performance
            generation_time = time.time() - start_time
            cls._log_performance(template_name, generation_time, len(pdf_bytes))
            
            # Log security event
            if user:
                SecurityService.log_security_event(
                    event_type='document_generated',
                    user=user,
                    ip_address='127.0.0.1',  # Internal service call
                    user_agent='PDFGenerationService',
                    request_path='/api/documents/generate/',
                    request_method='POST',
                    details={
                        'template_name': template_name,
                        'template_type': template.template_type,
                        'generation_time_seconds': generation_time,
                        'pdf_size_bytes': len(pdf_bytes),
                    },
                    severity='low'
                )
            
            logger.info(f"PDF generated successfully: {template_name} in {generation_time:.2f}s")
            return document_instance, pdf_bytes
            
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"PDF generation failed: {template_name} after {generation_time:.2f}s - {str(e)}")
            raise
    
    @classmethod
    def store_audited_copy(
        cls,
        pdf_bytes: bytes,
        metadata: Dict[str, Any],
        user: Optional[User] = None
    ) -> str:
        """
        Store a PDF copy with audit metadata.
        
        Args:
            pdf_bytes (bytes): PDF content
            metadata (dict): Metadata about the document
            user (User, optional): User who requested storage
            
        Returns:
            str: Path to stored file
        """
        try:
            # Generate filename
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"audit_{timestamp}_{metadata.get('template_type', 'unknown')}.pdf"
            
            # Store file
            file_path = default_storage.save(
                f'documents/audit/{filename}',
                ContentFile(pdf_bytes)
            )
            
            # Log storage event
            if user:
                SecurityService.log_security_event(
                    event_type='document_stored',
                    user=user,
                    ip_address='127.0.0.1',
                    user_agent='PDFGenerationService',
                    request_path='/api/documents/audit/',
                    request_method='POST',
                    details={
                        'file_path': file_path,
                        'file_size_bytes': len(pdf_bytes),
                        'metadata': metadata,
                    },
                    severity='low'
                )
            
            logger.info(f"PDF stored for audit: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to store audited PDF copy: {str(e)}")
            raise
    
    @classmethod
    def validate_required_fields(
        cls,
        template: DocumentTemplate,
        data: Dict[str, Any]
    ) -> Tuple[bool, list]:
        """
        Validate that provided data contains all required fields for the template.
        
        Args:
            template (DocumentTemplate): Template to validate against
            data (dict): Data to validate
            
        Returns:
            tuple: (is_valid, missing_fields)
        """
        return template.validate_data(data)
    
    @classmethod
    def _get_template(cls, template_name: str) -> DocumentTemplate:
        """Get a published template by name."""
        try:
            template = DocumentTemplate.objects.get(
                name=template_name,
                status='PUBLISHED'
            )
            return template
        except DocumentTemplate.DoesNotExist:
            raise ValueError(f"Published template not found: {template_name}")
    
    @classmethod
    def _prepare_template_context(
        cls,
        data: Dict[str, Any],
        signature_context: Optional[Dict[str, Any]] = None,
        user: Optional[User] = None,
        project: Optional[Project] = None
    ) -> Context:
        """Prepare the template context with all necessary data."""
        context_data = {
            'data': data,
            'generated_at': timezone.now(),
            'generated_by': user,
            'project': project,
        }
        
        # Add signature context if provided
        if signature_context:
            context_data['signature'] = signature_context
        
        # Add system information
        context_data.update({
            'system': {
                'name': 'Sumano Operations Management System',
                'version': '1.0.0',
                'company': 'Sumano Tech',
            }
        })
        
        return Context(context_data)
    
    @classmethod
    def _generate_pdf(cls, template: DocumentTemplate, context: Context) -> bytes:
        """Generate PDF from template and context."""
        try:
            # Create Django template from content
            django_template = Template(template.content)
            rendered_html = django_template.render(context)
            
            # TODO: Implement WeasyPrint PDF generation
            # For now, return a placeholder PDF
            pdf_content = f"PDF placeholder for template: {template.name}\n\n{rendered_html}"
            pdf_bytes = pdf_content.encode('utf-8')
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            raise Exception(f"PDF generation failed: {str(e)}")
    
    @classmethod
    def _create_document_instance(
        cls,
        template: DocumentTemplate,
        data: Dict[str, Any],
        pdf_bytes: bytes,
        user: Optional[User] = None,
        project: Optional[Project] = None
    ) -> DocumentInstance:
        """Create a DocumentInstance with the generated PDF."""
        try:
            # Generate document title
            document_title = f"{template.name} - {data.get('title', 'Document')}"
            if project:
                document_title = f"{document_title} - {project.project_name}"
            
            # Generate document number
            timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
            document_number = f"{template.template_type}-{timestamp}"
            
            # Create document instance
            document_instance = DocumentInstance.objects.create(
                template=template,
                project=project,
                filled_data=data,
                document_title=document_title,
                document_number=document_number,
                created_by=user or User.objects.filter(is_superuser=True).first()
            )
            
            # Save PDF file
            filename = f"{document_number}.pdf"
            document_instance.generated_pdf.save(
                filename,
                ContentFile(pdf_bytes),
                save=True
            )
            
            return document_instance
            
        except Exception as e:
            logger.error(f"Failed to create document instance: {str(e)}")
            raise
    
    @classmethod
    def _log_performance(cls, template_name: str, generation_time: float, pdf_size: int):
        """Log performance metrics for PDF generation."""
        # Determine document complexity based on size and template type
        complexity = cls._determine_complexity(pdf_size, template_name)
        threshold = cls.PERFORMANCE_THRESHOLDS.get(complexity, cls.PERFORMANCE_THRESHOLDS['complex'])
        
        if generation_time > threshold:
            logger.warning(
                f"PDF generation performance issue: {template_name} "
                f"took {generation_time:.2f}s (threshold: {threshold}s) "
                f"complexity: {complexity}"
            )
        else:
            logger.info(
                f"PDF generation performance OK: {template_name} "
                f"took {generation_time:.2f}s (threshold: {threshold}s) "
                f"complexity: {complexity}"
            )
    
    @classmethod
    def _determine_complexity(cls, pdf_size: int, template_name: str) -> str:
        """Determine document complexity based on size and template type."""
        # Simple heuristic based on file size and template type
        if pdf_size < 50000:  # < 50KB
            return 'simple'
        elif pdf_size < 200000:  # < 200KB
            return 'standard'
        else:
            return 'complex'
    
    @classmethod
    def get_performance_statistics(cls, days: int = 7) -> Dict[str, Any]:
        """Get performance statistics for PDF generation."""
        from django.db.models import Avg, Count
        from datetime import timedelta
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # This would require adding performance logging to the database
        # For now, return basic statistics
        return {
            'total_documents': DocumentInstance.objects.filter(
                created_at__range=(start_date, end_date)
            ).count(),
            'average_generation_time': 0,  # Would be calculated from performance logs
            'performance_thresholds': cls.PERFORMANCE_THRESHOLDS,
        }
