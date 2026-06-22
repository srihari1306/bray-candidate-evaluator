import { useState } from 'react';

/**
 * Setup stage — instructs candidate to enable camera, mic, and screen share.
 * Done button enables only when all three items are checked.
 */
export default function SetupStage({ onDone, candidateName }) {
  const [checks, setChecks] = useState({
    camera: false,
    microphone: false,
    screen: false,
    fullscreen: false,
    consent: false,
  });

  const allChecked = checks.camera && checks.microphone && checks.screen && checks.fullscreen && checks.consent;

  const toggle = (key) => {
    setChecks((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const items = [
    {
      key: 'camera',
      icon: '📹',
      title: 'Enable Camera',
      description: 'Turn on your camera so the recording captures your video.',
    },
    {
      key: 'microphone',
      icon: '🎤',
      title: 'Unmute Microphone',
      description: 'Ensure your microphone is unmuted and working.',
    },
    {
      key: 'screen',
      icon: '🖥️',
      title: 'Share Your Screen',
      description: 'Be ready to share your entire screen when prompted.',
    },
    {
      key: 'fullscreen',
      icon: '⛶',
      title: 'Fullscreen Mode',
      description: 'Your interview will run in fullscreen mode — do not exit during the session.',
    },
    {
      key: 'consent',
      icon: '✅',
      title: 'Recording Consent',
      description: 'I consent to my camera, microphone, and screen being recorded for evaluation purposes.',
    },
  ];

  return (
    <div className="stage-container">
      <div className="stage-header">
        <div className="welcome-badge">Welcome</div>
        <h1 className="stage-title">
          Hello, {candidateName || 'Candidate'}! 👋
        </h1>
        <p className="stage-subtitle">
          Before we begin your interview, please complete the setup checklist below.
        </p>
      </div>

      <div className="checklist-container">
        {items.map(({ key, icon, title, description }) => (
          <div
            key={key}
            className={`checklist-item ${checks[key] ? 'checked' : ''}`}
            onClick={() => toggle(key)}
          >
            <div className="checklist-checkbox">
              {checks[key] ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M20 6L9 17L4 12"
                    stroke="#22c55e"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : (
                <div className="checkbox-empty" />
              )}
            </div>
            <div className="checklist-icon">{icon}</div>
            <div className="checklist-text">
              <div className="checklist-title">{title}</div>
              <div className="checklist-description">{description}</div>
            </div>
          </div>
        ))}
      </div>

      <button
        className={`primary-button ${allChecked ? 'ready' : 'disabled'}`}
        onClick={onDone}
        disabled={!allChecked}
      >
        {allChecked ? "I'm Ready — Start Interview" : 'Complete All Steps Above'}
      </button>

      {!allChecked && (
        <p className="hint-text">
          Please check all items above to proceed.
        </p>
      )}
    </div>
  );
}
