"""
Data migration to populate sample document templates.
"""

from django.db import migrations
from django.core.files.base import ContentFile
import os


def populate_sample_templates(apps, schema_editor):
    """
    Create sample document templates for each document type.
    """
    DocumentTemplate = apps.get_model('core', 'DocumentTemplate')
    User = apps.get_model('core', 'User')
    
    # Get or create a superuser for the templates
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@sumano.local',
                password='admin123',
                is_superuser=True,
                is_staff=True
            )
    except:
        admin_user = None
    
    # Sample templates data
    templates_data = [
        {
            'name': 'Client Intake Form',
            'description': 'Standard client intake form for new projects',
            'template_type': 'INTAKE',
            'content': _get_intake_template_content(),
            'required_fields': ['company_name', 'contact_name', 'email', 'project_type', 'description'],
            'optional_fields': ['phone', 'address', 'budget_range', 'timeline', 'requirements'],
        },
        {
            'name': 'Project Acceptance Document',
            'description': 'Formal project acceptance and agreement document',
            'template_type': 'ACCEPTANCE',
            'content': _get_acceptance_template_content(),
            'required_fields': ['project_name', 'client_name', 'project_manager', 'start_date', 'completion_date'],
            'optional_fields': ['service_type', 'description', 'deliverables', 'budget', 'payment_terms'],
        },
        {
            'name': 'Change Request Form',
            'description': 'Document for tracking project change requests',
            'template_type': 'CHANGE',
            'content': _get_change_template_content(),
            'required_fields': ['request_id', 'project_name', 'requested_by', 'request_date', 'change_type', 'description'],
            'optional_fields': ['priority', 'justification', 'business_impact', 'technical_impact', 'cost_impact'],
        },
        {
            'name': 'Project Handover Document',
            'description': 'Document for project completion and handover',
            'template_type': 'HANDOVER',
            'content': _get_handover_template_content(),
            'required_fields': ['project_name', 'client_name', 'project_manager', 'start_date', 'completion_date'],
            'optional_fields': ['project_status', 'primary_deliverables', 'documentation', 'testing_results', 'support_contact'],
        },
        {
            'name': 'Legal Agreement Template',
            'description': 'Template for legal agreements and contracts',
            'template_type': 'LEGAL',
            'content': _get_legal_template_content(),
            'required_fields': ['document_type', 'first_party', 'second_party', 'effective_date', 'term'],
            'optional_fields': ['scope_of_work', 'payment_terms', 'intellectual_property', 'liability', 'governing_law'],
        },
    ]
    
    # Create templates
    for template_data in templates_data:
        template, created = DocumentTemplate.objects.get_or_create(
            name=template_data['name'],
            defaults={
                'description': template_data['description'],
                'template_type': template_data['template_type'],
                'content': template_data['content'],
                'required_fields': template_data['required_fields'],
                'optional_fields': template_data['optional_fields'],
                'status': 'PUBLISHED',
                'created_by': admin_user,
            }
        )
        if created:
            print(f"Created template: {template.name}")


def _get_intake_template_content():
    """Get the intake template HTML content."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Client Intake Document</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; color: #333; }
        .header { text-align: center; border-bottom: 3px solid #2c5aa0; padding-bottom: 20px; margin-bottom: 30px; }
        .company-logo { font-size: 24px; font-weight: bold; color: #2c5aa0; margin-bottom: 10px; }
        .document-title { font-size: 28px; font-weight: bold; color: #2c5aa0; margin-bottom: 10px; }
        .section { margin-bottom: 25px; }
        .section-title { font-size: 18px; font-weight: bold; color: #2c5aa0; border-bottom: 2px solid #e0e0e0; padding-bottom: 5px; margin-bottom: 15px; }
        .field { margin-bottom: 10px; }
        .field-label { font-weight: bold; display: inline-block; width: 150px; }
        .field-value { display: inline-block; min-height: 20px; padding: 5px; border-bottom: 1px solid #ccc; min-width: 300px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-logo">{{ system.company }}</div>
        <div class="document-title">Client Intake Document</div>
        <div class="document-subtitle">Project: {{ data.project_name|default:"Not specified" }}</div>
    </div>
    <div class="section">
        <div class="section-title">Client Information</div>
        <div class="field">
            <span class="field-label">Company Name:</span>
            <span class="field-value">{{ data.company_name|default:"Not provided" }}</span>
        </div>
        <div class="field">
            <span class="field-label">Contact Person:</span>
            <span class="field-value">{{ data.contact_name|default:"Not provided" }}</span>
        </div>
        <div class="field">
            <span class="field-label">Email:</span>
            <span class="field-value">{{ data.email|default:"Not provided" }}</span>
        </div>
    </div>
</body>
</html>"""


def _get_acceptance_template_content():
    """Get the acceptance template HTML content."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Project Acceptance Document</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; color: #333; }
        .header { text-align: center; border-bottom: 3px solid #28a745; padding-bottom: 20px; margin-bottom: 30px; }
        .company-logo { font-size: 24px; font-weight: bold; color: #28a745; margin-bottom: 10px; }
        .document-title { font-size: 28px; font-weight: bold; color: #28a745; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-logo">{{ system.company }}</div>
        <div class="document-title">Project Acceptance Document</div>
        <div class="document-subtitle">Project: {{ data.project_name|default:"Not specified" }}</div>
    </div>
    <div class="section">
        <div class="section-title">Project Overview</div>
        <div class="field">
            <span class="field-label">Project Name:</span>
            <span class="field-value">{{ data.project_name|default:"Not provided" }}</span>
        </div>
        <div class="field">
            <span class="field-label">Client:</span>
            <span class="field-value">{{ data.client_name|default:"Not provided" }}</span>
        </div>
    </div>
</body>
</html>"""


def _get_change_template_content():
    """Get the change template HTML content."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Change Request Document</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; color: #333; }
        .header { text-align: center; border-bottom: 3px solid #ffc107; padding-bottom: 20px; margin-bottom: 30px; }
        .company-logo { font-size: 24px; font-weight: bold; color: #ffc107; margin-bottom: 10px; }
        .document-title { font-size: 28px; font-weight: bold; color: #ffc107; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-logo">{{ system.company }}</div>
        <div class="document-title">Change Request Document</div>
        <div class="document-subtitle">Project: {{ data.project_name|default:"Not specified" }}</div>
    </div>
    <div class="section">
        <div class="section-title">Change Request Information</div>
        <div class="field">
            <span class="field-label">Request ID:</span>
            <span class="field-value">{{ data.request_id|default:"Not assigned" }}</span>
        </div>
        <div class="field">
            <span class="field-label">Project Name:</span>
            <span class="field-value">{{ data.project_name|default:"Not provided" }}</span>
        </div>
    </div>
</body>
</html>"""


def _get_handover_template_content():
    """Get the handover template HTML content."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Project Handover Document</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; color: #333; }
        .header { text-align: center; border-bottom: 3px solid #17a2b8; padding-bottom: 20px; margin-bottom: 30px; }
        .company-logo { font-size: 24px; font-weight: bold; color: #17a2b8; margin-bottom: 10px; }
        .document-title { font-size: 28px; font-weight: bold; color: #17a2b8; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-logo">{{ system.company }}</div>
        <div class="document-title">Project Handover Document</div>
        <div class="document-subtitle">Project: {{ data.project_name|default:"Not specified" }}</div>
    </div>
    <div class="section">
        <div class="section-title">Project Information</div>
        <div class="field">
            <span class="field-label">Project Name:</span>
            <span class="field-value">{{ data.project_name|default:"Not provided" }}</span>
        </div>
        <div class="field">
            <span class="field-label">Client:</span>
            <span class="field-value">{{ data.client_name|default:"Not provided" }}</span>
        </div>
    </div>
</body>
</html>"""


def _get_legal_template_content():
    """Get the legal template HTML content."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Legal Document</title>
    <style>
        body { font-family: Times New Roman, serif; line-height: 1.8; margin: 20px; color: #333; }
        .header { text-align: center; border-bottom: 3px solid #6f42c1; padding-bottom: 20px; margin-bottom: 30px; }
        .company-logo { font-size: 24px; font-weight: bold; color: #6f42c1; margin-bottom: 10px; }
        .document-title { font-size: 28px; font-weight: bold; color: #6f42c1; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-logo">{{ system.company }}</div>
        <div class="document-title">Legal Document</div>
        <div class="document-subtitle">{{ data.document_type|default:"Legal Agreement" }}</div>
    </div>
    <div class="section">
        <div class="section-title">Parties</div>
        <div class="field">
            <span class="field-label">First Party:</span>
            <span class="field-value">{{ data.first_party|default:"Sumano Tech" }}</span>
        </div>
        <div class="field">
            <span class="field-label">Second Party:</span>
            <span class="field-value">{{ data.second_party|default:"Client" }}</span>
        </div>
    </div>
</body>
</html>"""


def reverse_populate_templates(apps, schema_editor):
    """
    Remove sample templates.
    """
    DocumentTemplate = apps.get_model('core', 'DocumentTemplate')
    DocumentTemplate.objects.filter(
        name__in=[
            'Client Intake Form',
            'Project Acceptance Document',
            'Change Request Form',
            'Project Handover Document',
            'Legal Agreement Template',
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_documenttemplate_options_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_sample_templates, reverse_populate_templates),
    ]
