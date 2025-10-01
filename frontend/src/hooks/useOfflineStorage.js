import { useState, useEffect, useCallback } from 'react';

/**
 * Custom hook for offline storage and synchronization
 * Provides local storage capabilities with online/offline detection
 */
export const useOfflineStorage = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [storage, setStorage] = useState({});

  // Listen for online/offline events
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Load data from localStorage
  const loadFromStorage = useCallback((key) => {
    try {
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Failed to load from localStorage:', error);
      return null;
    }
  }, []);

  // Save data to localStorage
  const saveToStorage = useCallback((key, data) => {
    try {
      if (data === null) {
        localStorage.removeItem(key);
      } else {
        localStorage.setItem(key, JSON.stringify(data));
      }
      return true;
    } catch (error) {
      console.error('Failed to save to localStorage:', error);
      return false;
    }
  }, []);

  // Save data offline
  const saveOffline = useCallback(async (key, data) => {
    const success = saveToStorage(key, data);
    if (success) {
      setStorage(prev => ({ ...prev, [key]: data }));
    }
    return success;
  }, [saveToStorage]);

  // Sync offline data
  const syncOffline = useCallback(async (key) => {
    const data = loadFromStorage(key);
    if (data) {
      setStorage(prev => ({ ...prev, [key]: data }));
    }
    return data;
  }, [loadFromStorage]);

  // Clear offline data
  const clearOffline = useCallback((key) => {
    saveToStorage(key, null);
    setStorage(prev => {
      const newStorage = { ...prev };
      delete newStorage[key];
      return newStorage;
    });
  }, [saveToStorage]);

  // Get all offline keys
  const getOfflineKeys = useCallback(() => {
    const keys = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith('client_intake_') || key.startsWith('file_queue_'))) {
        keys.push(key);
      }
    }
    return keys;
  }, []);

  // File queue management
  const addFileToQueue = useCallback(async (file, projectId, description = '') => {
    const queueKey = `file_queue_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const fileData = {
      id: queueKey,
      file: {
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified,
        // Store file content as base64 for offline storage
        content: await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result);
          reader.readAsDataURL(file);
        })
      },
      projectId,
      description,
      timestamp: new Date().toISOString(),
      status: 'pending'
    };

    const success = saveToStorage(queueKey, fileData);
    if (success) {
      setStorage(prev => ({ ...prev, [queueKey]: fileData }));
    }
    return success;
  }, [saveToStorage]);

  const getFileQueue = useCallback(() => {
    const queueItems = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('file_queue_')) {
        const data = loadFromStorage(key);
        if (data && data.status === 'pending') {
          queueItems.push(data);
        }
      }
    }
    return queueItems.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  }, [loadFromStorage]);

  const removeFileFromQueue = useCallback((queueId) => {
    clearOffline(queueId);
  }, [clearOffline]);

  const updateFileQueueStatus = useCallback((queueId, status, error = null) => {
    const data = loadFromStorage(queueId);
    if (data) {
      data.status = status;
      if (error) {
        data.error = error;
      }
      saveToStorage(queueId, data);
      setStorage(prev => ({ ...prev, [queueId]: data }));
    }
  }, [loadFromStorage, saveToStorage]);

  return {
    isOnline,
    saveOffline,
    syncOffline,
    clearOffline,
    getOfflineKeys,
    storage,
    // File queue methods
    addFileToQueue,
    getFileQueue,
    removeFileFromQueue,
    updateFileQueueStatus,
  };
};
