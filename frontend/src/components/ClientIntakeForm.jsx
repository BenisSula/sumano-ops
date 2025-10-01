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
  Switch, 
  Alert, 
  CircularProgress,
  Divider,
  Card,
  CardContent,
  Chip,
  Stack
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { styled } from '@mui/material/styles';

// Custom hooks for offline storage and API calls
import { useOfflineStorage } from '../hooks/useOfflineStorage';
import { useApiClient } from '../hooks/useApiClient';

// Styled components
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  margin: theme.spacing(2),
  maxWidth: 1200,
  marginLeft: 'auto',
  marginRight: 'auto',
}));

const SectionCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(3),
}));

const FormSection = ({ title, children, ...props }) => (
  <SectionCard {...props}>
    <CardContent>
      <Typography variant="h6" gutterBottom color="primary">
        {title}
      </Typography>
      <Divider sx={{ mb: 2 }} />
      {children}
    </CardContent>
  </SectionCard>
);

// Form state reducer for complex state management
const formReducer = (state, action) => {
  switch (action.type) {
    case 'SET_FIELD':
      return {
        ...state,
        [action.field]: action.value,
      };
    case 'SET_MULTIPLE_FIELDS':
      return {
        ...state,
        ...action.fields,
      };
    case 'RESET_FORM':
      return action.initialState;
    default:
      return state;
  }
};

// Project type options for school pilot
const PROJECT_TYPES = [
  { value: 'website_development', label: 'Website Development' },
  { value: 'mobile_app', label: 'Mobile Application' },
  { value: 'student_portal', label: 'Student Portal' },
  { value: 'parent_portal', label: 'Parent Portal' },
  { value: 'teacher_portal', label: 'Teacher Portal' },
  { value: 'admin_portal', label: 'Administrative Portal' },
  { value: 'learning_management_system', label: 'Learning Management System' },
  { value: 'communication_system', label: 'Communication System' },
  { value: 'assessment_tools', label: 'Assessment Tools' },
  { value: 'reporting_system', label: 'Reporting System' },
  { value: 'other', label: 'Other' },
];

// Project purpose options
const PROJECT_PURPOSES = [
  { value: 'improve_student_engagement', label: 'Improve Student Engagement' },
  { value: 'enhance_communication', label: 'Enhance Communication' },
  { value: 'streamline_administration', label: 'Streamline Administration' },
  { value: 'modernize_technology', label: 'Modernize Technology' },
  { value: 'improve_parent_involvement', label: 'Improve Parent Involvement' },
  { value: 'enhance_learning_experience', label: 'Enhance Learning Experience' },
  { value: 'reduce_manual_processes', label: 'Reduce Manual Processes' },
  { value: 'improve_data_management', label: 'Improve Data Management' },
  { value: 'increase_accessibility', label: 'Increase Accessibility' },
  { value: 'other', label: 'Other' },
];

// Pilot scope features
const PILOT_FEATURES = [
  { value: 'user_authentication', label: 'User Authentication' },
  { value: 'student_management', label: 'Student Management' },
  { value: 'class_management', label: 'Class Management' },
  { value: 'gradebook', label: 'Gradebook' },
  { value: 'attendance_tracking', label: 'Attendance Tracking' },
  { value: 'parent_communication', label: 'Parent Communication' },
  { value: 'teacher_tools', label: 'Teacher Tools' },
  { value: 'admin_dashboard', label: 'Admin Dashboard' },
  { value: 'reporting_analytics', label: 'Reporting & Analytics' },
  { value: 'mobile_responsive', label: 'Mobile Responsive Design' },
  { value: 'multi_language', label: 'Multi-language Support' },
  { value: 'integration_apis', label: 'Integration APIs' },
  { value: 'data_export', label: 'Data Export' },
  { value: 'backup_recovery', label: 'Backup & Recovery' },
  { value: 'security_features', label: 'Security Features' },
];

// Timeline preferences
const TIMELINE_OPTIONS = [
  { value: 'asap', label: 'ASAP' },
  { value: '1_month', label: 'Within 1 Month' },
  { value: '3_months', label: 'Within 3 Months' },
  { value: '6_months', label: 'Within 6 Months' },
  { value: 'flexible', label: 'Flexible' },
];

const ClientIntakeForm = () => {
  // Form state management
  const [formState, dispatch] = useReducer(formReducer, {
    projectTypes: [],
    projectPurposes: [],
    pilotFeatures: [],
    isSubmitting: false,
    isOffline: false,
    lastSaved: null,
  });

  // React Hook Form setup
  const {
    control,
    handleSubmit,
    watch,
    setValue,
    getValues,
    formState: { errors, isDirty },
    reset,
  } = useForm({
    defaultValues: {
      // School Information
      school_name: '',
      address: '',
      contact_person: '',
      role_position: '',
      phone_whatsapp: '',
      email: '',
      current_website: '',
      number_of_students: '',
      number_of_staff: '',
      
      // Project Information
      project_type: [],
      project_purpose: [],
      pilot_scope_features: [],
      
      // Timeline
      pilot_start_date: null,
      pilot_end_date: null,
      timeline_preference: '',
      
      // Design Preferences
      design_preferences: {},
      logo_colors: {},
      
      // Content and Maintenance
      content_availability: false,
      maintenance_plan: {},
      
      // Financial
      token_commitment_fee: '',
      
      // Additional Information
      additional_notes: '',
      acknowledgment: {},
    },
  });

  // Custom hooks
  const { saveOffline, syncOffline, isOnline } = useOfflineStorage();
  const { submitClientIntake, generatePDF, isLoading, error } = useApiClient();

  // Watch form values for auto-save
  const watchedValues = watch();

  // Auto-save to offline storage
  useEffect(() => {
    if (isDirty && !formState.isSubmitting) {
      const timeoutId = setTimeout(() => {
        saveOffline('client_intake_form', watchedValues);
        dispatch({ type: 'SET_FIELD', field: 'lastSaved', value: new Date() });
      }, 2000); // Auto-save after 2 seconds of inactivity

      return () => clearTimeout(timeoutId);
    }
  }, [watchedValues, isDirty, formState.isSubmitting, saveOffline]);

  // Load saved data on mount
  useEffect(() => {
    const loadSavedData = async () => {
      try {
        const savedData = await syncOffline('client_intake_form');
        if (savedData) {
          Object.keys(savedData).forEach(key => {
            setValue(key, savedData[key]);
          });
        }
      } catch (error) {
        console.error('Failed to load saved data:', error);
      }
    };

    loadSavedData();
  }, [syncOffline, setValue]);

  // Handle form submission
  const onSubmit = async (data) => {
    dispatch({ type: 'SET_FIELD', field: 'isSubmitting', value: true });
    
    try {
      // Validate required fields
      const requiredFields = [
        'school_name', 'contact_person', 'email', 'project_type',
        'project_purpose', 'pilot_scope_features', 'timeline_preference'
      ];
      
      const missingFields = requiredFields.filter(field => {
        const value = data[field];
        return !value || (Array.isArray(value) && value.length === 0);
      });
      
      if (missingFields.length > 0) {
        throw new Error(`Please fill in all required fields: ${missingFields.join(', ')}`);
      }

      // Submit the form
      const response = await submitClientIntake(data);
      
      // Clear offline storage on successful submission
      await saveOffline('client_intake_form', null);
      
      // Show success message
      alert('Intake form submitted successfully!');
      
      // Reset form
      reset();
      dispatch({ type: 'RESET_FORM', initialState: {} });
      
    } catch (error) {
      console.error('Form submission error:', error);
      // Save to offline storage for later sync
      await saveOffline('client_intake_form', data);
      alert(`Form submission failed: ${error.message}. Data saved offline for later sync.`);
    } finally {
      dispatch({ type: 'SET_FIELD', field: 'isSubmitting', value: false });
    }
  };

  // Handle PDF generation
  const handleGeneratePDF = async () => {
    const formData = getValues();
    try {
      const pdfUrl = await generatePDF(formData);
      window.open(pdfUrl, '_blank');
    } catch (error) {
      console.error('PDF generation error:', error);
      alert('Failed to generate PDF. Please try again.');
    }
  };

  // Render multi-select checkboxes
  const renderMultiSelect = (name, options, label) => (
    <FormControl component="fieldset" error={!!errors[name]}>
      <FormLabel component="legend">{label}</FormLabel>
      <FormGroup>
        <Grid container spacing={1}>
          {options.map((option) => (
            <Grid item xs={12} sm={6} md={4} key={option.value}>
              <Controller
                name={name}
                control={control}
                render={({ field }) => (
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={field.value?.includes(option.value) || false}
                        onChange={(e) => {
                          const currentValue = field.value || [];
                          if (e.target.checked) {
                            field.onChange([...currentValue, option.value]);
                          } else {
                            field.onChange(currentValue.filter(v => v !== option.value));
                          }
                        }}
                      />
                    }
                    label={option.label}
                  />
                )}
              />
            </Grid>
          ))}
        </Grid>
      </FormGroup>
      {errors[name] && (
        <Typography variant="caption" color="error">
          {errors[name].message}
        </Typography>
      )}
    </FormControl>
  );

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <StyledPaper elevation={3}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" component="h1" gutterBottom color="primary">
            School Pilot Project Intake Form
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Please fill out this form to begin your school pilot project with Sumano Tech.
          </Typography>
          
          {/* Status indicators */}
          <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
            {formState.lastSaved && (
              <Chip 
                label={`Last saved: ${formState.lastSaved.toLocaleTimeString()}`} 
                size="small" 
                color="success" 
                variant="outlined" 
              />
            )}
            {!isOnline && (
              <Chip 
                label="Offline Mode" 
                size="small" 
                color="warning" 
                variant="filled" 
              />
            )}
          </Stack>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          {/* School Information */}
          <FormSection title="School Information">
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Controller
                  name="school_name"
                  control={control}
                  rules={{ required: 'School name is required' }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="School Name *"
                      fullWidth
                      error={!!errors.school_name}
                      helperText={errors.school_name?.message}
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Controller
                  name="contact_person"
                  control={control}
                  rules={{ required: 'Contact person is required' }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Contact Person *"
                      fullWidth
                      error={!!errors.contact_person}
                      helperText={errors.contact_person?.message}
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Controller
                  name="role_position"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Role/Position"
                      fullWidth
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Controller
                  name="email"
                  control={control}
                  rules={{ 
                    required: 'Email is required',
                    pattern: {
                      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                      message: 'Invalid email address'
                    }
                  }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Email Address *"
                      type="email"
                      fullWidth
                      error={!!errors.email}
                      helperText={errors.email?.message}
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Controller
                  name="phone_whatsapp"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Phone/WhatsApp"
                      fullWidth
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Controller
                  name="current_website"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Current Website URL"
                      fullWidth
                      placeholder="https://example.com"
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12}>
                <Controller
                  name="address"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="School Address"
                      multiline
                      rows={3}
                      fullWidth
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Controller
                  name="number_of_students"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Number of Students"
                      type="number"
                      fullWidth
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Controller
                  name="number_of_staff"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Number of Staff"
                      type="number"
                      fullWidth
                    />
                  )}
                />
              </Grid>
            </Grid>
          </FormSection>

          {/* Project Information */}
          <FormSection title="Project Information">
            <Grid container spacing={3}>
              <Grid item xs={12}>
                {renderMultiSelect('project_type', PROJECT_TYPES, 'Project Types *')}
              </Grid>
              <Grid item xs={12}>
                {renderMultiSelect('project_purpose', PROJECT_PURPOSES, 'Project Purposes *')}
              </Grid>
              <Grid item xs={12}>
                {renderMultiSelect('pilot_scope_features', PILOT_FEATURES, 'Pilot Scope Features *')}
              </Grid>
            </Grid>
          </FormSection>

          {/* Timeline */}
          <FormSection title="Project Timeline">
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Controller
                  name="timeline_preference"
                  control={control}
                  rules={{ required: 'Timeline preference is required' }}
                  render={({ field }) => (
                    <FormControl fullWidth error={!!errors.timeline_preference}>
                      <InputLabel>Timeline Preference *</InputLabel>
                      <Select
                        {...field}
                        label="Timeline Preference *"
                      >
                        {TIMELINE_OPTIONS.map((option) => (
                          <MenuItem key={option.value} value={option.value}>
                            {option.label}
                          </MenuItem>
                        ))}
                      </Select>
                      {errors.timeline_preference && (
                        <Typography variant="caption" color="error">
                          {errors.timeline_preference.message}
                        </Typography>
                      )}
                    </FormControl>
                  )}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Controller
                  name="pilot_start_date"
                  control={control}
                  render={({ field }) => (
                    <DatePicker
                      {...field}
                      label="Preferred Start Date"
                      renderInput={(params) => <TextField {...params} fullWidth />}
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Controller
                  name="pilot_end_date"
                  control={control}
                  render={({ field }) => (
                    <DatePicker
                      {...field}
                      label="Expected End Date"
                      renderInput={(params) => <TextField {...params} fullWidth />}
                    />
                  )}
                />
              </Grid>
            </Grid>
          </FormSection>

          {/* Financial Information */}
          <FormSection title="Financial Commitment">
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Controller
                  name="token_commitment_fee"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Token Commitment Fee"
                      type="number"
                      fullWidth
                      InputProps={{
                        startAdornment: '$',
                      }}
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Controller
                  name="content_availability"
                  control={control}
                  render={({ field }) => (
                    <FormControlLabel
                      control={
                        <Switch
                          checked={field.value}
                          onChange={field.onChange}
                        />
                      }
                      label="Content is readily available"
                    />
                  )}
                />
              </Grid>
            </Grid>
          </FormSection>

          {/* Additional Information */}
          <FormSection title="Additional Information">
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Controller
                  name="additional_notes"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Additional Notes"
                      multiline
                      rows={4}
                      fullWidth
                      placeholder="Please provide any additional information about your project requirements, goals, or questions..."
                    />
                  )}
                />
              </Grid>
            </Grid>
          </FormSection>

          {/* Form Actions */}
          <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Button
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
              size="large"
              disabled={formState.isSubmitting || isLoading}
              startIcon={formState.isSubmitting ? <CircularProgress size={20} /> : null}
            >
              {formState.isSubmitting ? 'Submitting...' : 'Submit Intake Form'}
            </Button>
          </Box>
        </form>
      </StyledPaper>
    </LocalizationProvider>
  );
};

export default ClientIntakeForm;
