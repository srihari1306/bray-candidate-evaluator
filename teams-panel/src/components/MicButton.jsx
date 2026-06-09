import { useState } from 'react';

/**
 * Animated mic button for speech recording.
 * Pulses when recording, solid when idle.
 */
export default function MicButton({ isRecording, onClick, disabled }) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        width: 80,
        height: 80,
        borderRadius: '50%',
        border: 'none',
        cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: isRecording
          ? 'linear-gradient(135deg, #ef4444, #dc2626)'
          : disabled
          ? '#374151'
          : isHovered
          ? 'linear-gradient(135deg, #3b82f6, #2563eb)'
          : 'linear-gradient(135deg, #667eea, #4f46e5)',
        boxShadow: isRecording
          ? '0 0 0 8px rgba(239,68,68,0.2), 0 0 0 16px rgba(239,68,68,0.1)'
          : isHovered && !disabled
          ? '0 0 0 6px rgba(102,126,234,0.3)'
          : '0 4px 20px rgba(0,0,0,0.3)',
        transition: 'all 0.3s ease',
        animation: isRecording ? 'pulse-mic 1.5s ease-in-out infinite' : 'none',
        opacity: disabled ? 0.4 : 1,
        position: 'relative',
      }}
    >
      <svg
        width="32"
        height="32"
        viewBox="0 0 24 24"
        fill="none"
        stroke="white"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {isRecording ? (
          // Stop icon (square)
          <rect x="6" y="6" width="12" height="12" rx="2" fill="white" stroke="none" />
        ) : (
          // Mic icon
          <>
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" fill="white" stroke="none" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </>
        )}
      </svg>
    </button>
  );
}
