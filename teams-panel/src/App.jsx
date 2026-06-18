import { useState, useEffect, useCallback } from 'react';
import SetupStage from './stages/SetupStage';
import QuestionStage from './stages/QuestionStage';
import GoodbyeStage from './stages/GoodbyeStage';
import { useInterviewSession } from './hooks/useInterviewSession';
import { useMediaRecorder } from './hooks/useMediaRecorder';
import './App.css';

/**
 * Smart Interviewer — Main App (Stage Router)
 *
 * Stages: loading → setup → question (x3) → goodbye
 *
 * In standalone mode (outside Teams), session_id is read from URL query params.
 */
export default function App() {
  const [stage, setStage] = useState('loading');
  const [questionIndex, setQuestionIndex] = useState(0);
  const [loadError, setLoadError] = useState(null);

  const {
    session,
    answers,
    loading,
    error: sessionError,
    loadSession,
    recordAnswer,
    submitAllAnswers,
  } = useInterviewSession();

  const { startRecording, stopRecordingAndUpload } = useMediaRecorder();

  // Extract session_id from URL query params (standalone mode)
  useEffect(() => {
    const init = async () => {
      try {
        const params = new URLSearchParams(window.location.search);
        let sessionId = params.get('session_id');

        // Also try Teams-style context parameter
        if (!sessionId) {
          const context = params.get('context');
          if (context) {
            try {
              const parsed = JSON.parse(decodeURIComponent(context));
              sessionId = parsed.session_id;
            } catch {
              // Not valid JSON
            }
          }
        }

        if (!sessionId) {
          setLoadError(
            'No session ID found. Please use the interview link from your email.'
          );
          setStage('error');
          return;
        }

        await loadSession(sessionId);
        setStage('setup');
      } catch (err) {
        setLoadError(err.message || 'Failed to load interview session.');
        setStage('error');
      }
    };

    init();
  }, [loadSession]);

  const handleSetupDone = useCallback(async () => {
    // Start recording (screen + mic)
    await startRecording();
    setStage('question');
  }, [startRecording]);

  const handleAllDone = useCallback(async (lastTranscript, focusEvents = []) => {
    setStage('goodbye');

    try {
      // Stop recording and upload
      const { screenBlobName, cameraBlobName } = await stopRecordingAndUpload(session?.id) || {};

      // Construct the final list of answers synchronously, combining Q1/Q2 state with Q3 transcript
      const totalQuestions = session?.questions?.length || 3;
      const finalAnswers = [
        ...answers,
        {
          question_index: totalQuestions - 1,
          question_text: session?.questions?.[totalQuestions - 1] || '',
          transcript: lastTranscript,
        }
      ];

      // Submit answers to backend (triggers async evaluation)
      await submitAllAnswers(screenBlobName || '', cameraBlobName || '', finalAnswers, focusEvents);
    } catch (err) {
      console.error('Error during interview completion:', err);
      // Don't change stage — stay on goodbye
    }
  }, [session, answers, stopRecordingAndUpload, submitAllAnswers]);

  const handleAnswerDone = useCallback(
    (transcript, focusEvents = []) => {
      const totalQuestions = session?.questions?.length || 3;
      if (questionIndex < totalQuestions - 1) {
        recordAnswer(questionIndex, transcript);
        setQuestionIndex((i) => i + 1);
      } else {
        // Last question — skip recordAnswer state update to avoid race conditions.
        // Pass the final transcript directly to handleAllDone.
        handleAllDone(transcript, focusEvents);
      }
    },
    [questionIndex, recordAnswer, session, handleAllDone]
  );

  const handleRetry = () => {
    setStage('loading');
    setLoadError(null);
    window.location.reload();
  };

  // ─── Render ───

  if (stage === 'loading') {
    return (
      <div className="panel-container">
        <div className="loading-screen">
          <div className="loading-spinner" />
          <h2>Loading your interview...</h2>
          <p>Please wait while we prepare your session.</p>
        </div>
      </div>
    );
  }

  if (stage === 'error') {
    return (
      <div className="panel-container">
        <div className="error-screen">
          <div className="error-icon">⚠️</div>
          <h2>Unable to Load Interview</h2>
          <p>{loadError || sessionError || 'An unexpected error occurred.'}</p>
          <button className="primary-button ready" onClick={handleRetry}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div className="panel-logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5z" fill="#667eea" />
            <path d="M2 17l10 5 10-5" stroke="#667eea" strokeWidth="2" fill="none" />
            <path d="M2 12l10 5 10-5" stroke="#667eea" strokeWidth="2" fill="none" />
          </svg>
          <span>Smart Interview</span>
        </div>
        {session && (
          <div className="session-info">
            {session.candidateName}
          </div>
        )}
      </div>

      <div className="panel-content">
        {stage === 'setup' && (
          <SetupStage
            onDone={handleSetupDone}
            candidateName={session?.candidateName}
          />
        )}
        {stage === 'question' && session && (
          <QuestionStage
            question={session.questions[questionIndex]}
            index={questionIndex}
            onDone={handleAnswerDone}
          />
        )}
        {stage === 'goodbye' && <GoodbyeStage />}
      </div>
    </div>
  );
}
