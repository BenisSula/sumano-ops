import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock the child components
import FileUploader from '../FileUploader';
import FileList from '../FileList';

import FileManager from '../FileManager';

// Mock the child components
jest.mock('../FileUploader');
jest.mock('../FileList');

describe('FileManager', () => {
  const mockOnFileUploaded = jest.fn();
  const mockOnFileDeleted = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock FileUploader component
    FileUploader.mockImplementation(({ projectId, onFileUploaded, onFileDeleted }) => (
      <div data-testid="file-uploader">
        <div>FileUploader for project: {projectId}</div>
        <button 
          onClick={() => onFileUploaded && onFileUploaded({ id: 'test-file', file_name: 'test.pdf' })}
        >
          Mock Upload Success
        </button>
        <button 
          onClick={() => onFileDeleted && onFileDeleted('test-file-id')}
        >
          Mock Delete Success
        </button>
      </div>
    ));

    // Mock FileList component
    FileList.mockImplementation(({ projectId, refreshTrigger }) => (
      <div data-testid="file-list">
        <div>FileList for project: {projectId}</div>
        <div>Refresh trigger: {refreshTrigger}</div>
      </div>
    ));
  });

  it('renders file manager interface', () => {
    render(<FileManager projectId="test-project-id" projectName="Test Project" />);
    
    expect(screen.getByText('File Manager')).toBeInTheDocument();
    expect(screen.getByText('Project: Test Project')).toBeInTheDocument();
    expect(screen.getByText('Upload Files')).toBeInTheDocument();
    expect(screen.getByText('View Files')).toBeInTheDocument();
  });

  it('shows warning when no project ID is provided', () => {
    render(<FileManager />);
    
    expect(screen.getByText('Please select a project to manage files.')).toBeInTheDocument();
  });

  it('shows only project name when provided without project ID', () => {
    render(<FileManager projectName="Test Project" />);
    
    expect(screen.getByText('Please select a project to manage files.')).toBeInTheDocument();
  });

  it('switches between upload and view tabs', async () => {
    const user = userEvent.setup();
    render(<FileManager projectId="test-project-id" />);
    
    // Default tab is Upload Files
    expect(screen.getByTestId('file-uploader')).toBeInTheDocument();
    expect(screen.queryByTestId('file-list')).not.toBeInTheDocument();
    
    // Switch to View Files tab
    await user.click(screen.getByText('View Files'));
    
    expect(screen.getByTestId('file-list')).toBeInTheDocument();
    expect(screen.queryByTestId('file-uploader')).not.toBeInTheDocument();
  });

  it('passes correct props to FileUploader', () => {
    render(<FileManager projectId="test-project-id" />);
    
    expect(FileUploader).toHaveBeenCalledWith(
      expect.objectContaining({
        projectId: 'test-project-id',
        onFileUploaded: expect.any(Function),
        onFileDeleted: expect.any(Function),
      }),
      expect.any(Object)
    );
  });

  it('passes correct props to FileList', () => {
    render(<FileManager projectId="test-project-id" />);
    
    expect(FileList).toHaveBeenCalledWith(
      expect.objectContaining({
        projectId: 'test-project-id',
        refreshTrigger: 0,
      }),
      expect.any(Object)
    );
  });

  it('shows success message when file is uploaded', async () => {
    const user = userEvent.setup();
    render(<FileManager projectId="test-project-id" />);
    
    // Trigger file upload success
    const uploadButton = screen.getByText('Mock Upload Success');
    await user.click(uploadButton);
    
    expect(screen.getByText('File "test.pdf" uploaded successfully!')).toBeInTheDocument();
  });

  it('auto-hides success message after 5 seconds', async () => {
    jest.useFakeTimers();
    const user = userEvent.setup();
    
    render(<FileManager projectId="test-project-id" />);
    
    // Trigger file upload success
    const uploadButton = screen.getByText('Mock Upload Success');
    await user.click(uploadButton);
    
    expect(screen.getByText('File "test.pdf" uploaded successfully!')).toBeInTheDocument();
    
    // Fast-forward time by 5 seconds
    jest.advanceTimersByTime(5000);
    
    await waitFor(() => {
      expect(screen.queryByText('File "test.pdf" uploaded successfully!')).not.toBeInTheDocument();
    });
    
    jest.useRealTimers();
  });

  it('allows manual dismissal of success message', async () => {
    const user = userEvent.setup();
    render(<FileManager projectId="test-project-id" />);
    
    // Trigger file upload success
    const uploadButton = screen.getByText('Mock Upload Success');
    await user.click(uploadButton);
    
    expect(screen.getByText('File "test.pdf" uploaded successfully!')).toBeInTheDocument();
    
    // Click close button on alert
    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);
    
    expect(screen.queryByText('File "test.pdf" uploaded successfully!')).not.toBeInTheDocument();
  });

  it('increments refresh trigger when file is uploaded', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<FileManager projectId="test-project-id" />);
    
    // Switch to View Files tab to see the refresh trigger
    await user.click(screen.getByText('View Files'));
    
    expect(screen.getByText('Refresh trigger: 0')).toBeInTheDocument();
    
    // Switch back to Upload Files tab
    await user.click(screen.getByText('Upload Files'));
    
    // Trigger file upload success
    const uploadButton = screen.getByText('Mock Upload Success');
    await user.click(uploadButton);
    
    // Switch back to View Files tab
    await user.click(screen.getByText('View Files'));
    
    expect(screen.getByText('Refresh trigger: 1')).toBeInTheDocument();
  });

  it('increments refresh trigger when file is deleted', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<FileManager projectId="test-project-id" />);
    
    // Switch to View Files tab to see the refresh trigger
    await user.click(screen.getByText('View Files'));
    
    expect(screen.getByText('Refresh trigger: 0')).toBeInTheDocument();
    
    // Switch back to Upload Files tab
    await user.click(screen.getByText('Upload Files'));
    
    // Trigger file delete success
    const deleteButton = screen.getByText('Mock Delete Success');
    await user.click(deleteButton);
    
    // Switch back to View Files tab
    await user.click(screen.getByText('View Files'));
    
    expect(screen.getByText('Refresh trigger: 1')).toBeInTheDocument();
  });

  it('maintains tab state when switching between tabs', async () => {
    const user = userEvent.setup();
    render(<FileManager projectId="test-project-id" />);
    
    // Switch to View Files tab
    await user.click(screen.getByText('View Files'));
    expect(screen.getByTestId('file-list')).toBeInTheDocument();
    
    // Switch back to Upload Files tab
    await user.click(screen.getByText('Upload Files'));
    expect(screen.getByTestId('file-uploader')).toBeInTheDocument();
    
    // Switch to View Files tab again
    await user.click(screen.getByText('View Files'));
    expect(screen.getByTestId('file-list')).toBeInTheDocument();
  });

  it('shows correct aria labels for tabs', () => {
    render(<FileManager projectId="test-project-id" />);
    
    const tabList = screen.getByRole('tablist');
    expect(tabList).toBeInTheDocument();
    
    const uploadTab = screen.getByRole('tab', { name: /upload files/i });
    const viewTab = screen.getByRole('tab', { name: /view files/i });
    
    expect(uploadTab).toBeInTheDocument();
    expect(viewTab).toBeInTheDocument();
  });

  it('handles multiple file uploads and updates refresh trigger', async () => {
    const user = userEvent.setup();
    render(<FileManager projectId="test-project-id" />);
    
    // Switch to View Files tab to see the refresh trigger
    await user.click(screen.getByText('View Files'));
    expect(screen.getByText('Refresh trigger: 0')).toBeInTheDocument();
    
    // Switch back to Upload Files tab
    await user.click(screen.getByText('Upload Files'));
    
    // Trigger multiple file uploads
    const uploadButton = screen.getByText('Mock Upload Success');
    await user.click(uploadButton);
    await user.click(uploadButton);
    
    // Switch back to View Files tab
    await user.click(screen.getByText('View Files'));
    
    expect(screen.getByText('Refresh trigger: 2')).toBeInTheDocument();
  });

  it('renders without project name when not provided', () => {
    render(<FileManager projectId="test-project-id" />);
    
    expect(screen.getByText('File Manager')).toBeInTheDocument();
    expect(screen.queryByText(/Project:/)).not.toBeInTheDocument();
  });
});
