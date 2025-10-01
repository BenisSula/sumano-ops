import { useState, useCallback } from 'react';

/**
 * Custom hook for API client operations
 * Handles authentication, error handling, and request management
 */
export const useApiClient = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Base API configuration
  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:4002/api';
  
  // Get authentication token
  const getAuthToken = useCallback(() => {
    return localStorage.getItem('auth_token');
  }, []);

  // Make authenticated API request
  const makeRequest = useCallback(async (url, options = {}) => {
    setIsLoading(true);
    setError(null);

    try {
      const token = getAuthToken();
      const config = {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
          ...options.headers,
        },
      };

      const response = await fetch(`${API_BASE_URL}${url}`, config);
      
      if (!response.ok) {
        if (response.status === 401) {
          // Handle unauthorized access
          localStorage.removeItem('auth_token');
          throw new Error('Authentication required. Please log in again.');
        } else if (response.status === 403) {
          throw new Error('Access denied. You do not have permission to perform this action.');
        } else if (response.status >= 500) {
          throw new Error('Server error. Please try again later.');
        } else {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Request failed with status ${response.status}`);
        }
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      } else {
        return response;
      }
    } catch (err) {
      const errorMessage = err.message || 'An unexpected error occurred';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [API_BASE_URL, getAuthToken]);

  // Submit client intake form
  const submitClientIntake = useCallback(async (formData) => {
    // Prepare organization data
    const organizationData = {
      name: formData.school_name,
      organization_type: 'educational',
      email: formData.email,
    };

    // Prepare client data
    const clientData = {
      organization: organizationData,
      school_name: formData.school_name,
      address: formData.address,
      contact_person: formData.contact_person,
      role_position: formData.role_position,
      phone_whatsapp: formData.phone_whatsapp,
      email: formData.email,
      current_website: formData.current_website,
      number_of_students: formData.number_of_students ? parseInt(formData.number_of_students) : null,
      number_of_staff: formData.number_of_staff ? parseInt(formData.number_of_staff) : null,
      project_type: formData.project_type,
      project_purpose: formData.project_purpose,
      pilot_scope_features: formData.pilot_scope_features,
      pilot_start_date: formData.pilot_start_date?.toISOString().split('T')[0],
      pilot_end_date: formData.pilot_end_date?.toISOString().split('T')[0],
      timeline_preference: formData.timeline_preference,
      design_preferences: formData.design_preferences,
      logo_colors: formData.logo_colors,
      content_availability: formData.content_availability,
      maintenance_plan: formData.maintenance_plan,
      token_commitment_fee: formData.token_commitment_fee ? parseFloat(formData.token_commitment_fee) : null,
      additional_notes: formData.additional_notes,
      acknowledgment: formData.acknowledgment,
    };

    return await makeRequest('/clients/', {
      method: 'POST',
      body: JSON.stringify(clientData),
    });
  }, [makeRequest]);

  // Generate PDF for client intake
  const generatePDF = useCallback(async (formData) => {
    // First, create or get the client
    const clientResponse = await submitClientIntake(formData);
    const clientId = clientResponse.id;

    // Generate PDF using the client ID
    const pdfResponse = await makeRequest(`/clients/${clientId}/generate-intake-pdf/`, {
      method: 'POST',
    });

    // Return the PDF URL
    return pdfResponse.document.pdf_url;
  }, [makeRequest, submitClientIntake]);

  // Get client list
  const getClients = useCallback(async (params = {}) => {
    const queryParams = new URLSearchParams(params);
    const url = `/clients/${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return await makeRequest(url);
  }, [makeRequest]);

  // Get client by ID
  const getClient = useCallback(async (clientId) => {
    return await makeRequest(`/clients/${clientId}/`);
  }, [makeRequest]);

  // Update client
  const updateClient = useCallback(async (clientId, updateData) => {
    return await makeRequest(`/clients/${clientId}/`, {
      method: 'PATCH',
      body: JSON.stringify(updateData),
    });
  }, [makeRequest]);

  // Get intake statistics
  const getIntakeStatistics = useCallback(async () => {
    return await makeRequest('/clients/intake-statistics/');
  }, [makeRequest]);

  // Complete client intake
  const completeClientIntake = useCallback(async (clientId, intakeData) => {
    return await makeRequest(`/clients/${clientId}/complete-intake/`, {
      method: 'POST',
      body: JSON.stringify(intakeData),
    });
  }, [makeRequest]);

  // Download PDF
  const downloadPDF = useCallback(async (documentId) => {
    const response = await makeRequest(`/documents/${documentId}/pdf/`);
    
    // Create blob and download link
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `client-intake-${documentId}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }, [makeRequest]);

  // Pilot Acceptance API methods
  const submitPilotAcceptance = useCallback(async (acceptanceData) => {
    return makeRequest('/pilot-acceptance/', {
      method: 'POST',
      body: JSON.stringify(acceptanceData),
    });
  }, [makeRequest]);

  const getPilotAcceptances = useCallback(async () => {
    return makeRequest('/pilot-acceptance/');
  }, [makeRequest]);

  const getPilotAcceptance = useCallback(async (acceptanceId) => {
    return makeRequest(`/pilot-acceptance/${acceptanceId}/`);
  }, [makeRequest]);

  const updatePilotAcceptance = useCallback(async (acceptanceId, updateData) => {
    return makeRequest(`/pilot-acceptance/${acceptanceId}/`, {
      method: 'PATCH',
      body: JSON.stringify(updateData),
    });
  }, [makeRequest]);

  const signPilotAcceptance = useCallback(async (acceptanceId, signatureData) => {
    return makeRequest(`/pilot-acceptance/${acceptanceId}/sign_acceptance/`, {
      method: 'POST',
      body: JSON.stringify(signatureData),
    });
  }, [makeRequest]);

  const generateAcceptancePDF = useCallback(async (acceptanceData) => {
    const response = await makeRequest('/pilot-acceptance/1/generate_certificate/', {
      method: 'POST',
    });
    
    if (response instanceof Blob) {
      const url = URL.createObjectURL(response);
      return url;
    }
    throw new Error('Failed to generate PDF');
  }, [makeRequest]);

  const getPilotAcceptanceStatistics = useCallback(async () => {
    return makeRequest('/pilot-acceptance/statistics/');
  }, [makeRequest]);

  const getPendingSignatures = useCallback(async () => {
    return makeRequest('/pilot-acceptance/pending_signatures/');
  }, [makeRequest]);

  // File Management API methods
  const uploadFile = useCallback(async (file, projectId, description = '') => {
    setIsLoading(true);
    setError(null);

    try {
      const token = getAuthToken();
      const formData = new FormData();
      formData.append('file', file);
      formData.append('project_id', projectId);
      if (description) {
        formData.append('description', description);
      }

      const response = await fetch(`${API_BASE_URL}/attachments/`, {
        method: 'POST',
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: formData,
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('auth_token');
          throw new Error('Authentication required. Please log in again.');
        } else if (response.status === 403) {
          throw new Error('Access denied. You do not have permission to upload files.');
        } else if (response.status >= 500) {
          throw new Error('Server error. Please try again later.');
        } else {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
        }
      }

      return await response.json();
    } catch (err) {
      const errorMessage = err.message || 'An unexpected error occurred during upload';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [API_BASE_URL, getAuthToken]);

  const getAttachments = useCallback(async (params = {}) => {
    const queryParams = new URLSearchParams(params);
    const url = `/attachments/${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return await makeRequest(url);
  }, [makeRequest]);

  const getAttachmentsByProject = useCallback(async (projectId) => {
    return await makeRequest(`/attachments/by_project/?project_id=${projectId}`);
  }, [makeRequest]);

  const downloadFile = useCallback(async (attachmentId) => {
    setIsLoading(true);
    setError(null);

    try {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/attachments/${attachmentId}/download/`, {
        method: 'GET',
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('auth_token');
          throw new Error('Authentication required. Please log in again.');
        } else if (response.status === 403) {
          throw new Error('Access denied. You do not have permission to download this file.');
        } else if (response.status === 404) {
          throw new Error('File not found.');
        } else {
          throw new Error(`Download failed with status ${response.status}`);
        }
      }

      const blob = await response.blob();
      return blob;
    } catch (err) {
      const errorMessage = err.message || 'An unexpected error occurred during download';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [API_BASE_URL, getAuthToken]);

  const deleteFile = useCallback(async (attachmentId) => {
    return await makeRequest(`/attachments/${attachmentId}/`, {
      method: 'DELETE',
    });
  }, [makeRequest]);

  const getMyUploads = useCallback(async () => {
    return await makeRequest('/attachments/my_uploads/');
  }, [makeRequest]);

  const getAttachmentStats = useCallback(async () => {
    return await makeRequest('/attachments/stats/');
  }, [makeRequest]);

  return {
    isLoading,
    error,
    submitClientIntake,
    generatePDF,
    getClients,
    getClient,
    updateClient,
    getIntakeStatistics,
    completeClientIntake,
    downloadPDF,
    // Pilot Acceptance methods
    submitPilotAcceptance,
    getPilotAcceptances,
    getPilotAcceptance,
    updatePilotAcceptance,
    signPilotAcceptance,
    generateAcceptancePDF,
    getPilotAcceptanceStatistics,
    getPendingSignatures,
    // File Management methods
    uploadFile,
    getAttachments,
    getAttachmentsByProject,
    downloadFile,
    deleteFile,
    getMyUploads,
    getAttachmentStats,
    makeRequest,
  };
};
