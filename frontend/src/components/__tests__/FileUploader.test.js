import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock the hooks
import { useApiClient } from '../../hooks/useApiClient';
import { useOfflineStorage } from '../../hooks/useOfflineStorage';

import FileUploader from '../FileUploader';

// Mock the hooks
jest.mock('../../hooks/useApiClient');
jest.mock('../../hooks/useOfflineStorage');

describe('FileUploader', () => {
  const mockUploadFile = jest.fn();
  const mockDeleteFile = jest.fn();
  const mockDownloadFile = jest.fn();
  const mockAddFileToQueue = jest.fn();
  const mockGetFileQueue = jest.fn();
  const mockRemoveFileFromQueue = jest.fn();
  const mockUpdateFileQueueStatus = jest.fn();

  const defaultApiClient = {
    uploadFile: mockUploadFile,
    deleteFile: mockDeleteFile,
    downloadFile: mockDownloadFile,
    isLoading: false,
    error: null,
  };

  const defaultOfflineStorage = {
    isOnline: true,
    addFileToQueue: mockAddFileToQueue,
    getFileQueue: mockGetFileQueue,
    removeFileFromQueue: mockRemoveFileFromQueue,
    updateFileQueueStatus: mockUpdateFileQueueStatus,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useApiClient.mockReturnValue(defaultApiClient);
    useOfflineStorage.mockReturnValue(defaultOfflineStorage);
    mockGetFileQueue.mockReturnValue([]);
  });

  it('renders file upload interface', () => {
    render(<FileUploader projectId="test-project-id" />);
    
    expect(screen.getByText('File Upload')).toBeInTheDocument();
    expect(screen.getByText('Online')).toBeInTheDocument();
    expect(screen.getByText('Drag & drop files here')).toBeInTheDocument();
    expect(screen.getByText('or click to select files')).toBeInTheDocument();
  });

  it('shows offline status when not online', () => {
    useOfflineStorage.mockReturnValue({
      ...defaultOfflineStorage,
      isOnline: false,
    });

    render(<FileUploader projectId="test-project-id" />);
    
    expect(screen.getByText('Offline')).toBeInTheDocument();
    expect(screen.getByText('Files will be queued for upload when connection is restored')).toBeInTheDocument();
  });

  it('displays error message when API error occurs', () => {
    useApiClient.mockReturnValue({
      ...defaultApiClient,
      error: 'Upload failed',
    });

    render(<FileUploader projectId="test-project-id" />);
    
    expect(screen.getByText('Upload failed')).toBeInTheDocument();
  });

  it('handles file selection via input', async () => {
    const user = userEvent.setup();
    render(<FileUploader projectId="test-project-id" />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByRole('button', { name: /drag & drop files here/i }).parentElement.querySelector('input[type="file"]');
    
    await user.upload(input, file);
    
    expect(screen.getByText('Selected Files (1)')).toBeInTheDocument();
    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    expect(screen.getByText('12 B')).toBeInTheDocument(); // File size
  });

  it('validates file size and shows error for large files', async () => {
    const user = userEvent.setup();
    render(<FileUploader projectId="test-project-id" />);
    
    // Create a file larger than 10MB
    const largeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.pdf', { type: 'application/pdf' });
    const input = screen.getByRole('button', { name: /drag & drop files here/i }).parentElement.querySelector('input[type="file"]');
    
    await user.upload(input, largeFile);
    
    // Should not add large files to selection
    expect(screen.queryByText('Selected Files (1)')).not.toBeInTheDocument();
  });

  it('validates file type and shows error for unsupported types', async () => {
    const user = userEvent.setup();
    render(<FileUploader projectId="test-project-id" />);
    
    const unsupportedFile = new File(['test content'], 'test.exe', { type: 'application/x-msdownload' });
    const input = screen.getByRole('button', { name: /drag & drop files here/i }).parentElement.querySelector('input[type="file"]');
    
    await user.upload(input, unsupportedFile);
    
    // Should not add unsupported files to selection
    expect(screen.queryByText('Selected Files (1)')).not.toBeInTheDocument();
  });

  it('removes selected files when remove button is clicked', async () => {
    const user = userEvent.setup();
    render(<FileUploader projectId="test-project-id" />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByRole('button', { name: /drag & drop files here/i }).parentElement.querySelector('input[type="file"]');
    
    await user.upload(input, file);
    
    expect(screen.getByText('Selected Files (1)')).toBeInTheDocument();
    
    const removeButton = screen.getByRole('button', { name: /delete/i });
    await user.click(removeButton);
    
    expect(screen.queryByText('Selected Files (1)')).not.toBeInTheDocument();
  });

  it('uploads files when online', async () => {
    const user = userEvent.setup();
    mockUploadFile.mockResolvedValue({ id: 'uploaded-file-id', file_name: 'test.pdf' });
    
    render(<FileUploader projectId="test-project-id" />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByRole('button', { name: /drag & drop files here/i }).parentElement.querySelector('input[type="file"]');
    
    await user.upload(input, file);
    await user.click(screen.getByText('Upload Files'));
    
    await waitFor(() => {
      expect(mockUploadFile).toHaveBeenCalledWith(file, 'test-project-id', '');
    });
  });

  it('queues files when offline', async () => {
    const user = userEvent.setup();
    useOfflineStorage.mockReturnValue({
      ...defaultOfflineStorage,
      isOnline: false,
    });
    
    mockAddFileToQueue.mockResolvedValue(true);
    
    render(<FileUploader projectId="test-project-id" />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByRole('button', { name: /drag & drop files here/i }).parentElement.querySelector('input[type="file"]');
    
    await user.upload(input, file);
    await user.click(screen.getByText('Queue for Upload'));
    
    await waitFor(() => {
      expect(mockAddFileToQueue).toHaveBeenCalledWith(file, 'test-project-id', '');
    });
  });

  it('allows adding description to files', async () => {
    const user = userEvent.setup();
    render(<FileUploader projectId="test-project-id" />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByRole('button', { name: /drag & drop files here/i }).parentElement.querySelector('input[type="file"]');
    
    await user.upload(input, file);
    
    const descriptionInput = screen.getByLabelText(/description/i);
    await user.type(descriptionInput, 'Test description');
    
    expect(descriptionInput).toHaveValue('Test description');
  });

  it('shows upload queue dialog', async () => {
    const user = userEvent.setup();
    const mockQueueItems = [
      {
        id: 'queue-item-1',
        file: { name: 'queued.pdf', size: 1024 },
        status: 'pending',
        timestamp: new Date().toISOString(),
      },
    ];
    
    mockGetFileQueue.mockReturnValue(mockQueueItems);
    
    render(<FileUploader projectId="test-project-id" />);
    
    await user.click(screen.getByText('View Upload Queue'));
    
    expect(screen.getByText('Upload Queue')).toBeInTheDocument();
    expect(screen.getByText('queued.pdf')).toBeInTheDocument();
  });

  it('clears selected files when clear button is clicked', async () => {
    const user = userEvent.setup();
    render(<FileUploader projectId="test-project-id" />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByRole('button', { name: /drag & drop files here/i }).parentElement.querySelector('input[type="file"]');
    
    await user.upload(input, file);
    
    expect(screen.getByText('Selected Files (1)')).toBeInTheDocument();
    
    await user.click(screen.getByText('Clear Selection'));
    
    expect(screen.queryByText('Selected Files (1)')).not.toBeInTheDocument();
  });

  it('shows supported file formats', () => {
    render(<FileUploader projectId="test-project-id" />);
    
    expect(screen.getByText(/Supported formats: Images, PDF, Word, Excel, Text files/)).toBeInTheDocument();
    expect(screen.getByText(/max 10MB each/)).toBeInTheDocument();
  });

  it('handles drag and drop events', () => {
    render(<FileUploader projectId="test-project-id" />);
    
    const dropZone = screen.getByRole('button', { name: /drag & drop files here/i }).parentElement;
    
    // Test drag enter
    fireEvent.dragEnter(dropZone);
    expect(screen.getByText('Drop files here')).toBeInTheDocument();
    
    // Test drag leave
    fireEvent.dragLeave(dropZone);
    expect(screen.getByText('Drag & drop files here')).toBeInTheDocument();
  });

  it('calls onFileUploaded callback when file is uploaded', async () => {
    const user = userEvent.setup();
    const mockOnFileUploaded = jest.fn();
    mockUploadFile.mockResolvedValue({ id: 'uploaded-file-id', file_name: 'test.pdf' });
    
    render(
      <FileUploader 
        projectId="test-project-id" 
        onFileUploaded={mockOnFileUploaded}
      />
    );
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByRole('button', { name: /drag & drop files here/i }).parentElement.querySelector('input[type="file"]');
    
    await user.upload(input, file);
    await user.click(screen.getByText('Upload Files'));
    
    await waitFor(() => {
      expect(mockOnFileUploaded).toHaveBeenCalledWith({ id: 'uploaded-file-id', file_name: 'test.pdf' });
    });
  });
});
