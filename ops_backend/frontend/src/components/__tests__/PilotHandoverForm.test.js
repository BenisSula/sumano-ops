/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PilotHandoverForm from '../PilotHandoverForm';
import { AuthContext } from '../../contexts/AuthContext';
import { OfflineContext } from '../../contexts/OfflineContext';
import { useApiClient } from '../../hooks/useApiClient';
import { useOfflineSync } from '../../hooks/useOfflineSync';

// Mock the hooks and contexts
jest.mock('../../hooks/useApiClient');
jest.mock('../../hooks/useOfflineSync');
jest.mock('react-signature-canvas', () => {
  return React.forwardRef((props, ref) => (
    <canvas
      ref={ref}
      data-testid="signature-canvas"
      {...props}
    />
  ));
});

// Mock context providers
const mockAuthContext = {
  user: {
    id: 'user-1',
    username: 'testuser',
    email: 'test@example.com',
    role: 'staff'
  }
};

const mockOfflineContext = {
  isOnline: true,
  syncPendingChanges: jest.fn()
};

const mockApiClient = {
  get: jest.fn(),
  post: jest.fn(),
  patch: jest.fn(),
  delete: jest.fn()
};

const mockOfflineSync = {
  syncToServer: jest.fn(),
  syncFromServer: jest.fn()
};

// Mock project data
const mockProjects = [
  {
    id: 'project-1',
    project_name: 'Test Project 1',
    client_organization_name: 'Test School 1'
  },
  {
    id: 'project-2',
    project_name: 'Test Project 2',
    client_organization_name: 'Test School 2'
  }
];

// Mock handover data
const mockHandoverData = {
  id: 'handover-1',
  project: 'project-1',
  status: 'draft',
  document_instance_detail: {
    filled_data: {
      expected_delivery_date: '2024-02-01',
      assigned_team_members: ['Team Member 1', 'Team Member 2'],
      checklist: {
        technical_setup: {
          domain_configured: true,
          ssl_active: false,
          site_load_ok: true
        },
        core_pages: {
          home_completed: false,
          about_news_added: true
        }
      },
      team_lead_signature: {
        name: 'Test Team Lead',
        signature: 'base64_signature',
        date: '2024-01-15T10:00:00Z'
      }
    }
  },
  approval_notes: 'Test approval notes'
};

const renderWithProviders = (component, options = {}) => {
  const { authContext = mockAuthContext, offlineContext = mockOfflineContext } = options;
  
  return render(
    <AuthContext.Provider value={authContext}>
      <OfflineContext.Provider value={offlineContext}>
        {component}
      </OfflineContext.Provider>
    </AuthContext.Provider>
  );
};

describe('PilotHandoverForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useApiClient.mockReturnValue(mockApiClient);
    useOfflineSync.mockReturnValue(mockOfflineSync);
    
    // Mock successful API responses
    mockApiClient.get.mockResolvedValue({
      data: { results: mockProjects }
    });
  });

  describe('Component Rendering', () => {
    test('renders form with all sections', async () => {
      renderWithProviders(<PilotHandoverForm />);
      
      await waitFor(() => {
        expect(screen.getByText('Internal Pilot Handover')).toBeInTheDocument();
        expect(screen.getByText('Project Information')).toBeInTheDocument();
        expect(screen.getByText('Internal Handover Checklist')).toBeInTheDocument();
        expect(screen.getByText('Team Lead Approval')).toBeInTheDocument();
      });
    });

    test('displays completion percentage', async () => {
      renderWithProviders(<PilotHandoverForm />);
      
      await waitFor(() => {
        expect(screen.getByText(/Completion: 0%/)).toBeInTheDocument();
      });
    });

    test('loads projects on mount', async () => {
      renderWithProviders(<PilotHandoverForm />);
      
      await waitFor(() => {
        expect(mockApiClient.get).toHaveBeenCalledWith('/api/projects/');
      });
    });
  });

  describe('Project Selection', () => {
    test('allows project selection in create mode', async () => {
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        const projectSelect = screen.getByLabelText(/Project/);
        expect(projectSelect).not.toBeDisabled();
      });
    });

    test('disables project selection in view mode', async () => {
      renderWithProviders(<PilotHandoverForm mode="view" handoverId="handover-1" />);
      
      mockApiClient.get.mockResolvedValueOnce({ data: mockHandoverData });
      
      await waitFor(() => {
        const projectSelect = screen.getByLabelText(/Project/);
        expect(projectSelect).toBeDisabled();
      });
    });
  });

  describe('Checklist Functionality', () => {
    test('allows updating checklist items in create mode', async () => {
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        const checkbox = screen.getByLabelText(/Domain Configured/);
        expect(checkbox).not.toBeDisabled();
        
        fireEvent.click(checkbox);
        expect(checkbox).toBeChecked();
      });
    });

    test('disables checklist items in view mode', async () => {
      renderWithProviders(<PilotHandoverForm mode="view" handoverId="handover-1" />);
      
      mockApiClient.get.mockResolvedValueOnce({ data: mockHandoverData });
      
      await waitFor(() => {
        const checkbox = screen.getByLabelText(/Domain Configured/);
        expect(checkbox).toBeDisabled();
      });
    });

    test('updates completion percentage when checklist items change', async () => {
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        // Initially 0%
        expect(screen.getByText(/Completion: 0%/)).toBeInTheDocument();
        
        // Check a few items
        fireEvent.click(screen.getByLabelText(/Domain Configured/));
        fireEvent.click(screen.getByLabelText(/SSL Active/));
        
        // Should update completion percentage
        expect(screen.getByText(/Completion: \d+%/)).toBeInTheDocument();
      });
    });
  });

  describe('Team Member Management', () => {
    test('allows adding team members', async () => {
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        const addButton = screen.getByText('Add Team Member');
        fireEvent.click(addButton);
        
        const teamMemberInputs = screen.getAllByPlaceholderText('Team member name');
        expect(teamMemberInputs).toHaveLength(1);
      });
    });

    test('allows removing team members', async () => {
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        // Add a team member first
        fireEvent.click(screen.getByText('Add Team Member'));
        
        const removeButton = screen.getByText('Remove');
        fireEvent.click(removeButton);
        
        const teamMemberInputs = screen.queryAllByPlaceholderText('Team member name');
        expect(teamMemberInputs).toHaveLength(0);
      });
    });

    test('disables team member management in view mode', async () => {
      renderWithProviders(<PilotHandoverForm mode="view" handoverId="handover-1" />);
      
      mockApiClient.get.mockResolvedValueOnce({ data: mockHandoverData });
      
      await waitFor(() => {
        expect(screen.queryByText('Add Team Member')).not.toBeInTheDocument();
        expect(screen.queryByText('Remove')).not.toBeInTheDocument();
      });
    });
  });

  describe('Signature Functionality', () => {
    test('renders signature canvas', async () => {
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        expect(screen.getByTestId('signature-canvas')).toBeInTheDocument();
      });
    });

    test('provides signature controls in create/edit mode', async () => {
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        expect(screen.getByText('Capture Signature')).toBeInTheDocument();
        expect(screen.getByText('Clear Signature')).toBeInTheDocument();
      });
    });

    test('hides signature controls in view mode', async () => {
      renderWithProviders(<PilotHandoverForm mode="view" handoverId="handover-1" />);
      
      mockApiClient.get.mockResolvedValueOnce({ data: mockHandoverData });
      
      await waitFor(() => {
        expect(screen.queryByText('Capture Signature')).not.toBeInTheDocument();
        expect(screen.queryByText('Clear Signature')).not.toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    test('submits form with correct data in create mode', async () => {
      const user = userEvent.setup();
      mockApiClient.post.mockResolvedValue({ data: { id: 'new-handover' } });
      
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        expect(screen.getByText('Create Handover')).toBeInTheDocument();
      });
      
      // Fill required fields
      const projectSelect = screen.getByLabelText(/Project/);
      await user.selectOptions(projectSelect, 'project-1');
      
      const dateInput = screen.getByLabelText(/Expected Delivery Date/);
      await user.type(dateInput, '2024-02-01');
      
      // Submit form
      const submitButton = screen.getByText('Create Handover');
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(mockApiClient.post).toHaveBeenCalledWith(
          '/api/pilot-handover/',
          expect.objectContaining({
            project_id: 'project-1',
            expected_delivery_date: '2024-02-01'
          })
        );
      });
    });

    test('submits form with correct data in edit mode', async () => {
      const user = userEvent.setup();
      mockApiClient.patch.mockResolvedValue({ data: mockHandoverData });
      
      renderWithProviders(<PilotHandoverForm mode="edit" handoverId="handover-1" />);
      
      mockApiClient.get.mockResolvedValueOnce({ data: mockHandoverData });
      
      await waitFor(() => {
        expect(screen.getByText('Update Handover')).toBeInTheDocument();
      });
      
      const submitButton = screen.getByText('Update Handover');
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(mockApiClient.patch).toHaveBeenCalledWith(
          '/api/pilot-handover/handover-1/',
          expect.any(Object)
        );
      });
    });

    test('handles submission errors gracefully', async () => {
      const user = userEvent.setup();
      mockApiClient.post.mockRejectedValue(new Error('Network error'));
      
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        expect(screen.getByText('Create Handover')).toBeInTheDocument();
      });
      
      // Fill and submit form
      const projectSelect = screen.getByLabelText(/Project/);
      await user.selectOptions(projectSelect, 'project-1');
      
      const dateInput = screen.getByLabelText(/Expected Delivery Date/);
      await user.type(dateInput, '2024-02-01');
      
      const submitButton = screen.getByText('Create Handover');
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/Failed to save handover/)).toBeInTheDocument();
      });
    });
  });

  describe('Document Generation', () => {
    test('generates document when button is clicked', async () => {
      const user = userEvent.setup();
      const mockBlob = new Blob(['pdf content'], { type: 'application/pdf' });
      mockApiClient.post.mockResolvedValue({ data: mockBlob });
      
      // Mock URL.createObjectURL and related methods
      global.URL.createObjectURL = jest.fn(() => 'mock-url');
      global.URL.revokeObjectURL = jest.fn();
      
      const mockLink = {
        click: jest.fn(),
        href: '',
        download: ''
      };
      const createElementSpy = jest.spyOn(document, 'createElement').mockReturnValue(mockLink);
      const appendChildSpy = jest.spyOn(document.body, 'appendChild').mockImplementation();
      const removeChildSpy = jest.spyOn(document.body, 'removeChild').mockImplementation();
      
      renderWithProviders(<PilotHandoverForm mode="edit" handoverId="handover-1" />);
      
      mockApiClient.get.mockResolvedValueOnce({ data: mockHandoverData });
      
      await waitFor(() => {
        expect(screen.getByText('Generate Document')).toBeInTheDocument();
      });
      
      const generateButton = screen.getByText('Generate Document');
      await user.click(generateButton);
      
      await waitFor(() => {
        expect(mockApiClient.post).toHaveBeenCalledWith(
          '/api/pilot-handover/handover-1/generate_handover_document/'
        );
        expect(createElementSpy).toHaveBeenCalledWith('a');
        expect(mockLink.click).toHaveBeenCalled();
      });
      
      // Clean up mocks
      createElementSpy.mockRestore();
      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
    });
  });

  describe('Offline Functionality', () => {
    test('handles offline mode gracefully', async () => {
      const user = userEvent.setup();
      const offlineContext = {
        ...mockOfflineContext,
        isOnline: false
      };
      
      mockOfflineSync.syncFromServer.mockResolvedValue();
      
      renderWithProviders(
        <PilotHandoverForm mode="create" />,
        { offlineContext }
      );
      
      await waitFor(() => {
        expect(screen.getByText('Create Handover')).toBeInTheDocument();
      });
      
      // Fill and submit form
      const projectSelect = screen.getByLabelText(/Project/);
      await user.selectOptions(projectSelect, 'project-1');
      
      const dateInput = screen.getByLabelText(/Expected Delivery Date/);
      await user.type(dateInput, '2024-02-01');
      
      const submitButton = screen.getByText('Create Handover');
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(mockOfflineSync.syncFromServer).toHaveBeenCalled();
        expect(screen.getByText(/saved offline/)).toBeInTheDocument();
      });
    });
  });

  describe('Loading States', () => {
    test('shows loading state when loading existing handover', () => {
      mockApiClient.get.mockImplementation(() => new Promise(() => {})); // Never resolves
      
      renderWithProviders(<PilotHandoverForm mode="edit" handoverId="handover-1" />);
      
      expect(screen.getByText('Loading handover data...')).toBeInTheDocument();
    });

    test('shows submitting state during form submission', async () => {
      const user = userEvent.setup();
      mockApiClient.post.mockImplementation(() => new Promise(() => {})); // Never resolves
      
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        expect(screen.getByText('Create Handover')).toBeInTheDocument();
      });
      
      // Fill and submit form
      const projectSelect = screen.getByLabelText(/Project/);
      await user.selectOptions(projectSelect, 'project-1');
      
      const dateInput = screen.getByLabelText(/Expected Delivery Date/);
      await user.type(dateInput, '2024-02-01');
      
      const submitButton = screen.getByText('Create Handover');
      await user.click(submitButton);
      
      expect(screen.getByText('Saving...')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('has proper form labels', async () => {
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        expect(screen.getByLabelText(/Project/)).toBeInTheDocument();
        expect(screen.getByLabelText(/Expected Delivery Date/)).toBeInTheDocument();
        expect(screen.getByLabelText(/Team Lead Name/)).toBeInTheDocument();
      });
    });

    test('has proper button labels', async () => {
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Create Handover/ })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Cancel/ })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Add Team Member/ })).toBeInTheDocument();
      });
    });

    test('has proper heading structure', async () => {
      renderWithProviders(<PilotHandoverForm mode="create" />);
      
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Internal Pilot Handover/ })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /Project Information/ })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /Internal Handover Checklist/ })).toBeInTheDocument();
      });
    });
  });
});
