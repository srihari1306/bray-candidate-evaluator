import { useEffect, useState } from 'react';

/**
 * Goodbye stage — shown after all questions are answered.
 * Displays a thank-you message.
 */
export default function GoodbyeStage() {
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => {
    // Trigger confetti animation
    setTimeout(() => setShowConfetti(true), 300);
  }, []);

  return (
    <div className="stage-container goodbye-stage">
      <div className={`goodbye-icon ${showConfetti ? 'animate' : ''}`}>
        🎉
      </div>

      <h1 className="goodbye-title">Thank You!</h1>

      <p className="goodbye-message">
        Your interview is complete. Our team will review your responses
        and be in touch shortly.
      </p>

      <div className="goodbye-details">
        <div className="goodbye-detail-item">
          <span className="goodbye-detail-icon">✅</span>
          <span>All answers recorded</span>
        </div>
        <div className="goodbye-detail-item">
          <span className="goodbye-detail-icon">📹</span>
          <span>Session recording saved</span>
        </div>
        <div className="goodbye-detail-item">
          <span className="goodbye-detail-icon">🤖</span>
          <span>AI evaluation in progress</span>
        </div>
      </div>

      <p className="goodbye-footer">
        You may close this window now.
      </p>
    </div>
  );
}
