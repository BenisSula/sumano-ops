import React, { useState, useEffect, useCallback } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Button, 
  IconButton, 
  Alert, 
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Pagination,
  Stack,
  Grid,
  Card,
  CardContent,
  CardActions,
  Divider
} from '@mui/material';
import { 
  Delete, 
  Download, 
  Visibility, 
  Edit, 
  Search,
  FilterList,
  Refresh,
  FileDownload,
  Image,
  Description,
  PictureAsPdf,
  TableChart,
  InsertDriveFile,
  MoreVert
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

// Custom hooks
import { useApiClient } from '../hooks/useApiClient';

// Styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  margin: theme.spacing(2),
  maxWidth: 1200,
  marginLeft: 'auto',
  marginRight: 'auto',
}));

const FileCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  transition: theme.transitions.create(['transform', 'box-shadow']),
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: theme.shadows[4],
  },
}));

const FileList = ({ projectId, refreshTrigger }) => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [fileTypeFilter, setFileTypeFilter] = useState('all');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'table'
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);

  const { 
    getAttachmentsByProject, 
    deleteFile, 
    downloadFile, 
    isLoading: apiLoading, 
    error: apiError 
  } = useApiClient();

  // Load files
  const loadFiles = useCallback(async () => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await getAttachmentsByProject(projectId);
      setFiles(response.results || response);
      setTotalPages(Math.ceil((response.count || response.length) / 12));
    } catch (err) {
      setError(err.message || 'Failed to load files');
    } finally {
      setLoading(false);
    }
  }, [projectId, getAttachmentsByProject]);

  // Load files when projectId changes or refresh is triggered
  useEffect(() => {
    loadFiles();
  }, [loadFiles, refreshTrigger]);

  // Filter files based on search and type
  const filteredFiles = files.filter(file => {
    const matchesSearch = file.file_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         file.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = fileTypeFilter === 'all' || file.file_type === fileTypeFilter;
    return matchesSearch && matchesType;
  });

  // Paginate files
  const itemsPerPage = 12;
  const startIndex = (page - 1) * itemsPerPage;
  const paginatedFiles = filteredFiles.slice(startIndex, startIndex + itemsPerPage);
  const paginatedTotalPages = Math.ceil(filteredFiles.length / itemsPerPage);

  // Handle download
  const handleDownload = useCallback(async (file) => {
    try {
      const blob = await downloadFile(file.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = file.file_name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setError(error.message || 'Download failed');
    }
  }, [downloadFile]);

  // Handle delete
  const handleDeleteClick = useCallback((file) => {
    setFileToDelete(file);
    setShowDeleteDialog(true);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!fileToDelete) return;

    try {
      await deleteFile(fileToDelete.id);
      setFiles(prev => prev.filter(f => f.id !== fileToDelete.id));
      setShowDeleteDialog(false);
      setFileToDelete(null);
    } catch (error) {
      setError(error.message || 'Delete failed');
    }
  }, [fileToDelete, deleteFile]);

  // Get file icon
  const getFileIcon = (fileType, fileName) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    
    if (fileType === 'image' || ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(extension)) {
      return <Image color="primary" />;
    } else if (fileType === 'pdf' || extension === 'pdf') {
      return <PictureAsPdf color="error" />;
    } else if (fileType === 'document' || ['doc', 'docx', 'txt', 'rtf'].includes(extension)) {
      return <Description color="info" />;
    } else if (fileType === 'spreadsheet' || ['xls', 'xlsx', 'csv'].includes(extension)) {
      return <TableChart color="success" />;
    } else {
      return <InsertDriveFile color="action" />;
    }
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Format date
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Get file type color
  const getFileTypeColor = (fileType) => {
    const colors = {
      image: 'primary',
      pdf: 'error',
      document: 'info',
      spreadsheet: 'success',
      archive: 'warning',
      other: 'default'
    };
    return colors[fileType] || 'default';
  };

  if (loading) {
    return (
      <StyledPaper elevation={2}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
          <CircularProgress />
        </Box>
      </StyledPaper>
    );
  }

  return (
    <StyledPaper elevation={2}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">
          Project Files ({filteredFiles.length})
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={loadFiles}
            disabled={apiLoading}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* Error Display */}
      {(error || apiError) && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || apiError}
        </Alert>
      )}

      {/* Filters */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Search files"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
            }}
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <TextField
            fullWidth
            select
            label="File Type"
            value={fileTypeFilter}
            onChange={(e) => setFileTypeFilter(e.target.value)}
            InputProps={{
              startAdornment: <FilterList sx={{ mr: 1, color: 'text.secondary' }} />
            }}
          >
            <MenuItem value="all">All Types</MenuItem>
            <MenuItem value="image">Images</MenuItem>
            <MenuItem value="pdf">PDFs</MenuItem>
            <MenuItem value="document">Documents</MenuItem>
            <MenuItem value="spreadsheet">Spreadsheets</MenuItem>
            <MenuItem value="archive">Archives</MenuItem>
            <MenuItem value="other">Other</MenuItem>
          </TextField>
        </Grid>
        <Grid item xs={12} md={3}>
          <Stack direction="row" spacing={1}>
            <Button
              variant={viewMode === 'grid' ? 'contained' : 'outlined'}
              onClick={() => setViewMode('grid')}
            >
              Grid
            </Button>
            <Button
              variant={viewMode === 'table' ? 'contained' : 'outlined'}
              onClick={() => setViewMode('table')}
            >
              Table
            </Button>
          </Stack>
        </Grid>
      </Grid>

      {/* File List */}
      {filteredFiles.length === 0 ? (
        <Box textAlign="center" py={4}>
          <Typography variant="h6" color="text.secondary">
            No files found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {searchTerm || fileTypeFilter !== 'all' 
              ? 'Try adjusting your search or filters'
              : 'Upload some files to get started'
            }
          </Typography>
        </Box>
      ) : viewMode === 'grid' ? (
        <>
          <Grid container spacing={2}>
            {paginatedFiles.map((file) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={file.id}>
                <FileCard>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box display="flex" alignItems="center" mb={1}>
                      {getFileIcon(file.file_type, file.file_name)}
                      <Typography variant="h6" noWrap sx={{ ml: 1, flex: 1 }}>
                        {file.file_name}
                      </Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {formatFileSize(file.file_size)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {formatDate(file.created_at)}
                    </Typography>
                    {file.description && (
                      <Typography variant="body2" sx={{ mt: 1 }} noWrap>
                        {file.description}
                      </Typography>
                    )}
                    <Box mt={1}>
                      <Chip
                        label={file.file_type}
                        size="small"
                        color={getFileTypeColor(file.file_type)}
                      />
                    </Box>
                  </CardContent>
                  <CardActions>
                    <Tooltip title="Download">
                      <IconButton
                        size="small"
                        onClick={() => handleDownload(file)}
                        disabled={apiLoading}
                      >
                        <Download />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteClick(file)}
                        disabled={apiLoading}
                        color="error"
                      >
                        <Delete />
                      </IconButton>
                    </Tooltip>
                  </CardActions>
                </FileCard>
              </Grid>
            ))}
          </Grid>
          {paginatedTotalPages > 1 && (
            <Box display="flex" justifyContent="center" mt={3}>
              <Pagination
                count={paginatedTotalPages}
                page={page}
                onChange={(e, value) => setPage(value)}
                color="primary"
              />
            </Box>
          )}
        </>
      ) : (
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>File</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Uploaded</TableCell>
                <TableCell>Uploaded By</TableCell>
                <TableCell>Downloads</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedFiles.map((file) => (
                <TableRow key={file.id} hover>
                  <TableCell>
                    <Box display="flex" alignItems="center">
                      {getFileIcon(file.file_type, file.file_name)}
                      <Box ml={1}>
                        <Typography variant="body2" noWrap>
                          {file.file_name}
                        </Typography>
                        {file.description && (
                          <Typography variant="caption" color="text.secondary" noWrap>
                            {file.description}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={file.file_type}
                      size="small"
                      color={getFileTypeColor(file.file_type)}
                    />
                  </TableCell>
                  <TableCell>{formatFileSize(file.file_size)}</TableCell>
                  <TableCell>{formatDate(file.created_at)}</TableCell>
                  <TableCell>{file.uploaded_by_username}</TableCell>
                  <TableCell>{file.download_count || 0}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Download">
                      <IconButton
                        size="small"
                        onClick={() => handleDownload(file)}
                        disabled={apiLoading}
                      >
                        <Download />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteClick(file)}
                        disabled={apiLoading}
                        color="error"
                      >
                        <Delete />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {paginatedTotalPages > 1 && (
            <Box display="flex" justifyContent="center" mt={3}>
              <Pagination
                count={paginatedTotalPages}
                page={page}
                onChange={(e, value) => setPage(value)}
                color="primary"
              />
            </Box>
          )}
        </TableContainer>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{fileToDelete?.file_name}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDeleteDialog(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            variant="contained"
            disabled={apiLoading}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </StyledPaper>
  );
};

export default FileList;
