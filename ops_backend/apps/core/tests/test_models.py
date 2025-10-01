"""
Model unit tests for normalized data models and relationships.

This module tests the core models to ensure proper relationships,
data integrity, and model functionality.
"""

import pytest
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.core.models import (
    Organization, Contact, Client, Project, ProjectPhase,
    DocumentTemplate, DocumentInstance, Role, Permission
)

User = get_user_model()


class TestOrganizationModel:
    """Test Organization model functionality."""
    
    @pytest.mark.django_db
    def test_organization_creation(self):
        """Test basic organization creation."""
        org = Organization.objects.create(
            name="Test Organization",
            organization_type="business",
            email="contact@testorg.com"
        )
        
        assert org.id is not None
        assert org.name == "Test Organization"
        assert org.organization_type == "business"
        assert org.status == "prospect"  # default status
        assert str(org) == "Test Organization"
    
    @pytest.mark.django_db
    def test_organization_string_representation(self):
        """Test organization string representation."""
        org = Organization.objects.create(name="Acme Corp")
        assert str(org) == "Acme Corp"


class TestContactModel:
    """Test Contact model functionality and relationships."""
    
    @pytest.mark.django_db
    def test_contact_creation_with_organization(self):
        """Test contact creation with organization relationship."""
        org = Organization.objects.create(name="Test Org")
        contact = Contact.objects.create(
            organization=org,
            first_name="John",
            last_name="Doe",
            email="john.doe@testorg.com",
            role_type="decision_maker"
        )
        
        assert contact.id is not None
        assert contact.organization == org
        assert contact.full_name == "John Doe"
        assert contact.role_type == "decision_maker"
        assert contact.is_primary_contact is False  # default
    
    @pytest.mark.django_db
    def test_contact_organization_relationship(self):
        """Test contact-organization relationship."""
        org = Organization.objects.create(name="Test Org")
        contact1 = Contact.objects.create(
            organization=org,
            first_name="John",
            last_name="Doe",
            email="john@testorg.com"
        )
        contact2 = Contact.objects.create(
            organization=org,
            first_name="Jane",
            last_name="Smith",
            email="jane@testorg.com"
        )
        
        # Test forward relationship
        assert contact1.organization == org
        assert contact2.organization == org
        
        # Test reverse relationship
        assert org.contacts.count() == 2
        assert contact1 in org.contacts.all()
        assert contact2 in org.contacts.all()
    
    @pytest.mark.django_db
    def test_contact_unique_email_per_organization(self):
        """Test that email is unique per organization."""
        org = Organization.objects.create(name="Test Org")
        Contact.objects.create(
            organization=org,
            first_name="John",
            last_name="Doe",
            email="john@testorg.com"
        )
        
        # Creating another contact with same email in same org should fail
        with pytest.raises(IntegrityError):
            Contact.objects.create(
                organization=org,
                first_name="Jane",
                last_name="Doe",
                email="john@testorg.com"
            )
    
    @pytest.mark.django_db
    def test_contact_string_representation(self):
        """Test contact string representation."""
        org = Organization.objects.create(name="Test Org")
        contact = Contact.objects.create(
            organization=org,
            first_name="John",
            last_name="Doe",
            email="john@testorg.com"
        )
        assert str(contact) == "John Doe (Test Org)"


class TestClientModel:
    """Test Client model functionality and relationships."""
    
    @pytest.mark.django_db
    def test_client_creation_with_organization(self):
        """Test client creation with organization relationship."""
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01",
            relationship_status="active"
        )
        
        assert client.id is not None
        assert client.organization == org
        assert client.client_since.strftime("%Y-%m-%d") == "2024-01-01"
        assert client.relationship_status == "active"
        assert client.is_active is True
    
    @pytest.mark.django_db
    def test_client_organization_one_to_one_relationship(self):
        """Test client-organization one-to-one relationship."""
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        
        # Test forward relationship
        assert client.organization == org
        
        # Test reverse relationship
        assert org.client_profile == client
    
    @pytest.mark.django_db
    def test_client_with_billing_contact(self):
        """Test client with billing contact relationship."""
        org = Organization.objects.create(name="Test Org")
        billing_contact = Contact.objects.create(
            organization=org,
            first_name="Billing",
            last_name="Contact",
            email="billing@testorg.com",
            role_type="billing"
        )
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01",
            billing_contact=billing_contact
        )
        
        assert client.billing_contact == billing_contact
        assert billing_contact in billing_contact.billing_clients.all()


class TestProjectModel:
    """Test Project model functionality and relationships."""
    
    @pytest.mark.django_db
    def test_project_creation_with_client(self):
        """Test project creation with client relationship."""
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        project = Project.objects.create(
            client=client,
            project_name="Test Project",
            service_type="web_development",
            description="A test project",
            start_date="2024-01-01"
        )
        
        assert project.id is not None
        assert project.client == client
        assert project.project_name == "Test Project"
        assert project.service_type == "web_development"
        assert project.client_name == "Test Org"  # property
        assert project.is_active is True  # default status is planning
    
    @pytest.mark.django_db
    def test_project_client_relationship(self):
        """Test project-client relationship."""
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        project1 = Project.objects.create(
            client=client,
            project_name="Project 1",
            service_type="web_development",
            start_date="2024-01-01"
        )
        project2 = Project.objects.create(
            client=client,
            project_name="Project 2",
            service_type="mobile_app",
            start_date="2024-02-01"
        )
        
        # Test forward relationship
        assert project1.client == client
        assert project2.client == client
        
        # Test reverse relationship
        assert client.projects.count() == 2
        assert project1 in client.projects.all()
        assert project2 in client.projects.all()
    
    @pytest.mark.django_db
    def test_project_with_user_manager(self):
        """Test project with user project manager."""
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        user = User.objects.create_user(
            username="pm",
            email="pm@sumano.tech",
            first_name="Project",
            last_name="Manager"
        )
        project = Project.objects.create(
            client=client,
            project_name="Test Project",
            service_type="web_development",
            start_date="2024-01-01",
            project_manager=user
        )
        
        assert project.project_manager == user
        assert project in user.managed_projects.all()


class TestProjectPhaseModel:
    """Test ProjectPhase model functionality and relationships."""
    
    @pytest.mark.django_db
    def test_project_phase_creation(self):
        """Test project phase creation."""
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        project = Project.objects.create(
            client=client,
            project_name="Test Project",
            service_type="web_development",
            start_date="2024-01-01"
        )
        phase = ProjectPhase.objects.create(
            project=project,
            phase_name="Planning Phase",
            phase_number=1,
            description="Initial planning phase",
            start_date="2024-01-01",
            target_end_date="2024-01-15"
        )
        
        assert phase.id is not None
        assert phase.project == project
        assert phase.phase_name == "Planning Phase"
        assert phase.phase_number == 1
        assert phase.status == "not_started"  # default
    
    @pytest.mark.django_db
    def test_project_phase_project_relationship(self):
        """Test project phase-project relationship."""
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        project = Project.objects.create(
            client=client,
            project_name="Test Project",
            service_type="web_development",
            start_date="2024-01-01"
        )
        phase1 = ProjectPhase.objects.create(
            project=project,
            phase_name="Phase 1",
            phase_number=1,
            start_date="2024-01-01",
            target_end_date="2024-01-15"
        )
        phase2 = ProjectPhase.objects.create(
            project=project,
            phase_name="Phase 2",
            phase_number=2,
            start_date="2024-01-16",
            target_end_date="2024-01-30"
        )
        
        # Test forward relationship
        assert phase1.project == project
        assert phase2.project == project
        
        # Test reverse relationship
        assert project.phases.count() == 2
        assert phase1 in project.phases.all()
        assert phase2 in project.phases.all()
    
    @pytest.mark.django_db
    def test_project_phase_unique_number_per_project(self):
        """Test that phase numbers are unique per project."""
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        project = Project.objects.create(
            client=client,
            project_name="Test Project",
            service_type="web_development",
            start_date="2024-01-01"
        )
        ProjectPhase.objects.create(
            project=project,
            phase_name="Phase 1",
            phase_number=1,
            start_date="2024-01-01",
            target_end_date="2024-01-15"
        )
        
        # Creating another phase with same number should fail
        with pytest.raises(IntegrityError):
            ProjectPhase.objects.create(
                project=project,
                phase_name="Phase 1 Duplicate",
                phase_number=1,
                start_date="2024-01-01",
                target_end_date="2024-01-15"
            )


class TestDocumentTemplateModel:
    """Test DocumentTemplate model functionality."""
    
    @pytest.mark.django_db
    def test_document_template_creation(self):
        """Test document template creation."""
        template = DocumentTemplate.objects.create(
            name="Project Proposal Template",
            description="Template for project proposals",
            document_type="proposal",
            template_content="Project: {{project_name}} for {{client_name}}",
            template_format="html"
        )
        
        assert template.id is not None
        assert template.name == "Project Proposal Template"
        assert template.document_type == "proposal"
        assert template.version == "1.0"  # default
        assert template.is_current_version is True  # default
        assert template.status == "draft"  # default
    
    @pytest.mark.django_db
    def test_document_template_version_control(self):
        """Test document template version control."""
        template_v1 = DocumentTemplate.objects.create(
            name="Test Template",
            description="Version 1",
            document_type="proposal",
            template_content="Version 1 content",
            version="1.0"
        )
        template_v2 = DocumentTemplate.objects.create(
            name="Test Template",
            description="Version 2",
            document_type="proposal",
            template_content="Version 2 content",
            version="2.0",
            previous_version=template_v1
        )
        
        assert template_v2.previous_version == template_v1
        assert template_v1 in template_v1.next_versions.all()
    
    @pytest.mark.django_db
    def test_document_template_placeholder_extraction(self):
        """Test placeholder field extraction."""
        template = DocumentTemplate.objects.create(
            name="Test Template",
            description="Test",
            document_type="proposal",
            template_content="Hello {{client_name}}, your project {{project_name}} is ready.",
            template_format="html"
        )
        
        placeholders = template.get_placeholder_fields()
        assert "client_name" in placeholders
        assert "project_name" in placeholders
        assert len(placeholders) == 2


class TestDocumentInstanceModel:
    """Test DocumentInstance model functionality and relationships."""
    
    @pytest.mark.django_db
    def test_document_instance_creation(self):
        """Test document instance creation."""
        # Create related objects
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        project = Project.objects.create(
            client=client,
            project_name="Test Project",
            service_type="web_development",
            start_date="2024-01-01"
        )
        template = DocumentTemplate.objects.create(
            name="Test Template",
            description="Test",
            document_type="proposal",
            template_content="Project: {{project_name}}",
            template_format="html"
        )
        
        # Create document instance
        doc_instance = DocumentInstance.objects.create(
            project=project,
            template=template,
            template_version="1.0",
            document_name="Test Document",
            document_type="proposal",
            filled_data={"project_name": "Test Project"}
        )
        
        assert doc_instance.id is not None
        assert doc_instance.project == project
        assert doc_instance.template == template
        assert doc_instance.status == "draft"  # default
    
    @pytest.mark.django_db
    def test_document_instance_project_relationship(self):
        """Test document instance-project relationship."""
        # Create related objects
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        project = Project.objects.create(
            client=client,
            project_name="Test Project",
            service_type="web_development",
            start_date="2024-01-01"
        )
        template = DocumentTemplate.objects.create(
            name="Test Template",
            description="Test",
            document_type="proposal",
            template_content="Content",
            template_format="html"
        )
        
        # Create document instances
        doc1 = DocumentInstance.objects.create(
            project=project,
            template=template,
            template_version="1.0",
            document_name="Doc 1",
            document_type="proposal",
            filled_data={}
        )
        doc2 = DocumentInstance.objects.create(
            project=project,
            template=template,
            template_version="1.0",
            document_name="Doc 2",
            document_type="proposal",
            filled_data={}
        )
        
        # Test forward relationship
        assert doc1.project == project
        assert doc2.project == project
        
        # Test reverse relationship
        assert project.documents.count() == 2
        assert doc1 in project.documents.all()
        assert doc2 in project.documents.all()
    
    @pytest.mark.django_db
    def test_document_instance_render(self):
        """Test document instance rendering."""
        template = DocumentTemplate.objects.create(
            name="Test Template",
            description="Test",
            document_type="proposal",
            template_content="Hello {{client_name}}, project {{project_name}} is ready.",
            template_format="html"
        )
        
        # Create related objects
        org = Organization.objects.create(name="Test Org")
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        project = Project.objects.create(
            client=client,
            project_name="Test Project",
            service_type="web_development",
            start_date="2024-01-01"
        )
        
        doc_instance = DocumentInstance.objects.create(
            project=project,
            template=template,
            template_version="1.0",
            document_name="Test Document",
            document_type="proposal",
            filled_data={
                "client_name": "Test Org",
                "project_name": "Test Project"
            }
        )
        
        rendered = doc_instance.render_document()
        expected = "Hello Test Org, project Test Project is ready."
        assert rendered == expected


class TestPermissionModel:
    """Test Permission model functionality."""
    
    @pytest.mark.django_db
    def test_permission_creation(self):
        """Test permission creation."""
        permission = Permission.objects.create(
            name="View Projects",
            codename="view_projects",
            description="Can view project information",
            category="project"
        )
        
        assert permission.id is not None
        assert permission.name == "View Projects"
        assert permission.codename == "view_projects"
        assert permission.category == "project"
        assert permission.is_active is True  # default


class TestRoleModel:
    """Test Role model functionality and relationships."""
    
    @pytest.mark.django_db
    def test_role_creation(self):
        """Test role creation."""
        role = Role.objects.create(
            name="Project Manager",
            codename="project_manager",
            description="Manages projects and teams",
            level=3
        )
        
        assert role.id is not None
        assert role.name == "Project Manager"
        assert role.codename == "project_manager"
        assert role.level == 3
        assert role.is_active is True  # default
    
    @pytest.mark.django_db
    def test_role_with_permissions(self):
        """Test role with permissions."""
        permission1 = Permission.objects.create(
            name="View Projects",
            codename="view_projects",
            description="Can view projects",
            category="project"
        )
        permission2 = Permission.objects.create(
            name="Edit Projects",
            codename="edit_projects",
            description="Can edit projects",
            category="project"
        )
        
        role = Role.objects.create(
            name="Project Manager",
            codename="project_manager",
            description="Manages projects",
            level=3
        )
        role.permissions.add(permission1, permission2)
        
        assert role.permissions.count() == 2
        assert permission1 in role.permissions.all()
        assert permission2 in role.permissions.all()
        assert role.has_permission("view_projects")
        assert role.has_permission("edit_projects")
        assert not role.has_permission("delete_projects")


class TestUserModel:
    """Test User model functionality and relationships."""
    
    @pytest.mark.django_db
    def test_user_creation(self):
        """Test user creation with custom fields."""
        user = User.objects.create_user(
            username="testuser",
            email="test@sumano.tech",
            first_name="Test",
            last_name="User",
            employee_id="EMP001",
            department="development"
        )
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@sumano.tech"
        assert user.full_name == "Test User"
        assert user.employee_id == "EMP001"
        assert user.department == "development"
        assert user.employment_status == "active"  # default
    
    @pytest.mark.django_db
    def test_user_with_role(self):
        """Test user with role relationship."""
        role = Role.objects.create(
            name="Developer",
            codename="developer",
            description="Software developer",
            level=2
        )
        
        user = User.objects.create_user(
            username="devuser",
            email="dev@sumano.tech",
            first_name="Dev",
            last_name="User",
            role=role
        )
        
        assert user.role == role
        assert user in role.users.all()
    
    @pytest.mark.django_db
    def test_user_permissions_via_role(self):
        """Test user permissions via role."""
        permission = Permission.objects.create(
            name="View Projects",
            codename="view_projects",
            description="Can view projects",
            category="project"
        )
        
        role = Role.objects.create(
            name="Developer",
            codename="developer",
            description="Software developer",
            level=2
        )
        role.permissions.add(permission)
        
        user = User.objects.create_user(
            username="devuser",
            email="dev@sumano.tech",
            first_name="Dev",
            last_name="User",
            role=role
        )
        
        assert user.has_permission("view_projects")
        assert permission in user.get_all_permissions()


class TestModelRelationships:
    """Test complex model relationships and data integrity."""
    
    @pytest.mark.django_db
    def test_complete_project_workflow(self):
        """Test complete project workflow with all relationships."""
        # Create organization and client
        org = Organization.objects.create(
            name="Acme Corporation",
            organization_type="business",
            email="contact@acme.com"
        )
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01",
            relationship_status="active"
        )
        
        # Create contacts
        primary_contact = Contact.objects.create(
            organization=org,
            first_name="John",
            last_name="Doe",
            email="john@acme.com",
            role_type="decision_maker",
            is_primary_contact=True
        )
        billing_contact = Contact.objects.create(
            organization=org,
            first_name="Jane",
            last_name="Smith",
            email="jane@acme.com",
            role_type="billing"
        )
        client.billing_contact = billing_contact
        client.save()
        
        # Create user and role
        permission = Permission.objects.create(
            name="Manage Projects",
            codename="manage_projects",
            description="Can manage projects",
            category="project"
        )
        role = Role.objects.create(
            name="Project Manager",
            codename="project_manager",
            description="Manages projects",
            level=3
        )
        role.permissions.add(permission)
        
        user = User.objects.create_user(
            username="pm",
            email="pm@sumano.tech",
            first_name="Project",
            last_name="Manager",
            role=role
        )
        
        # Create project
        project = Project.objects.create(
            client=client,
            project_name="Acme Website Redesign",
            project_code="PROJ-2024-001",
            service_type="web_development",
            description="Complete website redesign for Acme Corporation",
            start_date="2024-01-01",
            target_end_date="2024-03-31",
            project_manager=user,
            client_contact=primary_contact
        )
        
        # Create project phases
        phase1 = ProjectPhase.objects.create(
            project=project,
            phase_name="Discovery & Planning",
            phase_number=1,
            description="Requirements gathering and planning",
            start_date="2024-01-01",
            target_end_date="2024-01-15"
        )
        phase2 = ProjectPhase.objects.create(
            project=project,
            phase_name="Design & Development",
            phase_number=2,
            description="UI/UX design and development",
            start_date="2024-01-16",
            target_end_date="2024-02-28"
        )
        
        # Create document template and instance
        template = DocumentTemplate.objects.create(
            name="Project Proposal Template",
            description="Standard project proposal template",
            document_type="proposal",
            template_content="Project: {{project_name}} for {{client_name}}",
            template_format="html"
        )
        
        doc_instance = DocumentInstance.objects.create(
            project=project,
            template=template,
            template_version="1.0",
            document_name="Acme Website Proposal",
            document_type="proposal",
            filled_data={
                "project_name": "Acme Website Redesign",
                "client_name": "Acme Corporation"
            },
            created_by=user
        )
        
        # Verify all relationships
        assert org.client_profile == client
        assert client.organization == org
        assert client.billing_contact == billing_contact
        assert org.contacts.count() == 2
        
        assert project.client == client
        assert project.project_manager == user
        assert project.client_contact == primary_contact
        assert client.projects.count() == 1
        
        assert phase1.project == project
        assert phase2.project == project
        assert project.phases.count() == 2
        
        assert doc_instance.project == project
        assert doc_instance.created_by == user
        assert project.documents.count() == 1
        
        assert user.role == role
        assert user.has_permission("manage_projects")
        
        # Test string representations
        assert str(org) == "Acme Corporation"
        assert str(primary_contact) == "John Doe (Acme Corporation)"
        assert str(client) == "Acme Corporation (Client since 2024-01-01)"
        assert str(project) == "Acme Website Redesign - Acme Corporation"
        assert str(phase1) == "Acme Website Redesign - Phase 1: Discovery & Planning"
    
    @pytest.mark.django_db
    def test_no_data_duplication(self):
        """Test that no data duplication occurs in normalized schema."""
        # Create organization
        org = Organization.objects.create(
            name="Test Organization",
            email="contact@testorg.com"
        )
        
        # Create client (one-to-one with organization)
        client = Client.objects.create(
            organization=org,
            client_since="2024-01-01"
        )
        
        # Create multiple projects for same client
        project1 = Project.objects.create(
            client=client,
            project_name="Project 1",
            service_type="web_development",
            start_date="2024-01-01"
        )
        project2 = Project.objects.create(
            client=client,
            project_name="Project 2",
            service_type="mobile_app",
            start_date="2024-02-01"
        )
        
        # Verify no client name duplication in projects
        # Projects should reference client, not store client name
        assert project1.client_name == "Test Organization"  # property, not field
        assert project2.client_name == "Test Organization"  # property, not field
        
        # Verify client name is stored only once in organization
        assert Organization.objects.filter(name="Test Organization").count() == 1
        
        # Verify both projects reference same client instance
        assert project1.client == project2.client
        assert project1.client == client
