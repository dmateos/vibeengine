import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../utils/api';

interface ExecutionState {
  status: 'idle' | 'starting' | 'running' | 'completed' | 'error' | 'not_found';
  currentNodeId: string | null;
  completedNodes: string[];
  errorNodes: string[];
  trace: any[];
  steps: number;
  final: any;
  error: string | null;
  timestamp?: number;
}

interface UsePollingReturn {
  state: ExecutionState;
  startExecution: (nodes: any[], edges: any[], context?: any, startNodeId?: string, workflowId?: number, token?: string | null) => Promise<void>;
  stopPolling: () => void;
  isPolling: boolean;
}

const POLL_INTERVAL = 500; // 500ms

export function usePolling(): UsePollingReturn {
  const [state, setState] = useState<ExecutionState>({
    status: 'idle',
    currentNodeId: null,
    completedNodes: [],
    errorNodes: [],
    trace: [],
    steps: 0,
    final: null,
    error: null,
  });

  const [isPolling, setIsPolling] = useState(false);
  const intervalRef = useRef<number | null>(null);
  const executionIdRef = useRef<string | null>(null);

  // Poll for execution status
  const pollStatus = useCallback(async (executionId: string, token?: string | null) => {
    try {
      const headers: HeadersInit = {};
      if (token) {
        headers['Authorization'] = `Token ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/execution/${executionId}/status/`, { headers });

      if (!response.ok) {
        if (response.status === 404) {
          setState(prev => ({
            ...prev,
            status: 'not_found',
            error: 'Execution not found or expired',
          }));
          return false; // Stop polling
        }
        throw new Error('Failed to fetch execution status');
      }

      const data = await response.json();

      setState({
        status: data.status,
        currentNodeId: data.currentNodeId || null,
        completedNodes: data.completedNodes || [],
        errorNodes: data.errorNodes || [],
        trace: data.trace || [],
        steps: data.steps || 0,
        final: data.final || null,
        error: data.error || null,
        timestamp: data.timestamp,
      });

      // Stop polling if completed or error
      if (data.status === 'completed' || data.status === 'error') {
        return false;
      }

      return true; // Continue polling
    } catch (error) {
      console.error('Error polling execution status:', error);
      setState(prev => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
      }));
      return false; // Stop polling on error
    }
  }, []);

  // Start polling
  const startPolling = useCallback((executionId: string, token?: string | null) => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    setIsPolling(true);

    intervalRef.current = setInterval(async () => {
      const shouldContinue = await pollStatus(executionId, token);

      if (!shouldContinue) {
        stopPolling();
      }
    }, POLL_INTERVAL);

    // Poll immediately
    pollStatus(executionId, token);
  }, [pollStatus]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Start workflow execution
  const startExecution = useCallback(async (
    nodes: any[],
    edges: any[],
    context?: any,
    startNodeId?: string,
    workflowId?: number,
    token?: string | null
  ) => {
    try {
      setState({
        status: 'starting',
        currentNodeId: null,
        completedNodes: [],
        errorNodes: [],
        trace: [],
        steps: 0,
        final: null,
        error: null,
      });

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Token ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/execute-workflow-async/`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          nodes,
          edges,
          context,
          startNodeId,
          workflowId,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to start execution');
      }

      const data = await response.json();
      executionIdRef.current = data.executionId;

      // Start polling for status
      startPolling(data.executionId, token);
    } catch (error) {
      console.error('Error starting execution:', error);
      setState(prev => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
      }));
    }
  }, [startPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    state,
    startExecution,
    stopPolling,
    isPolling,
  };
}
