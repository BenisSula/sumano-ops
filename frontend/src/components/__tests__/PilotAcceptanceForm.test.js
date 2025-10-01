/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import PilotAcceptanceForm from '../PilotAcceptanceForm';

// Mock the hooks
jest.mock('../../hooks/useOfflineStorage', () => ({
  useOfflineStorage: () => ({
    saveOffline: jest.fn(),
    syncOffline: jest.fn(),
    isOnline: true,
  }),
}));

jest.mock('../../hooks/useApiClient', () => ({
  useApiClient: () => ({
    submitPilotAcceptance: jest.fn(),
    generateAcceptancePDF: jest.fn(),
    isLoading: false,
    error: null,
  }),
}));

// Mock react-signature-canvas
jest.mock('react-signature-canvas', () => {
  return function MockSignaturePad({ ref, ...props }) {
    React.useImperativeHandle(ref, () => ({
      toDataURL: () => 'data:image/png;base64,mock-signature-data',
      clear: jest.fn(),
    }));
    return <div data-testid="signature-canvas" {...props} />;
  };
});

// Create a test theme
const theme = createTheme();

// Test wrapper component
const TestWrapper = ({ children }) => (
  <ThemeProvider theme={theme}>
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      {children}
    </LocalizationProvider>
  </ThemeProvider>
);

describe('PilotAcceptanceForm', () => {
  const mockProjectId = 'test-project-id';
  const mockOnSuccess = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the pilot acceptance form', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    expect(screen.getByText('Pilot Project Acceptance Form')).toBeInTheDocument();
    expect(screen.getByText('Project Information')).toBeInTheDocument();
    expect(screen.getByText('Acceptance Checklist')).toBeInTheDocument();
    expect(screen.getByText('Digital Signatures')).toBeInTheDocument();
  });

  it('displays completion progress correctly', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    expect(screen.getByText(/Completion Progress: 0%/)).toBeInTheDocument();
  });

  it('shows all checklist items', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    // Check for key checklist items
    expect(screen.getByText('Digital Gateway Live')).toBeInTheDocument();
    expect(screen.getByText('Mobile Friendly')).toBeInTheDocument();
    expect(screen.getByText('All Pages Present')).toBeInTheDocument();
    expect(screen.getByText('Portals Linked')).toBeInTheDocument();
    expect(screen.getByText('Social Media Embedded')).toBeInTheDocument();
    expect(screen.getByText('Logo & Colors Correct')).toBeInTheDocument();
    expect(screen.getByText('Photos & Content Displayed')).toBeInTheDocument();
    expect(screen.getByText('Layout & Design OK')).toBeInTheDocument();
    expect(screen.getByText('Staff Training Completed')).toBeInTheDocument();
    expect(screen.getByText('Training Materials Provided')).toBeInTheDocument();
    expect(screen.getByText('No Critical Errors')).toBeInTheDocument();
    expect(screen.getByText('Minor Issues Resolved')).toBeInTheDocument();
  });

  it('updates completion progress when checklist items are checked', async () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    // Initially 0% completion
    expect(screen.getByText(/Completion Progress: 0%/)).toBeInTheDocument();

    // Check first checklist item
    const firstCheckbox = screen.getAllByRole('checkbox')[0];
    fireEvent.click(firstCheckbox);

    // Should show updated progress (1 out of 12 items = ~8.3%)
    await waitFor(() => {
      expect(screen.getByText(/Completion Progress: 8%/)).toBeInTheDocument();
    });
  });

  it('displays acceptance status options', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    // Click on acceptance status dropdown
    const statusDropdown = screen.getByLabelText('Acceptance Status');
    fireEvent.mouseDown(statusDropdown);

    // Check for status options
    expect(screen.getByText('Accepted')).toBeInTheDocument();
    expect(screen.getByText('Accepted with Conditions')).toBeInTheDocument();
    expect(screen.getByText('Not Accepted')).toBeInTheDocument();
  });

  it('shows signature capture areas', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    expect(screen.getByText('School Representative')).toBeInTheDocument();
    expect(screen.getByText('Company Representative')).toBeInTheDocument();
    expect(screen.getAllByText('Capture Signature')).toHaveLength(2);
  });

  it('opens signature dialog when capture button is clicked', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    const captureButtons = screen.getAllByText('Capture Signature');
    fireEvent.click(captureButtons[0]);

    expect(screen.getByText('Capture School Representative Signature')).toBeInTheDocument();
    expect(screen.getByDisplayValue('')).toBeInTheDocument(); // Name field
  });

  it('disables submit button when checklist is incomplete', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    const submitButton = screen.getByText('Submit Acceptance');
    expect(submitButton).toBeDisabled();
  });

  it('enables submit button when checklist is complete', async () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    // Check all checklist items
    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach(checkbox => {
      fireEvent.click(checkbox);
    });

    // Submit button should be enabled
    await waitFor(() => {
      const submitButton = screen.getByText('Submit Acceptance');
      expect(submitButton).not.toBeDisabled();
    });
  });

  it('shows completion requirement message when incomplete', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    expect(screen.getByText(
      'Please complete all checklist items before submitting the acceptance form.'
    )).toBeInTheDocument();
  });

  it('calls onCancel when cancel button is clicked', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('handles signature capture and save', async () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    // Open signature dialog
    const captureButtons = screen.getAllByText('Capture Signature');
    fireEvent.click(captureButtons[0]);

    // Fill signature form
    const nameInput = screen.getByDisplayValue('');
    const titleInput = screen.getByDisplayValue('');

    fireEvent.change(nameInput, { target: { value: 'Jane Doe' } });
    fireEvent.change(titleInput, { target: { value: 'Principal' } });

    // Save signature
    const saveButton = screen.getByText('Save Signature');
    fireEvent.click(saveButton);

    // Dialog should close and signature should be displayed
    await waitFor(() => {
      expect(screen.queryByText('Capture School Representative Signature')).not.toBeInTheDocument();
    });

    expect(screen.getByText('✓ Signed by Jane Doe')).toBeInTheDocument();
    expect(screen.getByText('Principal')).toBeInTheDocument();
  });

  it('handles signature dialog cancel', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    // Open signature dialog
    const captureButtons = screen.getAllByText('Capture Signature');
    fireEvent.click(captureButtons[0]);

    // Cancel dialog
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    // Dialog should close
    expect(screen.queryByText('Capture School Representative Signature')).not.toBeInTheDocument();
  });

  it('shows preview PDF button', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    expect(screen.getByText('Preview PDF')).toBeInTheDocument();
  });

  it('displays form fields with proper labels', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    expect(screen.getByLabelText('Acceptance Status')).toBeInTheDocument();
    expect(screen.getByLabelText('Completion Date')).toBeInTheDocument();
    expect(screen.getByLabelText('Token Payment Amount')).toBeInTheDocument();
    expect(screen.getByLabelText('Issues to Resolve (Optional)')).toBeInTheDocument();
  });

  it('shows checklist item descriptions', () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    expect(screen.getByText('Payment gateway is operational and tested')).toBeInTheDocument();
    expect(screen.getByText('Website is fully responsive on mobile devices')).toBeInTheDocument();
    expect(screen.getByText('All required pages are created and functional')).toBeInTheDocument();
  });

  it('updates checklist completion percentage display', async () => {
    render(
      <TestWrapper>
        <PilotAcceptanceForm
          projectId={mockProjectId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      </TestWrapper>
    );

    // Check a few items
    const checkboxes = screen.getAllByRole('checkbox');
    
    // Check first 3 items (25% completion)
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    fireEvent.click(checkboxes[2]);

    await waitFor(() => {
      expect(screen.getByText(/Checklist Completion: 25%/)).toBeInTheDocument();
    });
  });
});
