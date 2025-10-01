import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ClientIntakeForm from '../ClientIntakeForm';

// Mock the custom hooks
jest.mock('../../hooks/useOfflineStorage', () => ({
  useOfflineStorage: () => ({
    saveOffline: jest.fn(),
    syncOffline: jest.fn(),
    isOnline: true,
  }),
}));

jest.mock('../../hooks/useApiClient', () => ({
  useApiClient: () => ({
    submitClientIntake: jest.fn(),
    generatePDF: jest.fn(),
    isLoading: false,
    error: null,
  }),
}));

const theme = createTheme();

const renderWithTheme = (component) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('ClientIntakeForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders form with all required sections', () => {
    renderWithTheme(<ClientIntakeForm />);
    
    // Check for main title
    expect(screen.getByText('School Pilot Project Intake Form')).toBeInTheDocument();
    
    // Check for section titles
    expect(screen.getByText('School Information')).toBeInTheDocument();
    expect(screen.getByText('Project Information')).toBeInTheDocument();
    expect(screen.getByText('Project Timeline')).toBeInTheDocument();
    expect(screen.getByText('Financial Commitment')).toBeInTheDocument();
    expect(screen.getByText('Additional Information')).toBeInTheDocument();
  });

  test('renders required form fields', () => {
    renderWithTheme(<ClientIntakeForm />);
    
    // Check for required fields
    expect(screen.getByLabelText('School Name *')).toBeInTheDocument();
    expect(screen.getByLabelText('Contact Person *')).toBeInTheDocument();
    expect(screen.getByLabelText('Email Address *')).toBeInTheDocument();
  });

  test('validates required fields on submit', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ClientIntakeForm />);
    
    const submitButton = screen.getByText('Submit Intake Form');
    
    // Try to submit without filling required fields
    await user.click(submitButton);
    
    // Check for validation errors
    await waitFor(() => {
      expect(screen.getByText('School name is required')).toBeInTheDocument();
      expect(screen.getByText('Contact person is required')).toBeInTheDocument();
      expect(screen.getByText('Email is required')).toBeInTheDocument();
    });
  });

  test('validates email format', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ClientIntakeForm />);
    
    const emailInput = screen.getByLabelText('Email Address *');
    
    // Enter invalid email
    await user.type(emailInput, 'invalid-email');
    
    // Try to submit
    const submitButton = screen.getByText('Submit Intake Form');
    await user.click(submitButton);
    
    // Check for email validation error
    await waitFor(() => {
      expect(screen.getByText('Invalid email address')).toBeInTheDocument();
    });
  });

  test('allows selecting multiple project types', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ClientIntakeForm />);
    
    // Check for project type checkboxes
    const websiteCheckbox = screen.getByLabelText('Website Development');
    const mobileCheckbox = screen.getByLabelText('Mobile Application');
    
    // Select multiple options
    await user.click(websiteCheckbox);
    await user.click(mobileCheckbox);
    
    // Verify both are selected
    expect(websiteCheckbox).toBeChecked();
    expect(mobileCheckbox).toBeChecked();
  });

  test('allows selecting timeline preference', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ClientIntakeForm />);
    
    // Click on timeline preference dropdown
    const timelineSelect = screen.getByLabelText('Timeline Preference *');
    await user.click(timelineSelect);
    
    // Select an option
    const asapOption = screen.getByText('ASAP');
    await user.click(asapOption);
    
    // Verify selection
    expect(timelineSelect).toHaveTextContent('ASAP');
  });

  test('handles form submission with valid data', async () => {
    const user = userEvent.setup();
    const mockSubmitClientIntake = jest.fn().mockResolvedValue({ id: '123' });
    
    // Mock the API client hook
    jest.doMock('../../hooks/useApiClient', () => ({
      useApiClient: () => ({
        submitClientIntake: mockSubmitClientIntake,
        generatePDF: jest.fn(),
        isLoading: false,
        error: null,
      }),
    }));
    
    renderWithTheme(<ClientIntakeForm />);
    
    // Fill in required fields
    await user.type(screen.getByLabelText('School Name *'), 'Test School');
    await user.type(screen.getByLabelText('Contact Person *'), 'John Doe');
    await user.type(screen.getByLabelText('Email Address *'), 'john@testschool.com');
    
    // Select project types
    await user.click(screen.getByLabelText('Website Development'));
    
    // Select project purposes
    await user.click(screen.getByLabelText('Improve Student Engagement'));
    
    // Select pilot features
    await user.click(screen.getByLabelText('User Authentication'));
    
    // Select timeline preference
    await user.click(screen.getByLabelText('Timeline Preference *'));
    await user.click(screen.getByText('ASAP'));
    
    // Submit form
    const submitButton = screen.getByText('Submit Intake Form');
    await user.click(submitButton);
    
    // Verify submission was called
    await waitFor(() => {
      expect(mockSubmitClientIntake).toHaveBeenCalled();
    });
  });

  test('displays loading state during submission', async () => {
    const user = userEvent.setup();
    
    // Mock loading state
    jest.doMock('../../hooks/useApiClient', () => ({
      useApiClient: () => ({
        submitClientIntake: jest.fn().mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000))),
        generatePDF: jest.fn(),
        isLoading: true,
        error: null,
      }),
    }));
    
    renderWithTheme(<ClientIntakeForm />);
    
    // Check for loading state
    expect(screen.getByText('Submitting...')).toBeInTheDocument();
    expect(screen.getByText('Submit Intake Form')).toBeDisabled();
  });

  test('displays error message when submission fails', async () => {
    const mockError = 'Submission failed';
    
    // Mock error state
    jest.doMock('../../hooks/useApiClient', () => ({
      useApiClient: () => ({
        submitClientIntake: jest.fn(),
        generatePDF: jest.fn(),
        isLoading: false,
        error: mockError,
      }),
    }));
    
    renderWithTheme(<ClientIntakeForm />);
    
    // Check for error message
    expect(screen.getByText(mockError)).toBeInTheDocument();
  });

  test('handles PDF generation', async () => {
    const user = userEvent.setup();
    const mockGeneratePDF = jest.fn().mockResolvedValue('http://example.com/pdf');
    
    // Mock PDF generation
    jest.doMock('../../hooks/useApiClient', () => ({
      useApiClient: () => ({
        submitClientIntake: jest.fn(),
        generatePDF: mockGeneratePDF,
        isLoading: false,
        error: null,
      }),
    }));
    
    // Mock window.open
    const mockOpen = jest.fn();
    Object.defineProperty(window, 'open', {
      value: mockOpen,
      writable: true,
    });
    
    renderWithTheme(<ClientIntakeForm />);
    
    // Click PDF preview button
    const pdfButton = screen.getByText('Preview PDF');
    await user.click(pdfButton);
    
    // Verify PDF generation was called
    await waitFor(() => {
      expect(mockGeneratePDF).toHaveBeenCalled();
    });
  });

  test('handles number inputs correctly', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ClientIntakeForm />);
    
    const studentsInput = screen.getByLabelText('Number of Students');
    const staffInput = screen.getByLabelText('Number of Staff');
    
    // Enter numbers
    await user.type(studentsInput, '500');
    await user.type(staffInput, '50');
    
    // Verify values
    expect(studentsInput).toHaveValue(500);
    expect(staffInput).toHaveValue(50);
  });

  test('handles toggle switch for content availability', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ClientIntakeForm />);
    
    const contentSwitch = screen.getByLabelText('Content is readily available');
    
    // Initially should be unchecked
    expect(contentSwitch).not.toBeChecked();
    
    // Click to toggle
    await user.click(contentSwitch);
    
    // Should now be checked
    expect(contentSwitch).toBeChecked();
  });

  test('handles textarea for additional notes', async () => {
    const user = userEvent.setup();
    renderWithTheme(<ClientIntakeForm />);
    
    const notesTextarea = screen.getByLabelText('Additional Notes');
    const testNotes = 'This is a test note for the project requirements.';
    
    // Type in textarea
    await user.type(notesTextarea, testNotes);
    
    // Verify content
    expect(notesTextarea).toHaveValue(testNotes);
  });
});
