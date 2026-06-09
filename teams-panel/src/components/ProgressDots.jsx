/**
 * Progress dots showing Q1, Q2, Q3 status.
 * Filled = completed, active = current, empty = upcoming.
 */
export default function ProgressDots({ currentIndex, totalQuestions = 3 }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 12,
      margin: '16px 0',
    }}>
      {Array.from({ length: totalQuestions }, (_, i) => {
        const isCompleted = i < currentIndex;
        const isActive = i === currentIndex;

        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 6,
            }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 14,
                  fontWeight: 700,
                  transition: 'all 0.4s ease',
                  background: isCompleted
                    ? 'linear-gradient(135deg, #22c55e, #16a34a)'
                    : isActive
                    ? 'linear-gradient(135deg, #667eea, #4f46e5)'
                    : 'rgba(255,255,255,0.08)',
                  color: isCompleted || isActive ? '#fff' : 'rgba(255,255,255,0.3)',
                  border: isActive
                    ? '2px solid rgba(102,126,234,0.5)'
                    : '2px solid transparent',
                  boxShadow: isActive
                    ? '0 0 0 4px rgba(102,126,234,0.15)'
                    : 'none',
                }}
              >
                {isCompleted ? '✓' : `Q${i + 1}`}
              </div>
              <span style={{
                fontSize: 11,
                fontWeight: 500,
                color: isActive ? '#667eea' : 'rgba(255,255,255,0.4)',
                textTransform: 'uppercase',
                letterSpacing: 0.5,
              }}>
                {isCompleted ? 'Done' : isActive ? 'Current' : 'Next'}
              </span>
            </div>
            {i < totalQuestions - 1 && (
              <div style={{
                width: 40,
                height: 2,
                background: isCompleted
                  ? 'linear-gradient(90deg, #22c55e, #16a34a)'
                  : 'rgba(255,255,255,0.1)',
                borderRadius: 1,
                marginBottom: 20,
              }} />
            )}
          </div>
        );
      })}
    </div>
  );
}
