import React, { useState, useCallback } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Tabs, 
  Tab, 
  Alert,
  Stack
} from '@mui/material';
import { styled } from '@mui/material/styles';

// Components
import FileUploader from './FileUploader';
import FileList from './FileList';

// Styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  margin: theme.spacing(2),
  maxWidth: 1200,
  marginLeft: 'auto',
  marginRight: 'auto',
}));

const TabPanel = ({ children, value, index, ...other }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`file-manager-tabpanel-${index}`}
    aria-labelledby={`file-manager-tab-${index}`}
    {...other}
  >
    {value === index && (
      <Box sx={{ p: 3 }}>
        {children}
      </Box>
    )}
  </div>
);

const FileManager = ({ projectId, projectName }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState(null);

  // Handle tab change
  const handleTabChange = useCallback((event, newValue) => {
    setActiveTab(newValue);
  }, []);

  // Handle file upload success
  const handleFileUploaded = useCallback((uploadedFile) => {
    setRefreshTrigger(prev => prev + 1);
    setUploadSuccess(`File "${uploadedFile.file_name}" uploaded successfully!`);
    
    // Auto-hide success message after 5 seconds
    setTimeout(() => {
      setUploadSuccess(null);
    }, 5000);
  }, []);

  // Handle file deletion
  const handleFileDeleted = useCallback((deletedFileId) => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  if (!projectId) {
    return (
      <StyledPaper elevation={2}>
        <Box p={3}>
          <Alert severity="warning">
            Please select a project to manage files.
          </Alert>
        </Box>
      </StyledPaper>
    );
  }

  return (
    <StyledPaper elevation={2}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h4" sx={{ p: 2, pb: 1 }}>
          File Manager
        </Typography>
        {projectName && (
          <Typography variant="subtitle1" color="text.secondary" sx={{ px: 2, pb: 1 }}>
            Project: {projectName}
          </Typography>
        )}
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          aria-label="file manager tabs"
          sx={{ px: 2 }}
        >
          <Tab label="Upload Files" />
          <Tab label="View Files" />
        </Tabs>
      </Box>

      {/* Success Message */}
      {uploadSuccess && (
        <Alert 
          severity="success" 
          sx={{ mx: 2, mt: 2 }}
          onClose={() => setUploadSuccess(null)}
        >
          {uploadSuccess}
        </Alert>
      )}

      <TabPanel value={activeTab} index={0}>
        <FileUploader
          projectId={projectId}
          onFileUploaded={handleFileUploaded}
          onFileDeleted={handleFileDeleted}
        />
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <FileList
          projectId={projectId}
          refreshTrigger={refreshTrigger}
        />
      </TabPanel>
    </StyledPaper>
  );
};

export default FileManager;
