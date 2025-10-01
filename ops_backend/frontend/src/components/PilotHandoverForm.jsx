import React, { useState, useEffect, useReducer, useContext } from 'react';
import { useForm, Controller } from 'react-hook-form';
import SignaturePad from 'react-signature-canvas';
import { AuthContext } from '../contexts/AuthContext';
import { OfflineContext } from '../contexts/OfflineContext';
import { useApiClient } from '../hooks/useApiClient';
import { useOfflineSync } from '../hooks/useOfflineSync';
import { formatDate, parseDate } from '../utils/dateUtils';
import { validateRequired, validateEmail } from '../utils/validationUtils';
import './PilotHandoverForm.css';

// Initial state for form data
const initialFormState = {
  projectId: '',
  expectedDeliveryDate: '',
  assignedTeamMembers: [],
  checklist: {
    technicalSetup: {
      domainConfigured: false,
      sslActive: false,
      siteLoadOk: false,
      responsiveDesign: false,
      noBrokenLinks: false,
    },
    corePages: {
      homeCompleted: false,
      aboutNewsAdded: false,
      contactCorrect: false,
      portalLinksOk: false,
      socialMediaTested: false,
    },
    contentAccuracy: {
      logoCorrect: false,
      photosOptimized: false,
      textProofread: false,
      infoMatchesOfficial: false,
    },
    securityCompliance: {
      adminCreated: false,
      restrictedAccess: false,
      privacyStatementIncluded: false,
    },
    trainingHandoverPrep: {
      trainingScheduled: false,
      trainingMaterialsReady: false,
      howtoInstructions: false,
      supportContactAdded: false,
    },
    finalTestRun: {
      browsersTested: false,
      formsTested: false,
      backupTaken: false,
      screenshotsCaptured: false,
    },
  },
  teamLeadSignature: {
    name: '',
    signature: '',
    date: null,
  },
  approvalNotes: '',
  status: 'draft',
};

// Reducer for managing complex form state
const formReducer = (state, action) => {
  switch (action.type) {
    case 'SET_PROJECT':
      return { ...state, projectId: action.payload };
    case 'SET_DELIVERY_DATE':
      return { ...state, expectedDeliveryDate: action.payload };
    case 'SET_TEAM_MEMBERS':
      return { ...state, assignedTeamMembers: action.payload };
    case 'UPDATE_CHECKLIST_SECTION':
      return {
        ...state,
        checklist: {
          ...state.checklist,
          [action.section]: {
            ...state.checklist[action.section],
            ...action.payload,
          },
        },
      };
    case 'UPDATE_SIGNATURE':
      return {
        ...state,
        teamLeadSignature: {
          ...state.teamLeadSignature,
          ...action.payload,
        },
      };
    case 'SET_APPROVAL_NOTES':
      return { ...state, approvalNotes: action.payload };
    case 'RESET_FORM':
      return initialFormState;
    case 'LOAD_EXISTING':
      return { ...state, ...action.payload };
    default:
      return state;
  }
};

const PilotHandoverForm = ({ 
  projectId: initialProjectId = null, 
  handoverId = null, 
  onSave = null, 
  onCancel = null,
  mode = 'create' // 'create', 'edit', 'view'
}) => {
  const { user } = useContext(AuthContext);
  const { isOnline, syncPendingChanges } = useContext(OfflineContext);
  const apiClient = useApiClient();
  const { syncToServer, syncFromServer } = useOfflineSync();
  
  const [formState, dispatch] = useReducer(formReducer, initialFormState);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [signaturePad, setSignaturePad] = useState(null);
  const [projects, setProjects] = useState([]);
  const [completionPercentage, setCompletionPercentage] = useState(0);
  
  const { register, handleSubmit, control, setValue, watch, formState: { errors } } = useForm({
    defaultValues: formState,
    mode: 'onChange'
  });

  // Load projects on component mount
  useEffect(() => {
    loadProjects();
    if (handoverId) {
      loadExistingHandover();
    } else if (initialProjectId) {
      dispatch({ type: 'SET_PROJECT', payload: initialProjectId });
    }
  }, [handoverId, initialProjectId]);

  // Calculate completion percentage when checklist changes
  useEffect(() => {
    calculateCompletionPercentage();
  }, [formState.checklist]);

  // Watch form values for real-time updates
  const watchedValues = watch();

  const loadProjects = async () => {
    try {
      const response = await apiClient.get('/api/projects/');
      setProjects(response.data.results || []);
    } catch (error) {
      console.error('Error loading projects:', error);
      setError('Failed to load projects');
    }
  };

  const loadExistingHandover = async () => {
    if (!handoverId) return;
    
    setIsLoading(true);
    try {
      const response = await apiClient.get(`/api/pilot-handover/${handoverId}/`);
      const handover = response.data;
      
      dispatch({
        type: 'LOAD_EXISTING',
        payload: {
          projectId: handover.project,
          expectedDeliveryDate: handover.document_instance_detail?.filled_data?.expected_delivery_date || '',
          assignedTeamMembers: handover.document_instance_detail?.filled_data?.assigned_team_members || [],
          checklist: handover.document_instance_detail?.filled_data?.checklist || initialFormState.checklist,
          teamLeadSignature: handover.document_instance_detail?.filled_data?.team_lead_signature || initialFormState.teamLeadSignature,
          approvalNotes: handover.approval_notes || '',
          status: handover.status,
        }
      });
      
      // Set form values
      Object.keys(handover.document_instance_detail?.filled_data?.checklist || {}).forEach(section => {
        Object.keys(handover.document_instance_detail.filled_data.checklist[section]).forEach(field => {
          setValue(`checklist.${section}.${field}`, handover.document_instance_detail.filled_data.checklist[section][field]);
        });
      });
      
    } catch (error) {
      console.error('Error loading handover:', error);
      setError('Failed to load handover data');
    } finally {
      setIsLoading(false);
    }
  };

  const calculateCompletionPercentage = () => {
    const sections = Object.values(formState.checklist);
    const totalItems = sections.reduce((total, section) => total + Object.keys(section).length, 0);
    const completedItems = sections.reduce((total, section) => 
      total + Object.values(section).filter(Boolean).length, 0
    );
    const percentage = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;
    setCompletionPercentage(percentage);
  };

  const updateChecklistSection = (section, field, value) => {
    dispatch({
      type: 'UPDATE_CHECKLIST_SECTION',
      section,
      payload: { [field]: value },
    });
    setValue(`checklist.${section}.${field}`, value);
  };

  const addTeamMember = () => {
    const newMembers = [...formState.assignedTeamMembers, ''];
    dispatch({ type: 'SET_TEAM_MEMBERS', payload: newMembers });
  };

  const removeTeamMember = (index) => {
    const newMembers = formState.assignedTeamMembers.filter((_, i) => i !== index);
    dispatch({ type: 'SET_TEAM_MEMBERS', payload: newMembers });
  };

  const updateTeamMember = (index, value) => {
    const newMembers = [...formState.assignedTeamMembers];
    newMembers[index] = value;
    dispatch({ type: 'SET_TEAM_MEMBERS', payload: newMembers });
  };

  const captureSignature = () => {
    if (signaturePad) {
      const signature = signaturePad.toDataURL();
      dispatch({
        type: 'UPDATE_SIGNATURE',
        payload: {
          signature,
          date: new Date().toISOString(),
        },
      });
      setValue('teamLeadSignature.signature', signature);
      setValue('teamLeadSignature.date', new Date().toISOString());
    }
  };

  const clearSignature = () => {
    if (signaturePad) {
      signaturePad.clear();
      dispatch({
        type: 'UPDATE_SIGNATURE',
        payload: {
          signature: '',
          date: null,
        },
      });
      setValue('teamLeadSignature.signature', '');
      setValue('teamLeadSignature.date', null);
    }
  };

  const onSubmit = async (data) => {
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const payload = {
        project_id: formState.projectId,
        expected_delivery_date: formState.expectedDeliveryDate,
        assigned_team_members: formState.assignedTeamMembers.filter(member => member.trim() !== ''),
        checklist: formState.checklist,
        team_lead_signature: formState.teamLeadSignature,
        approval_notes: formState.approvalNotes,
      };

      let response;
      if (mode === 'edit' && handoverId) {
        response = await apiClient.patch(`/api/pilot-handover/${handoverId}/`, payload);
      } else {
        response = await apiClient.post('/api/pilot-handover/', payload);
      }

      setSuccess(mode === 'edit' ? 'Handover updated successfully' : 'Handover created successfully');
      
      if (onSave) {
        onSave(response.data);
      }

      // Sync to server if online
      if (isOnline) {
        await syncToServer();
      }

    } catch (error) {
      console.error('Error saving handover:', error);
      
      if (!isOnline) {
        // Store for offline sync
        await syncFromServer({
          type: 'pilot_handover',
          action: mode === 'edit' ? 'update' : 'create',
          data: payload,
          handoverId: handoverId,
        });
        setSuccess('Handover saved offline and will sync when online');
      } else {
        setError(error.response?.data?.detail || 'Failed to save handover');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const generateDocument = async () => {
    if (!handoverId) {
      setError('Please save the handover first before generating document');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await apiClient.post(`/api/pilot-handover/${handoverId}/generate_handover_document/`);
      
      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Internal_Handover_Document_${formState.projectId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      setSuccess('Document generated and downloaded successfully');
    } catch (error) {
      console.error('Error generating document:', error);
      setError('Failed to generate document');
    } finally {
      setIsSubmitting(false);
    }
  };

  const signHandover = async () => {
    if (!handoverId) {
      setError('Please save the handover first before signing');
      return;
    }

    if (!formState.teamLeadSignature.signature) {
      setError('Please provide your signature');
      return;
    }

    setIsSubmitting(true);
    try {
      const signatureData = {
        signature_data: {
          name: formState.teamLeadSignature.name || user.username,
          signature: formState.teamLeadSignature.signature,
          date: formState.teamLeadSignature.date || new Date().toISOString(),
        }
      };

      await apiClient.post(`/api/pilot-handover/${handoverId}/sign_handover/`, signatureData);
      setSuccess('Handover signed successfully');
      
      // Reload handover data
      loadExistingHandover();
      
    } catch (error) {
      console.error('Error signing handover:', error);
      setError('Failed to sign handover');
    } finally {
      setIsSubmitting(false);
    }
  };

  const ChecklistSection = ({ title, sectionKey, items }) => (
    <div className="checklist-section">
      <h3>{title}</h3>
      <div className="checklist-items">
        {Object.entries(items).map(([key, value]) => (
          <label key={key} className="checklist-item">
            <input
              type="checkbox"
              checked={value}
              onChange={(e) => updateChecklistSection(sectionKey, key, e.target.checked)}
              disabled={mode === 'view'}
            />
            <span className="checklist-label">{key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}</span>
          </label>
        ))}
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <div className="pilot-handover-form loading">
        <div className="loading-spinner">Loading handover data...</div>
      </div>
    );
  }

  return (
    <div className="pilot-handover-form">
      <div className="form-header">
        <h2>Internal Pilot Handover</h2>
        <div className="completion-indicator">
          <span>Completion: {completionPercentage}%</span>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${completionPercentage}%` }}
            />
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}

      <form onSubmit={handleSubmit(onSubmit)} className="handover-form">
        {/* Project Selection */}
        <div className="form-section">
          <h3>Project Information</h3>
          <div className="form-row">
            <label htmlFor="projectId">Project *</label>
            <select
              id="projectId"
              value={formState.projectId}
              onChange={(e) => dispatch({ type: 'SET_PROJECT', payload: e.target.value })}
              disabled={mode === 'view' || handoverId}
              required
            >
              <option value="">Select a project</option>
              {projects.map(project => (
                <option key={project.id} value={project.id}>
                  {project.project_name} - {project.client_organization_name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <label htmlFor="expectedDeliveryDate">Expected Delivery Date *</label>
            <input
              type="date"
              id="expectedDeliveryDate"
              value={formState.expectedDeliveryDate}
              onChange={(e) => dispatch({ type: 'SET_DELIVERY_DATE', payload: e.target.value })}
              disabled={mode === 'view'}
              required
            />
          </div>

          <div className="form-row">
            <label>Assigned Team Members</label>
            {formState.assignedTeamMembers.map((member, index) => (
              <div key={index} className="team-member-row">
                <input
                  type="text"
                  value={member}
                  onChange={(e) => updateTeamMember(index, e.target.value)}
                  disabled={mode === 'view'}
                  placeholder="Team member name"
                />
                {mode !== 'view' && (
                  <button
                    type="button"
                    onClick={() => removeTeamMember(index)}
                    className="remove-member-btn"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            {mode !== 'view' && (
              <button type="button" onClick={addTeamMember} className="add-member-btn">
                Add Team Member
              </button>
            )}
          </div>
        </div>

        {/* Checklist Sections */}
        <div className="form-section">
          <h3>Internal Handover Checklist</h3>
          
          <ChecklistSection
            title="Technical Setup"
            sectionKey="technicalSetup"
            items={formState.checklist.technicalSetup}
          />
          
          <ChecklistSection
            title="Core Pages"
            sectionKey="corePages"
            items={formState.checklist.corePages}
          />
          
          <ChecklistSection
            title="Content Accuracy"
            sectionKey="contentAccuracy"
            items={formState.checklist.contentAccuracy}
          />
          
          <ChecklistSection
            title="Security & Compliance"
            sectionKey="securityCompliance"
            items={formState.checklist.securityCompliance}
          />
          
          <ChecklistSection
            title="Training & Handover Prep"
            sectionKey="trainingHandoverPrep"
            items={formState.checklist.trainingHandoverPrep}
          />
          
          <ChecklistSection
            title="Final Test Run"
            sectionKey="finalTestRun"
            items={formState.checklist.finalTestRun}
          />
        </div>

        {/* Team Lead Signature */}
        <div className="form-section">
          <h3>Team Lead Approval</h3>
          
          <div className="form-row">
            <label htmlFor="teamLeadName">Team Lead Name</label>
            <input
              type="text"
              id="teamLeadName"
              value={formState.teamLeadSignature.name}
              onChange={(e) => dispatch({
                type: 'UPDATE_SIGNATURE',
                payload: { name: e.target.value }
              })}
              disabled={mode === 'view'}
              placeholder="Enter team lead name"
            />
          </div>

          <div className="form-row">
            <label>Digital Signature</label>
            <div className="signature-container">
              <SignaturePad
                ref={(ref) => setSignaturePad(ref)}
                canvasProps={{
                  className: 'signature-canvas',
                  width: 400,
                  height: 200,
                }}
                backgroundColor="white"
                penColor="black"
              />
              {mode !== 'view' && (
                <div className="signature-controls">
                  <button type="button" onClick={captureSignature}>
                    Capture Signature
                  </button>
                  <button type="button" onClick={clearSignature}>
                    Clear Signature
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="form-row">
            <label htmlFor="approvalNotes">Approval Notes</label>
            <textarea
              id="approvalNotes"
              value={formState.approvalNotes}
              onChange={(e) => dispatch({ type: 'SET_APPROVAL_NOTES', payload: e.target.value })}
              disabled={mode === 'view'}
              placeholder="Any additional notes or comments..."
              rows={4}
            />
          </div>
        </div>

        {/* Form Actions */}
        <div className="form-actions">
          {mode !== 'view' && (
            <>
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-primary"
              >
                {isSubmitting ? 'Saving...' : (mode === 'edit' ? 'Update Handover' : 'Create Handover')}
              </button>
              
              {handoverId && (
                <>
                  <button
                    type="button"
                    onClick={generateDocument}
                    disabled={isSubmitting}
                    className="btn-secondary"
                  >
                    Generate Document
                  </button>
                  
                  <button
                    type="button"
                    onClick={signHandover}
                    disabled={isSubmitting || !formState.teamLeadSignature.signature}
                    className="btn-success"
                  >
                    Sign Handover
                  </button>
                </>
              )}
            </>
          )}
          
          <button
            type="button"
            onClick={onCancel}
            className="btn-cancel"
          >
            {mode === 'view' ? 'Close' : 'Cancel'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default PilotHandoverForm;
