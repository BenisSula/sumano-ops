import React, { useState, useReducer, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { 
  Box, 
  Paper, 
  Typography, 
  TextField, 
  Button, 
  Grid, 
  FormControl, 
  FormLabel, 
  FormGroup, 
  FormControlLabel, 
  Checkbox, 
  Select, 
  MenuItem, 
  InputLabel, 
  Alert, 
  CircularProgress,
  Divider,
  Card,
  CardContent,
  Chip,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { styled } from '@mui/material/styles';

import { useOfflineStorage } from '../hooks/useOfflineStorage';
import { useApiClient } from '../hooks/useApiClient';
import SignaturePad from 'react-signature-canvas';

// Styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  margin: theme.spacing(2),
  borderRadius: theme.spacing(2),
  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
}));

const ChecklistCard = styled(Card)(({ theme }) => ({
  margin: theme.spacing(2, 0),
  borderRadius: theme.spacing(1.5),
  border: `2px solid ${theme.palette.primary.light}`,
  '&:hover': {
    boxShadow: '0 6px 16px rgba(0,0,0,0.15)',
  },
}));

const SignatureContainer = styled(Box)(({ theme }) => ({
  border: `2px dashed ${theme.palette.primary.main}`,
  borderRadius: theme.spacing(1),
  padding: theme.spacing(2),
  backgroundColor: '#fafafa',
  minHeight: '200px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
}));

const ProgressIndicator = styled(Box)(({ theme }) => ({
  backgroundColor: theme.palette.primary.light,
  borderRadius: theme.spacing(1),
  padding: theme.spacing(2),
  margin: theme.spacing(2, 0),
  textAlign: 'center',
}));

// Form state reducer
const formReducer = (state, action) => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_SUCCESS':
      return { ...state, success: action.payload };
    case 'UPDATE_CHECKLIST':
      return { 
        ...state, 
        checklist: { ...state.checklist, ...action.payload }
      };
    case 'SET_SIGNATURE_DIALOG':
      return { ...state, signatureDialogOpen: action.payload };
    case 'SET_SIGNATURE_TYPE':
      return { ...state, signatureType: action.payload };
    case 'SET_SIGNATURES':
      return { ...state, signatures: { ...state.signatures, ...action.payload } };
    default:
      return state;
  }
};

// Checklist items configuration
const CHECKLIST_ITEMS = [
  { key: 'digital_gateway_live', label: 'Digital Gateway Live', description: 'Payment gateway is operational and tested' },
  { key: 'mobile_friendly', label: 'Mobile Friendly', description: 'Website is fully responsive on mobile devices' },
  { key: 'pages_present', label: 'All Pages Present', description: 'All required pages are created and functional' },
  { key: 'portals_linked', label: 'Portals Linked', description: 'Student and staff portals are properly connected' },
  { key: 'social_media_embedded', label: 'Social Media Embedded', description: 'Social media integration is working' },
  { key: 'logo_colors_correct', label: 'Logo & Colors Correct', description: 'School branding matches specifications' },
  { key: 'photos_content_displayed', label: 'Photos & Content Displayed', description: 'All content and images are properly displayed' },
  { key: 'layout_design_ok', label: 'Layout & Design OK', description: 'Overall design meets requirements' },
  { key: 'staff_training_completed', label: 'Staff Training Completed', description: 'Staff have been trained on the system' },
  { key: 'training_materials_provided', label: 'Training Materials Provided', description: 'Training materials and documentation provided' },
  { key: 'no_critical_errors', label: 'No Critical Errors', description: 'No critical bugs or issues remain' },
  { key: 'minor_issues_resolved', label: 'Minor Issues Resolved', description: 'All minor issues have been addressed' },
];

const ACCEPTANCE_STATUS_OPTIONS = [
  { value: 'accepted', label: 'Accepted', color: 'success' },
  { value: 'accepted_with_conditions', label: 'Accepted with Conditions', color: 'warning' },
  { value: 'not_accepted', label: 'Not Accepted', color: 'error' },
];

const PilotAcceptanceForm = ({ projectId, onSuccess, onCancel }) => {
  // Form state
  const [formState, dispatch] = useReducer(formReducer, {
    isLoading: false,
    error: null,
    success: null,
    checklist: {},
    signatures: {},
    signatureDialogOpen: false,
    signatureType: null,
  });

  // Form control
  const { control, handleSubmit, watch, setValue, getValues, formState: { errors } } = useForm({
    defaultValues: {
      project_id: projectId,
      acceptance_status: 'accepted',
      completion_date: new Date(),
      token_payment: '',
      issues_to_resolve: '',
      checklist: {},
      signatures: {},
    }
  });

  // Hooks
  const { saveOffline, syncOffline, isOnline } = useOfflineStorage();
  const { submitPilotAcceptance, generateAcceptancePDF, isLoading, error } = useApiClient();

  // Watch form values for auto-save
  const watchedValues = watch();

  // Auto-save to offline storage
  useEffect(() => {
    if (Object.keys(watchedValues).length > 0) {
      saveOffline('pilot_acceptance_form', watchedValues);
    }
  }, [watchedValues, saveOffline]);

  // Calculate completion percentage
  const calculateCompletion = () => {
    const checklist = formState.checklist;
    const totalItems = CHECKLIST_ITEMS.length;
    const completedItems = Object.values(checklist).filter(Boolean).length;
    return Math.round((completedItems / totalItems) * 100);
  };

  // Handle checklist item change
  const handleChecklistChange = (itemKey, checked) => {
    dispatch({ type: 'UPDATE_CHECKLIST', payload: { [itemKey]: checked } });
    setValue(`checklist.${itemKey}`, checked);
  };

  // Handle signature capture
  const handleSignatureCapture = (type) => {
    dispatch({ type: 'SET_SIGNATURE_TYPE', payload: type });
    dispatch({ type: 'SET_SIGNATURE_DIALOG', payload: true });
  };

  // Handle signature save
  const handleSignatureSave = (signatureData) => {
    const signatureType = formState.signatureType;
    dispatch({ 
      type: 'SET_SIGNATURES', 
      payload: { [signatureType]: signatureData } 
    });
    setValue(`signatures.${signatureType}`, signatureData);
    dispatch({ type: 'SET_SIGNATURE_DIALOG', payload: false });
  };

  // Handle form submission
  const onSubmit = async (data) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    try {
      const formData = {
        ...data,
        checklist: formState.checklist,
        signatures: formState.signatures,
      };

      if (isOnline) {
        const result = await submitPilotAcceptance(formData);
        dispatch({ type: 'SET_SUCCESS', payload: 'Pilot acceptance submitted successfully!' });
        
        if (onSuccess) {
          onSuccess(result);
        }
      } else {
        // Save offline for later sync
        await saveOffline('pending_pilot_acceptance', formData);
        dispatch({ type: 'SET_SUCCESS', payload: 'Pilot acceptance saved offline. Will sync when online.' });
      }
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.message || 'Failed to submit pilot acceptance' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  // Handle PDF generation
  const handleGeneratePDF = async () => {
    const formData = getValues();
    try {
      const pdfUrl = await generateAcceptancePDF(formData);
      window.open(pdfUrl, '_blank');
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to generate PDF. Please try again.' });
    }
  };

  const completionPercentage = calculateCompletion();

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <StyledPaper>
        <Typography variant="h4" component="h1" gutterBottom align="center" color="primary">
          Pilot Project Acceptance Form
        </Typography>

        <ProgressIndicator>
          <Typography variant="h6" color="primary">
            Completion Progress: {completionPercentage}%
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={completionPercentage} 
            sx={{ mt: 1, height: 8, borderRadius: 4 }}
          />
        </ProgressIndicator>

        {formState.error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {formState.error}
          </Alert>
        )}

        {formState.success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {formState.success}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit(onSubmit)}>
          {/* Project Information Section */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h5" gutterBottom color="primary">
                Project Information
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Controller
                    name="acceptance_status"
                    control={control}
                    rules={{ required: 'Acceptance status is required' }}
                    render={({ field }) => (
                      <FormControl fullWidth error={!!errors.acceptance_status}>
                        <InputLabel>Acceptance Status</InputLabel>
                        <Select {...field} label="Acceptance Status">
                          {ACCEPTANCE_STATUS_OPTIONS.map((option) => (
                            <MenuItem key={option.value} value={option.value}>
                              <Chip 
                                label={option.label} 
                                color={option.color} 
                                size="small" 
                                sx={{ mr: 1 }}
                              />
                              {option.label}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    )}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Controller
                    name="completion_date"
                    control={control}
                    rules={{ required: 'Completion date is required' }}
                    render={({ field }) => (
                      <DatePicker
                        {...field}
                        label="Completion Date"
                        renderInput={(params) => (
                          <TextField 
                            {...params} 
                            fullWidth 
                            error={!!errors.completion_date}
                            helperText={errors.completion_date?.message}
                          />
                        )}
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Controller
                    name="token_payment"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Token Payment Amount"
                        type="number"
                        fullWidth
                        inputProps={{ step: "0.01", min: "0" }}
                        helperText="Payment amount for pilot completion"
                      />
                    )}
                  />
                </Grid>
                <Grid item xs={12}>
                  <Controller
                    name="issues_to_resolve"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Issues to Resolve (Optional)"
                        multiline
                        rows={3}
                        fullWidth
                        helperText="Any issues that need to be resolved"
                      />
                    )}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Acceptance Checklist Section */}
          <ChecklistCard>
            <CardContent>
              <Typography variant="h5" gutterBottom color="primary">
                Acceptance Checklist
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Please verify each item below. All items must be checked for full acceptance.
              </Typography>
              
              <Grid container spacing={2}>
                {CHECKLIST_ITEMS.map((item) => (
                  <Grid item xs={12} md={6} key={item.key}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={formState.checklist[item.key] || false}
                          onChange={(e) => handleChecklistChange(item.key, e.target.checked)}
                          color="primary"
                        />
                      }
                      label={
                        <Box>
                          <Typography variant="subtitle2" fontWeight="bold">
                            {item.label}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {item.description}
                          </Typography>
                        </Box>
                      }
                    />
                  </Grid>
                ))}
              </Grid>

              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Typography variant="body1">
                  <strong>Checklist Completion: {completionPercentage}%</strong>
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={completionPercentage} 
                  sx={{ mt: 1, height: 6, borderRadius: 3 }}
                />
              </Box>
            </CardContent>
          </ChecklistCard>

          {/* Signatures Section */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h5" gutterBottom color="primary">
                Digital Signatures
              </Typography>
              
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    School Representative
                  </Typography>
                  <SignatureContainer>
                    {formState.signatures.school_representative ? (
                      <Box>
                        <Typography variant="body1" color="success.main">
                          ✓ Signed by {formState.signatures.school_representative.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {formState.signatures.school_representative.title}
                        </Typography>
                        <Button 
                          variant="outlined" 
                          size="small" 
                          onClick={() => handleSignatureCapture('school_representative')}
                          sx={{ mt: 1 }}
                        >
                          Re-sign
                        </Button>
                      </Box>
                    ) : (
                      <Box textAlign="center">
                        <Typography variant="body1" gutterBottom>
                          No signature captured
                        </Typography>
                        <Button 
                          variant="contained" 
                          onClick={() => handleSignatureCapture('school_representative')}
                        >
                          Capture Signature
                        </Button>
                      </Box>
                    )}
                  </SignatureContainer>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    Company Representative
                  </Typography>
                  <SignatureContainer>
                    {formState.signatures.company_representative ? (
                      <Box>
                        <Typography variant="body1" color="success.main">
                          ✓ Signed by {formState.signatures.company_representative.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {formState.signatures.company_representative.title}
                        </Typography>
                        <Button 
                          variant="outlined" 
                          size="small" 
                          onClick={() => handleSignatureCapture('company_representative')}
                          sx={{ mt: 1 }}
                        >
                          Re-sign
                        </Button>
                      </Box>
                    ) : (
                      <Box textAlign="center">
                        <Typography variant="body1" gutterBottom>
                          No signature captured
                        </Typography>
                        <Button 
                          variant="contained" 
                          onClick={() => handleSignatureCapture('company_representative')}
                        >
                          Capture Signature
                        </Button>
                      </Box>
                    )}
                  </SignatureContainer>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <Stack direction="row" spacing={2} justifyContent="center" sx={{ mt: 3 }}>
            <Button
              type="button"
              variant="outlined"
              onClick={onCancel}
              disabled={isLoading}
              size="large"
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="outlined"
              onClick={handleGeneratePDF}
              disabled={isLoading}
              size="large"
            >
              Preview PDF
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={isLoading || completionPercentage < 100}
              size="large"
              startIcon={isLoading ? <CircularProgress size={20} /> : null}
            >
              {isLoading ? 'Submitting...' : 'Submit Acceptance'}
            </Button>
          </Stack>

          {completionPercentage < 100 && (
            <Alert severity="info" sx={{ mt: 2 }}>
              Please complete all checklist items before submitting the acceptance form.
            </Alert>
          )}
        </Box>

        {/* Signature Dialog */}
        <SignatureDialog
          open={formState.signatureDialogOpen}
          type={formState.signatureType}
          onSave={handleSignatureSave}
          onClose={() => dispatch({ type: 'SET_SIGNATURE_DIALOG', payload: false })}
        />
      </StyledPaper>
    </LocalizationProvider>
  );
};

// Signature Dialog Component
const SignatureDialog = ({ open, type, onSave, onClose }) => {
  const [signatureData, setSignatureData] = useState({ name: '', title: '' });
  const signaturePadRef = React.useRef();

  const handleSave = () => {
    if (signaturePadRef.current) {
      const signature = signaturePadRef.current.toDataURL();
      onSave({
        ...signatureData,
        signature,
        date: new Date().toISOString(),
      });
      setSignatureData({ name: '', title: '' });
      signaturePadRef.current.clear();
    }
  };

  const handleClear = () => {
    if (signaturePadRef.current) {
      signaturePadRef.current.clear();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Capture {type === 'school_representative' ? 'School Representative' : 'Company Representative'} Signature
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Name"
              value={signatureData.name}
              onChange={(e) => setSignatureData({ ...signatureData, name: e.target.value })}
              required
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Title"
              value={signatureData.title}
              onChange={(e) => setSignatureData({ ...signatureData, title: e.target.value })}
              required
            />
          </Grid>
          <Grid item xs={12}>
            <Box sx={{ border: '1px solid #ccc', borderRadius: 1, p: 1 }}>
              <SignaturePad
                ref={signaturePadRef}
                canvasProps={{
                  width: '100%',
                  height: 200,
                  className: 'signature-canvas',
                  style: { border: '1px solid #ddd' }
                }}
              />
            </Box>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClear}>Clear</Button>
        <Button onClick={onClose}>Cancel</Button>
        <Button 
          onClick={handleSave} 
          variant="contained"
          disabled={!signatureData.name || !signatureData.title}
        >
          Save Signature
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PilotAcceptanceForm;
