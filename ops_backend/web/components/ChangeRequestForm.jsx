/**
 * Change Request Form Component
 * 
 * Provides a comprehensive form for creating and managing change requests
 * during pilot projects, including change details, impact assessment, and client decisions.
 */

import React, { useState, useReducer, useCallback } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import SignaturePad from 'react-signature-canvas';
import { useAuth } from '../contexts/AuthContext';
import { useApi } from '../hooks/useApi';
import { useOfflineSync } from '../hooks/useOfflineSync';

// Form state reducer for complex state management
const formReducer = (state, action) => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    case 'SET_SUCCESS':
      return { ...state, success: action.payload, loading: false, error: null };
    case 'SET_IMPACT_ASSESSMENT':
      return { ...state, impactAssessment: { ...state.impactAssessment, ...action.payload } };
    case 'SET_CLIENT_DECISION':
      return { ...state, clientDecision: { ...state.clientDecision, ...action.payload } };
    case 'RESET_FORM':
      return { ...state, impactAssessment: {}, clientDecision: {}, error: null, success: null };
    default:
      return state;
  }
};

// Initial form state
const initialState = {
  loading: false,
  error: null,
  success: null,
  impactAssessment: {},
  clientDecision: {},
};

const ChangeRequestForm = ({ 
  project, 
  changeRequest = null, 
  mode = 'create', // 'create' | 'edit' | 'view'
  onSuccess = null 
}) => {
  const { user } = useAuth();
  const { apiCall, loading: apiLoading } = useApi();
  const { syncOfflineData } = useOfflineSync();
  const navigate = useNavigate();

  const [formState, dispatch] = useReducer(formReducer, initialState);
  const [signatureData, setSignatureData] = useState({
    clientSignature: null,
    providerSignature: null,
  });

  // Form configuration
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
    setValue,
    reset,
  } = useForm({
    defaultValues: {
      description: changeRequest?.change_request?.description || '',
      reason: changeRequest?.change_request?.reason || '',
      request_date: changeRequest?.request_date || new Date().toISOString().split('T')[0],
      reference_agreement: changeRequest?.reference_agreement || '',
      // Impact assessment
      no_additional_cost: changeRequest?.impact_assessment?.no_additional_cost || false,
      requires_additional_effort: changeRequest?.impact_assessment?.requires_additional_effort || false,
      estimated_time: changeRequest?.impact_assessment?.estimated_time || '',
      estimated_cost: changeRequest?.impact_assessment?.estimated_cost || '',
      // Client decision
      decision: changeRequest?.client_decision || '',
      issues_to_resolve: changeRequest?.issues_to_resolve || '',
    },
    mode: 'onBlur',
  });

  // Watch for conditional field visibility
  const noAdditionalCost = watch('no_additional_cost');
  const requiresAdditionalEffort = watch('requires_additional_effort');

  // Check user permissions
  const canManageChangeRequests = user?.role?.codename === 'staff' || user?.role?.codename === 'superadmin';
  const canMakeClientDecision = user?.role?.codename === 'client_contact' || canManageChangeRequests;

  // Handle signature capture
  const handleSignatureCapture = useCallback((type, signaturePadRef) => {
    if (signaturePadRef.current) {
      const signature = signaturePadRef.current.toDataURL();
      setSignatureData(prev => ({ ...prev, [type]: signature }));
    }
  }, []);

  // Handle impact assessment update
  const handleImpactAssessment = useCallback(async (data) => {
    if (!changeRequest?.id) return;

    try {
      dispatch({ type: 'SET_LOADING', payload: true });

      await apiCall(`/api/change-requests/${changeRequest.id}/update_impact_assessment/`, {
        method: 'POST',
        body: {
          impact_assessment: {
            no_additional_cost: data.no_additional_cost,
            requires_additional_effort: data.requires_additional_effort,
            estimated_time: data.estimated_time ? parseInt(data.estimated_time) : null,
            estimated_cost: data.estimated_cost ? parseFloat(data.estimated_cost) : null,
          }
        }
      });

      dispatch({ type: 'SET_SUCCESS', payload: 'Impact assessment updated successfully.' });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    }
  }, [changeRequest?.id, apiCall]);

  // Handle client decision
  const handleClientDecision = useCallback(async (data) => {
    if (!changeRequest?.id) return;

    try {
      dispatch({ type: 'SET_LOADING', payload: true });

      await apiCall(`/api/change-requests/${changeRequest.id}/make_client_decision/`, {
        method: 'PATCH',
        body: { decision: data.decision }
      });

      dispatch({ type: 'SET_SUCCESS', payload: 'Client decision recorded successfully.' });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    }
  }, [changeRequest?.id, apiCall]);

  // Handle signature submission
  const handleSignatureSubmit = useCallback(async () => {
    if (!changeRequest?.id) return;

    const signatureType = user?.role?.codename === 'client_contact' ? 'client_representative' : 'provider_representative';
    const signatureKey = user?.role?.codename === 'client_contact' ? 'clientSignature' : 'providerSignature';

    if (!signatureData[signatureKey]) {
      dispatch({ type: 'SET_ERROR', payload: 'Please provide a signature.' });
      return;
    }

    try {
      dispatch({ type: 'SET_LOADING', payload: true });

      await apiCall(`/api/change-requests/${changeRequest.id}/sign_change_request/`, {
        method: 'POST',
        body: {
          signature_data: {
            name: user?.username || '',
            signature: signatureData[signatureKey],
            date: new Date().toISOString(),
          }
        }
      });

      dispatch({ type: 'SET_SUCCESS', payload: 'Document signed successfully.' });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    }
  }, [changeRequest?.id, signatureData, user, apiCall]);

  // Handle form submission
  const onSubmit = async (data) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });

      let response;
      if (mode === 'create') {
        response = await apiCall('/api/change-requests/', {
          method: 'POST',
          body: {
            project_id: project.id,
            request_date: data.request_date,
            reference_agreement: data.reference_agreement,
            change_request: {
              description: data.description,
              reason: data.reason,
            }
          }
        });
      } else {
        response = await apiCall(`/api/change-requests/${changeRequest.id}/`, {
          method: 'PATCH',
          body: data
        });
      }

      // Sync offline data if needed
      await syncOfflineData();

      dispatch({ type: 'SET_SUCCESS', payload: 'Change request saved successfully.' });
      
      if (onSuccess) {
        onSuccess(response.data);
      } else if (mode === 'create') {
        navigate(`/projects/${project.id}/change-requests/${response.data.id}`);
      }

    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    }
  };

  // Handle PDF generation
  const handleGeneratePDF = useCallback(async () => {
    if (!changeRequest?.id) return;

    try {
      dispatch({ type: 'SET_LOADING', payload: true });

      const response = await apiCall(`/api/change-requests/${changeRequest.id}/generate_authorization_document/`, {
        method: 'POST',
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `change_request_${changeRequest.id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      dispatch({ type: 'SET_SUCCESS', payload: 'PDF generated successfully.' });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Error generating PDF: ' + error.message });
    }
  }, [changeRequest?.id, apiCall]);

  if (!project) {
    return (
      <div className="error-container">
        <h2>Error</h2>
        <p>No project specified for change request.</p>
      </div>
    );
  }

  return (
    <div className="change-request-form">
      <div className="form-header">
        <h2>Change Request Form</h2>
        <div className="project-info">
          <p><strong>Project:</strong> {project.project_name}</p>
          <p><strong>Client:</strong> {project.client?.organization?.name}</p>
        </div>
      </div>

      {/* Success/Error Messages */}
      {formState.success && (
        <div className="alert alert-success" role="alert">
          {formState.success}
        </div>
      )}
      {formState.error && (
        <div className="alert alert-error" role="alert">
          {formState.error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="change-request-form-content">
        
        {/* Request Details Section */}
        <section className="form-section">
          <h3>Request Details</h3>
          
          <div className="form-group">
            <label htmlFor="description" className="required">
              Change Description
            </label>
            <Controller
              name="description"
              control={control}
              rules={{ required: 'Description is required' }}
              render={({ field }) => (
                <textarea
                  {...field}
                  id="description"
                  rows={4}
                  className={`form-control ${errors.description ? 'error' : ''}`}
                  placeholder="Describe the requested change in detail..."
                  disabled={mode === 'view'}
                  aria-describedby={errors.description ? 'description-error' : undefined}
                />
              )}
            />
            {errors.description && (
              <span id="description-error" className="error-message" role="alert">
                {errors.description.message}
              </span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="reason" className="required">
              Business Reason
            </label>
            <Controller
              name="reason"
              control={control}
              rules={{ required: 'Reason is required' }}
              render={({ field }) => (
                <textarea
                  {...field}
                  id="reason"
                  rows={3}
                  className={`form-control ${errors.reason ? 'error' : ''}`}
                  placeholder="Explain why this change is needed..."
                  disabled={mode === 'view'}
                  aria-describedby={errors.reason ? 'reason-error' : undefined}
                />
              )}
            />
            {errors.reason && (
              <span id="reason-error" className="error-message" role="alert">
                {errors.reason.message}
              </span>
            )}
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="request_date">
                Request Date
              </label>
              <Controller
                name="request_date"
                control={control}
                render={({ field }) => (
                  <input
                    {...field}
                    type="date"
                    id="request_date"
                    className="form-control"
                    disabled={mode === 'view'}
                  />
                )}
              />
            </div>

            <div className="form-group">
              <label htmlFor="reference_agreement">
                Reference Agreement
              </label>
              <Controller
                name="reference_agreement"
                control={control}
                render={({ field }) => (
                  <input
                    {...field}
                    type="text"
                    id="reference_agreement"
                    className="form-control"
                    placeholder="Agreement/Contract reference"
                    disabled={mode === 'view'}
                  />
                )}
              />
            </div>
          </div>
        </section>

        {/* Impact Assessment Section (Staff only) */}
        {canManageChangeRequests && (
          <section className="form-section">
            <h3>Impact Assessment</h3>
            
            <div className="form-group">
              <Controller
                name="no_additional_cost"
                control={control}
                render={({ field }) => (
                  <label className="checkbox-label">
                    <input
                      {...field}
                      type="checkbox"
                      checked={field.value}
                      disabled={mode === 'view'}
                    />
                    <span className="checkmark"></span>
                    No additional cost required
                  </label>
                )}
              />
            </div>

            <div className="form-group">
              <Controller
                name="requires_additional_effort"
                control={control}
                render={({ field }) => (
                  <label className="checkbox-label">
                    <input
                      {...field}
                      type="checkbox"
                      checked={field.value}
                      disabled={mode === 'view'}
                    />
                    <span className="checkmark"></span>
                    Requires additional effort
                  </label>
                )}
              />
            </div>

            {requiresAdditionalEffort && (
              <div className="form-group">
                <label htmlFor="estimated_time">
                  Estimated Time (Days)
                </label>
                <Controller
                  name="estimated_time"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="number"
                      id="estimated_time"
                      min="0"
                      className="form-control"
                      disabled={mode === 'view'}
                    />
                  )}
                />
              </div>
            )}

            {!noAdditionalCost && (
              <div className="form-group">
                <label htmlFor="estimated_cost">
                  Estimated Additional Cost ($)
                </label>
                <Controller
                  name="estimated_cost"
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="number"
                      id="estimated_cost"
                      step="0.01"
                      min="0"
                      className="form-control"
                      disabled={mode === 'view'}
                    />
                  )}
                />
              </div>
            )}

            {changeRequest && (
              <div className="form-actions">
                <button
                  type="button"
                  onClick={handleSubmit(handleImpactAssessment)}
                  className="btn btn-primary"
                  disabled={formState.loading || mode === 'view'}
                >
                  {formState.loading ? 'Updating...' : 'Update Impact Assessment'}
                </button>
              </div>
            )}
          </section>
        )}

        {/* Client Decision Section */}
        {canMakeClientDecision && (
          <section className="form-section">
            <h3>Client Decision</h3>
            
            <div className="form-group">
              <label htmlFor="decision">Decision</label>
              <Controller
                name="decision"
                control={control}
                render={({ field }) => (
                  <select
                    {...field}
                    id="decision"
                    className="form-control"
                    disabled={mode === 'view'}
                  >
                    <option value="">Select decision...</option>
                    <option value="proceed">Proceed with Change</option>
                    <option value="defer">Defer Change</option>
                    <option value="withdraw">Withdraw Change</option>
                  </select>
                )}
              />
            </div>

            <div className="form-group">
              <label htmlFor="issues_to_resolve">
                Issues to Resolve (if applicable)
              </label>
              <Controller
                name="issues_to_resolve"
                control={control}
                render={({ field }) => (
                  <textarea
                    {...field}
                    id="issues_to_resolve"
                    rows={3}
                    className="form-control"
                    placeholder="Describe any issues that need to be resolved..."
                    disabled={mode === 'view'}
                  />
                )}
              />
            </div>

            {changeRequest && (
              <div className="form-actions">
                <button
                  type="button"
                  onClick={handleSubmit(handleClientDecision)}
                  className="btn btn-primary"
                  disabled={formState.loading || mode === 'view'}
                >
                  {formState.loading ? 'Recording...' : 'Record Client Decision'}
                </button>
              </div>
            )}
          </section>
        )}

        {/* Signature Section */}
        <section className="form-section">
          <h3>Digital Signature</h3>
          
          <div className="signature-container">
            <div className="signature-pad-container">
              <SignaturePad
                canvasProps={{
                  className: 'signature-canvas',
                  width: 400,
                  height: 200,
                }}
                ref={(ref) => { signaturePadRef = ref; }}
              />
              <div className="signature-actions">
                <button
                  type="button"
                  onClick={() => signaturePadRef?.current?.clear()}
                  className="btn btn-secondary btn-sm"
                  disabled={mode === 'view'}
                >
                  Clear
                </button>
                <button
                  type="button"
                  onClick={() => handleSignatureCapture(
                    user?.role?.codename === 'client_contact' ? 'clientSignature' : 'providerSignature',
                    signaturePadRef
                  )}
                  className="btn btn-primary btn-sm"
                  disabled={mode === 'view'}
                >
                  Capture Signature
                </button>
              </div>
            </div>

            {changeRequest && (
              <div className="form-actions">
                <button
                  type="button"
                  onClick={handleSignatureSubmit}
                  className="btn btn-primary"
                  disabled={formState.loading || mode === 'view'}
                >
                  {formState.loading ? 'Signing...' : 'Sign Document'}
                </button>
              </div>
            )}
          </div>
        </section>

        {/* Form Actions */}
        {mode !== 'view' && (
          <div className="form-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={formState.loading || isSubmitting}
            >
              {formState.loading || isSubmitting ? 'Saving...' : 'Save Change Request'}
            </button>
            
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="btn btn-secondary"
              disabled={formState.loading}
            >
              Cancel
            </button>
          </div>
        )}

        {/* PDF Generation */}
        {changeRequest && canManageChangeRequests && (
          <div className="form-actions">
            <button
              type="button"
              onClick={handleGeneratePDF}
              className="btn btn-outline-primary"
              disabled={formState.loading}
            >
              {formState.loading ? 'Generating...' : 'Generate PDF'}
            </button>
          </div>
        )}
      </form>
    </div>
  );
};

export default ChangeRequestForm;
