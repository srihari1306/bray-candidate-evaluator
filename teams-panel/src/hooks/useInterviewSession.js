import { useState, useCallback } from 'react';
import { getSession, submitAnswers } from '../api/sessionApi';

/**
 * Hook for managing the interview session lifecycle.
 * Handles loading session data, recording answers, and submitting results.
 */
export function useInterviewSession() {
  const [session, setSession] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadSession = useCallback(async (sessionId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSession(sessionId);
      setSession({
        id: data.session_id,
        candidateName: data.candidate_name,
        questions: data.questions,
        status: data.status,
      });
      setAnswers([]);
      return data;
    } catch (err) {
      const msg = `Failed to load session: ${err.message}`;
      setError(msg);
      console.error(msg, err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const recordAnswer = useCallback((questionIndex, transcript) => {
    setAnswers((prev) => {
      const updated = [...prev];
      updated[questionIndex] = {
        question_index: questionIndex,
        question_text: session?.questions?.[questionIndex] || '',
        transcript,
      };
      return updated;
    });
  }, [session]);

  const submitAllAnswers = useCallback(async (recordingBlobName = '', cameraBlobName = '', finalAnswers = null, focusEvents = []) => {
    if (!session) throw new Error('No session loaded');
    try {
      const result = await submitAnswers({
        session_id: session.id,
        answers: finalAnswers || answers,
        recording_blob_name: recordingBlobName,
        camera_blob_name: cameraBlobName,
        focus_events: focusEvents,
      });
      return result;
    } catch (err) {
      console.error('Failed to submit answers:', err);
      throw err;
    }
  }, [session, answers]);

  return {
    session,
    answers,
    loading,
    error,
    loadSession,
    recordAnswer,
    submitAllAnswers,
  };
}
