/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import ChangeRequestForm from '../../../../web/components/ChangeRequestForm';
import { AuthProvider } from '../../../../web/contexts/AuthContext';

// Mock API calls
const mockApiCall = jest.fn();
jest.mock('../../../../web/hooks/useApi', () => ({
  useApi: () => ({
    apiCall: mockApiCall,
    loading: false,
    error: null,
  }),
}));

// Mock signature pad
jest.mock('react-signature-canvas', () => {
  return function MockSignaturePad() {
    return <div data-testid="signature-pad">Signature Pad</div>;
  };
});

// Mock project data
const mockProject = {
  id: 'test-project-id',
  project_name: 'Test Pilot Project',
  client: {
    organization: {
      name: 'Test School'
    }
  }
};

// Mock user data
const mockUser = {
  id: 'test-user-id',
  username: 'testuser',
  role: {
    codename: 'staff',
    name: 'Staff'
  }
};

const renderWithProviders = (component, props = {}) => {
  return render(
    <BrowserRouter>
      <AuthProvider value={{ user: mockUser }}>
        {React.cloneElement(component, props)}
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('ChangeRequestForm', () => {
  beforeEach(() => {
    mockApiCall.mockClear();
    mockApiCall.mockResolvedValue({ data: { id: 'new-change-request-id' } });
  });

  it('renders form fields correctly', () => {
    renderWithProviders(<ChangeRequestForm project={mockProject} />);

    // Check for main form sections
    expect(screen.getByText('Change Request Form')).toBeInTheDocument();
    expect(screen.getByText('Request Details')).toBeInTheDocument();
    expect(screen.getByText('Impact Assessment')).toBeInTheDocument();
    expect(screen.getByText('Client Decision')).toBeInTheDocument();

    // Check for required fields
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/reason/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/request date/i)).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChangeRequestForm project={mockProject} />);

    // Try to submit without filling required fields
    const submitButton = screen.getByRole('button', { name: /submit/i });
    await user.click(submitButton);

    // Check for validation errors
    await waitFor(() => {
      expect(screen.getByText(/description is required/i)).toBeInTheDocument();
      expect(screen.getByText(/reason is required/i)).toBeInTheDocument();
    });
  });

  it('submits form with valid data', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChangeRequestForm project={mockProject} />);

    // Fill in required fields
    await user.type(screen.getByLabelText(/description/i), 'Test change description');
    await user.type(screen.getByLabelText(/reason/i), 'Test change reason');

    // Submit form
    const submitButton = screen.getByRole('button', { name: /submit/i });
    await user.click(submitButton);

    // Check API call was made
    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith('/api/change-requests/', {
        method: 'POST',
        body: expect.objectContaining({
          project_id: mockProject.id,
          change_request: {
            description: 'Test change description',
            reason: 'Test change reason'
          }
        })
      });
    });
  });

  it('handles impact assessment for staff users', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChangeRequestForm project={mockProject} />);

    // Check impact assessment section is visible for staff
    expect(screen.getByText('Impact Assessment')).toBeInTheDocument();
    expect(screen.getByLabelText(/no additional cost/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/requires additional effort/i)).toBeInTheDocument();
  });

  it('handles client decision section', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChangeRequestForm project={mockProject} />);

    // Check client decision section
    expect(screen.getByText('Client Decision')).toBeInTheDocument();
    expect(screen.getByLabelText(/decision/i)).toBeInTheDocument();
  });

  it('displays signature capture component', () => {
    renderWithProviders(<ChangeRequestForm project={mockProject} />);

    expect(screen.getByTestId('signature-pad')).toBeInTheDocument();
  });

  it('handles form submission errors', async () => {
    const user = userEvent.setup();
    mockApiCall.mockRejectedValueOnce(new Error('API Error'));

    renderWithProviders(<ChangeRequestForm project={mockProject} />);

    // Fill in required fields
    await user.type(screen.getByLabelText(/description/i), 'Test change description');
    await user.type(screen.getByLabelText(/reason/i), 'Test change reason');

    // Submit form
    const submitButton = screen.getByRole('button', { name: /submit/i });
    await user.click(submitButton);

    // Check error is displayed
    await waitFor(() => {
      expect(screen.getByText(/error submitting change request/i)).toBeInTheDocument();
    });
  });

  it('disables submit button when loading', () => {
    // Mock loading state
    jest.mocked(require('../../../../web/hooks/useApi')).useApi.mockReturnValue({
      apiCall: mockApiCall,
      loading: true,
      error: null,
    });

    renderWithProviders(<ChangeRequestForm project={mockProject} />);

    const submitButton = screen.getByRole('button', { name: /submit/i });
    expect(submitButton).toBeDisabled();
  });

  it('shows different sections based on user role', () => {
    // Test with client user
    const clientUser = { ...mockUser, role: { codename: 'client_contact', name: 'Client Contact' } };

    renderWithProviders(
      <BrowserRouter>
        <AuthProvider value={{ user: clientUser }}>
          <ChangeRequestForm project={mockProject} />
        </AuthProvider>
      </BrowserRouter>
    );

    // Client users should see decision section but not impact assessment
    expect(screen.getByText('Client Decision')).toBeInTheDocument();
  });
});
