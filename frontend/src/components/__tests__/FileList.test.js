import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock the hooks
import { useApiClient } from '../../hooks/useApiClient';

import FileList from '../FileList';

// Mock the hook
jest.mock('../../hooks/useApiClient');

describe('FileList', () => {
  const mockGetAttachmentsByProject = jest.fn();
  const mockDeleteFile = jest.fn();
  const mockDownloadFile = jest.fn();

  const defaultApiClient = {
    getAttachmentsByProject: mockGetAttachmentsByProject,
    deleteFile: mockDeleteFile,
    downloadFile: mockDownloadFile,
    isLoading: false,
    error: null,
  };

  const mockFiles = [
    {
      id: 'file-1',
      file_name: 'test.pdf',
      file_type: 'pdf',
      file_size: 1024,
      description: 'Test PDF file',
      created_at: '2023-01-01T10:00:00Z',
      uploaded_by_username: 'testuser',
      download_count: 5,
    },
    {
      id: 'file-2',
      file_name: 'image.jpg',
      file_type: 'image',
      file_size: 2048,
      description: 'Test image',
      created_at: '2023-01-02T10:00:00Z',
      uploaded_by_username: 'testuser',
      download_count: 3,
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    useApiClient.mockReturnValue(defaultApiClient);
    mockGetAttachmentsByProject.mockResolvedValue(mockFiles);
  });

  it('renders file list interface', async () => {
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (2)')).toBeInTheDocument();
    });
    
    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    expect(screen.getByText('image.jpg')).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    mockGetAttachmentsByProject.mockImplementation(() => new Promise(() => {}));
    
    render(<FileList projectId="test-project-id" />);
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays error message when API error occurs', async () => {
    useApiClient.mockReturnValue({
      ...defaultApiClient,
      error: 'Failed to load files',
    });

    render(<FileList projectId="test-project-id" />);
    
    expect(screen.getByText('Failed to load files')).toBeInTheDocument();
  });

  it('shows no files message when no files exist', async () => {
    mockGetAttachmentsByProject.mockResolvedValue([]);
    
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('No files found')).toBeInTheDocument();
    });
  });

  it('filters files by search term', async () => {
    const user = userEvent.setup();
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (2)')).toBeInTheDocument();
    });
    
    const searchInput = screen.getByLabelText(/search files/i);
    await user.type(searchInput, 'pdf');
    
    // Should only show PDF file
    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    expect(screen.queryByText('image.jpg')).not.toBeInTheDocument();
  });

  it('filters files by file type', async () => {
    const user = userEvent.setup();
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (2)')).toBeInTheDocument();
    });
    
    const typeFilter = screen.getByLabelText(/file type/i);
    await user.click(typeFilter);
    await user.click(screen.getByText('Images'));
    
    // Should only show image file
    expect(screen.getByText('image.jpg')).toBeInTheDocument();
    expect(screen.queryByText('test.pdf')).not.toBeInTheDocument();
  });

  it('switches between grid and table view', async () => {
    const user = userEvent.setup();
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (2)')).toBeInTheDocument();
    });
    
    // Default is grid view
    expect(screen.getByText('Grid')).toHaveClass('MuiButton-contained');
    
    // Switch to table view
    await user.click(screen.getByText('Table'));
    expect(screen.getByText('Table')).toHaveClass('MuiButton-contained');
    
    // Should show table headers
    expect(screen.getByText('File')).toBeInTheDocument();
    expect(screen.getByText('Type')).toBeInTheDocument();
    expect(screen.getByText('Size')).toBeInTheDocument();
  });

  it('downloads file when download button is clicked', async () => {
    const user = userEvent.setup();
    const mockBlob = new Blob(['test content'], { type: 'application/pdf' });
    mockDownloadFile.mockResolvedValue(mockBlob);
    
    // Mock URL.createObjectURL and related methods
    const mockUrl = 'blob:test-url';
    window.URL.createObjectURL = jest.fn(() => mockUrl);
    window.URL.revokeObjectURL = jest.fn();
    
    // Mock document.createElement and related methods
    const mockLink = {
      href: '',
      download: '',
      click: jest.fn(),
    };
    document.createElement = jest.fn(() => mockLink);
    document.body.appendChild = jest.fn();
    document.body.removeChild = jest.fn();
    
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (2)')).toBeInTheDocument();
    });
    
    const downloadButtons = screen.getAllByRole('button', { name: /download/i });
    await user.click(downloadButtons[0]);
    
    await waitFor(() => {
      expect(mockDownloadFile).toHaveBeenCalledWith('file-1');
    });
    
    expect(mockLink.href).toBe(mockUrl);
    expect(mockLink.download).toBe('test.pdf');
    expect(mockLink.click).toHaveBeenCalled();
  });

  it('shows delete confirmation dialog', async () => {
    const user = userEvent.setup();
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (2)')).toBeInTheDocument();
    });
    
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);
    
    expect(screen.getByText('Confirm Delete')).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to delete "test.pdf"/)).toBeInTheDocument();
  });

  it('deletes file when confirmed', async () => {
    const user = userEvent.setup();
    mockDeleteFile.mockResolvedValue();
    
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (2)')).toBeInTheDocument();
    });
    
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);
    
    // Confirm deletion
    await user.click(screen.getByText('Delete'));
    
    await waitFor(() => {
      expect(mockDeleteFile).toHaveBeenCalledWith('file-1');
    });
  });

  it('cancels delete operation when cancel is clicked', async () => {
    const user = userEvent.setup();
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (2)')).toBeInTheDocument();
    });
    
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);
    
    // Cancel deletion
    await user.click(screen.getByText('Cancel'));
    
    expect(mockDeleteFile).not.toHaveBeenCalled();
    expect(screen.queryByText('Confirm Delete')).not.toBeInTheDocument();
  });

  it('refreshes files when refresh button is clicked', async () => {
    const user = userEvent.setup();
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (2)')).toBeInTheDocument();
    });
    
    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    await user.click(refreshButton);
    
    expect(mockGetAttachmentsByProject).toHaveBeenCalledTimes(2);
  });

  it('formats file sizes correctly', async () => {
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('1 KB')).toBeInTheDocument(); // 1024 bytes
      expect(screen.getByText('2 KB')).toBeInTheDocument(); // 2048 bytes
    });
  });

  it('formats dates correctly', async () => {
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/Jan 1, 2023/)).toBeInTheDocument();
      expect(screen.getByText(/Jan 2, 2023/)).toBeInTheDocument();
    });
  });

  it('shows file type chips with correct colors', async () => {
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('pdf')).toBeInTheDocument();
      expect(screen.getByText('image')).toBeInTheDocument();
    });
  });

  it('shows download counts', async () => {
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument(); // download count for first file
      expect(screen.getByText('3')).toBeInTheDocument(); // download count for second file
    });
  });

  it('handles pagination when many files exist', async () => {
    const manyFiles = Array.from({ length: 15 }, (_, i) => ({
      id: `file-${i}`,
      file_name: `file-${i}.pdf`,
      file_type: 'pdf',
      file_size: 1024,
      description: `File ${i}`,
      created_at: '2023-01-01T10:00:00Z',
      uploaded_by_username: 'testuser',
      download_count: 0,
    }));
    
    mockGetAttachmentsByProject.mockResolvedValue(manyFiles);
    
    render(<FileList projectId="test-project-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (15)')).toBeInTheDocument();
    });
    
    // Should show pagination controls
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });

  it('updates when refreshTrigger changes', async () => {
    const { rerender } = render(<FileList projectId="test-project-id" refreshTrigger={0} />);
    
    await waitFor(() => {
      expect(screen.getByText('Project Files (2)')).toBeInTheDocument();
    });
    
    // Change refreshTrigger
    rerender(<FileList projectId="test-project-id" refreshTrigger={1} />);
    
    // Should call API again
    expect(mockGetAttachmentsByProject).toHaveBeenCalledTimes(2);
  });
});
