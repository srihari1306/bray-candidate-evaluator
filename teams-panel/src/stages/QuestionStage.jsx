import { useState, useEffect, useRef } from 'react';
import MicButton from '../components/MicButton';
import ProgressDots from '../components/ProgressDots';
import { useAzureSpeech } from '../hooks/useAzureSpeech';

/**
 * Question stage — displays one question at a time with speech recording.
 * Shows live transcript, mic button, and Done button.
 */
export default function QuestionStage({ question, index, onDone }) {
  const {
    transcript,
    interimTranscript,
    isRecording,
    error: speechError,
    startRecognition,
    stopRecognition,
    resetTranscript,
  } = useAzureSpeech();

  const [hasStartedRecording, setHasStartedRecording] = useState(false);
  const [localTranscript, setLocalTranscript] = useState('');
  const [fullscreenWarning, setFullscreenWarning] = useState(false);

  // Collect browser focus events across questions
  const focusEventsRef = useRef([]);

  useEffect(() => {
    // Request fullscreen when question stage starts
    const requestFS = async () => {
      try {
        if (document.documentElement.requestFullscreen) {
          await document.documentElement.requestFullscreen();
        }
      } catch (err) {
        console.warn('Fullscreen request failed:', err);
        // Don't block interview if fullscreen is unavailable
      }
    };
    requestFS();

    // Detect fullscreen exit
    const handleFullscreenChange = () => {
      if (!document.fullscreenElement) {
        // They exited fullscreen
        focusEventsRef.current.push({
          type: 'fullscreen_exit',
          timestamp: new Date().toISOString()
        });
        setFullscreenWarning(true);
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      // Exit fullscreen when leaving question stage
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }
    };
  }, []);

  useEffect(() => {
    const onBlur = () => focusEventsRef.current.push({ type: 'blur', timestamp: new Date().toISOString() });
    const onFocus = () => focusEventsRef.current.push({ type: 'focus', timestamp: new Date().toISOString() });
    const onVisibility = () => focusEventsRef.current.push({ type: document.hidden ? 'tab_hidden' : 'tab_visible', timestamp: new Date().toISOString() });

    window.addEventListener('blur', onBlur);
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, []);

  // Sync hook transcript to local state
  useEffect(() => {
    if (transcript) {
      setLocalTranscript(transcript);
    }
  }, [transcript]);

  // Reset when question changes
  useEffect(() => {
    resetTranscript();
    setHasStartedRecording(false);
    setLocalTranscript('');
  }, [index, resetTranscript]);

  const handleMicClick = async () => {
    if (isRecording) {
      stopRecognition();
    } else {
      setHasStartedRecording(true);
      await startRecognition();
    }
  };

  const handleDone = () => {
    if (isRecording) {
      stopRecognition();
    }
    // Pass local transcript and the current accumulated focus events
    onDone(localTranscript, focusEventsRef.current);
  };

  const hasTranscript = localTranscript.trim().length > 0;

  return (
    <>
      {fullscreenWarning && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.95)',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '24px',
          padding: '40px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '48px' }}>⚠️</div>
          <h2 style={{ color: '#ff4444', fontSize: '24px', margin: 0 }}>
            Fullscreen Mode Exited
          </h2>
          <p style={{ color: '#cccccc', fontSize: '16px', maxWidth: '480px', margin: 0 }}>
            You have exited fullscreen mode. This has been flagged and recorded.
            Please return to fullscreen to continue your interview.
          </p>
          <p style={{ color: '#888888', fontSize: '13px', margin: 0 }}>
            Repeated exits will negatively impact your proctoring score.
          </p>
          <button
            onClick={async () => {
              try {
                if (document.documentElement.requestFullscreen) {
                  await document.documentElement.requestFullscreen();
                }
                setFullscreenWarning(false);
              } catch (err) {
                console.warn('Could not re-enter fullscreen:', err);
                // Strict enforcement: do not dismiss warning if fullscreen fails
              }
            }}
            style={{
              padding: '14px 32px',
              backgroundColor: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              cursor: 'pointer',
              fontWeight: '600'
            }}
          >
            Return to Fullscreen
          </button>
        </div>
      )}
      <div className="stage-container">
        <ProgressDots currentIndex={index} totalQuestions={3} />

      <div className="question-card">
        <div className="question-label">Question {index + 1} of 3</div>
        <h2 className="question-text">{question}</h2>
      </div>

      <div className="recording-section">
        <p className="recording-instruction">
          {!hasStartedRecording
            ? 'Click the microphone button when you\'re ready to answer.'
            : isRecording
            ? 'Speak your answer clearly. Click the button again to pause.'
            : 'Click the microphone to continue recording, or Done to submit.'}
        </p>

        <MicButton
          isRecording={isRecording}
          onClick={handleMicClick}
          disabled={false}
        />

        {isRecording && (
          <div className="recording-indicator">
            <span className="recording-dot" />
            Recording...
          </div>
        )}
      </div>

      {/* Editable transcript text area */}
      <div className="transcript-container">
        <div className="transcript-label">Your Answer (edit or type below):</div>
        <textarea
          className="transcript-textarea"
          value={isRecording && interimTranscript ? `${localTranscript} ${interimTranscript}` : localTranscript}
          onChange={(e) => setLocalTranscript(e.target.value)}
          placeholder="Speak your answer, or type it directly here..."
          rows={5}
          style={{
            width: '100%',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '12px',
            color: '#fff',
            padding: '16px',
            fontSize: '14px',
            lineHeight: '1.6',
            fontFamily: 'inherit',
            resize: 'vertical',
            outline: 'none',
            marginTop: '8px',
            transition: 'border-color 0.2s',
          }}
        />
      </div>

      {/* Error display */}
      {speechError && (
        <div className="error-message">
          ⚠️ {speechError}
          <button
            className="retry-button"
            onClick={() => {
              resetTranscript();
              startRecognition();
            }}
          >
            Retry
          </button>
        </div>
      )}

      <button
        className={`primary-button ${hasTranscript ? 'ready' : 'disabled'}`}
        onClick={handleDone}
        disabled={!hasTranscript}
      >
        {hasTranscript ? 'Done — Next Question' : 'Record or type an answer first'}
      </button>
      </div>
    </>
  );
}
