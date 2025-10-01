import React, { useState, useCallback, useRef } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Button, 
  TextField, 
  Alert, 
  CircularProgress,
  LinearProgress,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Stack
} from '@mui/material';
import { 
  CloudUpload, 
  Delete, 
  CheckCircle, 
  Error, 
  Pending, 
  FileDownload,
  Queue,
  Sync,
  Cancel
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

// Custom hooks
import { useApiClient } from '../hooks/useApiClient';
import { useOfflineStorage } from '../hooks/useOfflineStorage';

// Styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  margin: theme.spacing(2),
  maxWidth: 800,
  marginLeft: 'auto',
  marginRight: 'auto',
}));

const DropZone = styled(Box)(({ theme, isDragActive, isDragReject }) => ({
  border: `2px dashed ${isDragReject ? theme.palette.error.main : isDragActive ? theme.palette.primary.main : theme.palette.grey[400]}`,
  borderRadius: theme.shape.borderRadius,
  padding: theme.spacing(4),
  textAlign: 'center',
  cursor: 'pointer',
  transition: theme.transitions.create(['border-color', 'background-color']),
  backgroundColor: isDragActive ? theme.palette.primary.light + '20' : 'transparent',
  '&:hover': {
    borderColor: theme.palette.primary.main,
    backgroundColor: theme.palette.primary.light + '10',
  },
}));

const FileItem = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: theme.spacing(1.5),
  margin: theme.spacing(0.5, 0),
  border: `1px solid ${theme.palette.grey[300]}`,
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.grey[50],
}));

const FileUploader = ({ projectId, onFileUploaded, onFileDeleted }) => {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [description, setDescription] = useState('');
  const [isDragActive, setIsDragActive] = useState(false);
  const [isDragReject, setIsDragReject] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [showQueueDialog, setShowQueueDialog] = useState(false);
  const fileInputRef = useRef(null);

  const { uploadFile, deleteFile, downloadFile, isLoading, error } = useApiClient();
  const { 
    isOnline, 
    addFileToQueue, 
    getFileQueue, 
    removeFileFromQueue, 
    updateFileQueueStatus 
  } = useOfflineStorage();

  // File validation
  const validateFile = (file) => {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = [
      'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
      'application/pdf',
      'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/plain'
    ];

    if (file.size > maxSize) {
      throw new Error(`File "${file.name}" is too large. Maximum size is 10MB.`);
    }

    if (!allowedTypes.includes(file.type)) {
      throw new Error(`File type "${file.type}" is not allowed.`);
    }

    return true;
  };

  // Handle file selection
  const handleFileSelect = useCallback((files) => {
    const fileArray = Array.from(files);
    const validFiles = [];
    const errors = [];

    fileArray.forEach(file => {
      try {
        validateFile(file);
        validFiles.push(file);
      } catch (error) {
        errors.push(error.message);
      }
    });

    if (errors.length > 0) {
      console.error('File validation errors:', errors);
    }

    setSelectedFiles(prev => [...prev, ...validFiles]);
  }, []);

  // Handle drag and drop
  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
    setIsDragReject(false);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    setIsDragReject(false);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    setIsDragReject(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files);
    }
  }, [handleFileSelect]);

  // Handle file input change
  const handleFileInputChange = useCallback((e) => {
    const files = e.target.files;
    if (files.length > 0) {
      handleFileSelect(files);
    }
  }, [handleFileSelect]);

  // Remove file from selection
  const removeFile = useCallback((index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  // Upload files
  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return;

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const fileId = `${file.name}_${file.size}_${i}`;

      try {
        setUploadProgress(prev => ({ ...prev, [fileId]: 0 }));

        if (isOnline) {
          // Upload directly
          const result = await uploadFile(file, projectId, description);
          setUploadProgress(prev => ({ ...prev, [fileId]: 100 }));
          
          if (onFileUploaded) {
            onFileUploaded(result);
          }
        } else {
          // Add to offline queue
          await addFileToQueue(file, projectId, description);
          setUploadProgress(prev => ({ ...prev, [fileId]: 100 }));
        }

        // Remove from selected files after successful upload/queue
        setSelectedFiles(prev => prev.filter((_, index) => index !== i));
        
      } catch (error) {
        console.error('Upload error:', error);
        setUploadProgress(prev => ({ ...prev, [fileId]: -1 })); // -1 indicates error
      }
    }

    setDescription('');
  }, [selectedFiles, projectId, description, isOnline, uploadFile, addFileToQueue, onFileUploaded]);

  // Sync offline queue
  const syncOfflineQueue = useCallback(async () => {
    const queueItems = getFileQueue();
    
    for (const item of queueItems) {
      try {
        updateFileQueueStatus(item.id, 'uploading');
        
        // Convert base64 back to file
        const response = await fetch(item.file.content);
        const blob = await response.blob();
        const file = new File([blob], item.file.name, { 
          type: item.file.type,
          lastModified: item.file.lastModified 
        });

        await uploadFile(file, item.projectId, item.description);
        updateFileQueueStatus(item.id, 'completed');
        removeFileFromQueue(item.id);
        
      } catch (error) {
        console.error('Queue sync error:', error);
        updateFileQueueStatus(item.id, 'failed', error.message);
      }
    }
  }, [getFileQueue, updateFileQueueStatus, uploadFile, removeFileFromQueue]);

  // Handle download
  const handleDownload = useCallback(async (attachmentId, fileName) => {
    try {
      const blob = await downloadFile(attachmentId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download error:', error);
    }
  }, [downloadFile]);

  // Handle delete
  const handleDelete = useCallback(async (attachmentId) => {
    try {
      await deleteFile(attachmentId);
      if (onFileDeleted) {
        onFileDeleted(attachmentId);
      }
    } catch (error) {
      console.error('Delete error:', error);
    }
  }, [deleteFile, onFileDeleted]);

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Get file icon based on type
  const getFileIcon = (type) => {
    if (type.startsWith('image/')) return '🖼️';
    if (type === 'application/pdf') return '📄';
    if (type.includes('word')) return '📝';
    if (type.includes('excel') || type.includes('spreadsheet')) return '📊';
    return '📁';
  };

  return (
    <StyledPaper elevation={2}>
      <Typography variant="h5" gutterBottom>
        File Upload
      </Typography>

      {/* Connection Status */}
      <Box mb={2}>
        <Chip
          icon={isOnline ? <CheckCircle /> : <Error />}
          label={isOnline ? 'Online' : 'Offline'}
          color={isOnline ? 'success' : 'error'}
          size="small"
        />
        {!isOnline && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
            Files will be queued for upload when connection is restored
          </Typography>
        )}
      </Box>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Drop Zone */}
      <DropZone
        isDragActive={isDragActive}
        isDragReject={isDragReject}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <CloudUpload sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          or click to select files
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          Supported formats: Images, PDF, Word, Excel, Text files (max 10MB each)
        </Typography>
      </DropZone>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileInputChange}
        style={{ display: 'none' }}
      />

      {/* Description Field */}
      {selectedFiles.length > 0 && (
        <Box mt={2}>
          <TextField
            fullWidth
            label="Description (optional)"
            multiline
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Add a description for these files..."
          />
        </Box>
      )}

      {/* Selected Files */}
      {selectedFiles.length > 0 && (
        <Box mt={2}>
          <Typography variant="h6" gutterBottom>
            Selected Files ({selectedFiles.length})
          </Typography>
          {selectedFiles.map((file, index) => (
            <FileItem key={`${file.name}_${index}`}>
              <Box display="flex" alignItems="center" flex={1}>
                <Typography sx={{ mr: 1 }}>{getFileIcon(file.type)}</Typography>
                <Box flex={1}>
                  <Typography variant="body2" noWrap>
                    {file.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatFileSize(file.size)}
                  </Typography>
                </Box>
              </Box>
              <Box display="flex" alignItems="center">
                {uploadProgress[`${file.name}_${file.size}_${index}`] === 0 && (
                  <CircularProgress size={20} />
                )}
                {uploadProgress[`${file.name}_${file.size}_${index}`] === 100 && (
                  <CheckCircle color="success" />
                )}
                {uploadProgress[`${file.name}_${file.size}_${index}`] === -1 && (
                  <Error color="error" />
                )}
                <IconButton
                  size="small"
                  onClick={() => removeFile(index)}
                  disabled={uploadProgress[`${file.name}_${file.size}_${index}`] === 0}
                >
                  <Delete />
                </IconButton>
              </Box>
            </FileItem>
          ))}
        </Box>
      )}

      {/* Upload Button */}
      {selectedFiles.length > 0 && (
        <Box mt={2} display="flex" gap={2}>
          <Button
            variant="contained"
            onClick={handleUpload}
            disabled={isLoading}
            startIcon={isLoading ? <CircularProgress size={20} /> : <CloudUpload />}
          >
            {isOnline ? 'Upload Files' : 'Queue for Upload'}
          </Button>
          <Button
            variant="outlined"
            onClick={() => setSelectedFiles([])}
            disabled={isLoading}
          >
            Clear Selection
          </Button>
        </Box>
      )}

      {/* Queue Management */}
      <Box mt={3} display="flex" gap={2} alignItems="center">
        <Button
          variant="outlined"
          startIcon={<Queue />}
          onClick={() => setShowQueueDialog(true)}
        >
          View Upload Queue
        </Button>
        {!isOnline && getFileQueue().length > 0 && (
          <Button
            variant="outlined"
            startIcon={<Sync />}
            onClick={syncOfflineQueue}
            disabled={isLoading}
          >
            Sync When Online
          </Button>
        )}
      </Box>

      {/* Queue Dialog */}
      <Dialog
        open={showQueueDialog}
        onClose={() => setShowQueueDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Upload Queue</DialogTitle>
        <DialogContent>
          {getFileQueue().length === 0 ? (
            <Typography color="text.secondary">
              No files in queue
            </Typography>
          ) : (
            <List>
              {getFileQueue().map((item, index) => (
                <React.Fragment key={item.id}>
                  <ListItem>
                    <ListItemText
                      primary={item.file.name}
                      secondary={
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Typography variant="caption">
                            {formatFileSize(item.file.size)}
                          </Typography>
                          <Chip
                            icon={
                              item.status === 'pending' ? <Pending /> :
                              item.status === 'uploading' ? <Sync /> :
                              item.status === 'completed' ? <CheckCircle /> :
                              <Error />
                            }
                            label={item.status}
                            size="small"
                            color={
                              item.status === 'completed' ? 'success' :
                              item.status === 'failed' ? 'error' :
                              'default'
                            }
                          />
                          {item.status === 'failed' && item.error && (
                            <Typography variant="caption" color="error">
                              {item.error}
                            </Typography>
                          )}
                        </Stack>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Tooltip title="Remove from queue">
                        <IconButton
                          edge="end"
                          onClick={() => removeFileFromQueue(item.id)}
                        >
                          <Cancel />
                        </IconButton>
                      </Tooltip>
                    </ListItemSecondaryAction>
                  </ListItem>
                  {index < getFileQueue().length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowQueueDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </StyledPaper>
  );
};

export default FileUploader;
