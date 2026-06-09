import { useState, useEffect } from 'react';
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
    onDone(localTranscript);
  };

  const hasTranscript = localTranscript.trim().length > 0;

  return (
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
  );
}
