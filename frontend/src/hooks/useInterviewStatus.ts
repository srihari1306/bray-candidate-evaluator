/**
 * Polling hook for interview status updates.
 * Polls GET /interview/results/{session_id} every 5 seconds
 * until status becomes 'completed' or 'failed'.
 */
import { useState, useEffect, useCallback } from 'react';
import interviewApi from '../services/interviewApi';
import type { InterviewSession, InterviewStatusType } from '../types';

export function useInterviewStatus(
  sessionId: string | null,
  initialStatus: InterviewStatusType = 'none',
  evaluationId?: string
) {
  const [status, setStatus] = useState<InterviewStatusType>(initialStatus);
  const [results, setResults] = useState<InterviewSession | null>(null);

  const fetchResults = useCallback(async () => {
    if (!sessionId) return;
    try {
      const response = await interviewApi.getResults(sessionId, evaluationId);
      const data = response.data;
      setStatus(data.status as InterviewStatusType);
      if (data.status === 'completed') {
        setResults(data);
      }
    } catch (err) {
      console.error('Failed to fetch interview results:', err);
    }
  }, [sessionId, evaluationId]);

  // Sync initialStatus from outside immediately
  useEffect(() => {
    setStatus(initialStatus);
  }, [initialStatus]);

  // Fetch results once on mount/load if the session is already completed or failed
  useEffect(() => {
    if (sessionId && (initialStatus === 'completed' || initialStatus === 'failed') && !results) {
      fetchResults();
    }
  }, [sessionId, initialStatus, results, fetchResults]);

  useEffect(() => {
    if (!sessionId || status === 'completed' || status === 'failed' || status === 'none') {
      return;
    }

    // Skip polling if the initial status is already completed or failed
    if (initialStatus === 'completed' || initialStatus === 'failed') {
      return;
    }

    // Only start polling if the initial status is scheduled or in_progress
    if (initialStatus !== 'scheduled' && initialStatus !== 'in_progress') {
      return;
    }

    // Fetch immediately
    fetchResults();

    // Then poll every 5 seconds
    const interval = setInterval(fetchResults, 5000);
    return () => clearInterval(interval);
  }, [sessionId, status, initialStatus, fetchResults]);

  return { status, results, setStatus, setResults };
}
