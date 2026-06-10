import { useEffect, useState } from 'react';
import { app, pages } from '@microsoft/teams-js';

/**
 * Teams Configuration Page
 *
 * Loaded when the app is added to a meeting via the side-panel "+" button.
 * Registers the save handler so Teams knows the content URL to render.
 * Uses window.location.origin dynamically — works across localhost, devtunnels,
 * and production without hardcoded URLs.
 */
export default function Config() {
  const [initialized, setInitialized] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    app
      .initialize()
      .then(() => {
        console.log('[Config] Teams SDK initialized');
        setInitialized(true);

        // Enable the Save button in the Teams configuration dialog
        pages.config.setValidityState(true);

        // Register the save handler — called when the user clicks Save
        pages.config.registerOnSaveHandler((saveEvent) => {
          const origin = window.location.origin;
          console.log('[Config] Saving config with contentUrl:', origin);

          pages.config.setConfig({
            suggestedDisplayName: 'Smart Interviewer',
            entityId: 'smart-interviewer',
            contentUrl: `${origin}/`,
            websiteUrl: `${origin}/`,
          });

          saveEvent.notifySuccess();
        });
      })
      .catch((err) => {
        console.error('[Config] Teams SDK initialization failed:', err);
        setError(err.message || 'Failed to initialize Teams SDK');
      });
  }, []);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        padding: '20px',
        textAlign: 'center',
        fontFamily:
          'Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif',
        backgroundColor: '#f3f2f1',
        color: '#323130',
      }}
    >
      <div
        style={{
          maxWidth: '400px',
          padding: '30px',
          borderRadius: '8px',
          backgroundColor: '#ffffff',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        }}
      >
        <h2 style={{ color: '#1F4E79', margin: '0 0 15px 0' }}>
          Smart Interviewer
        </h2>

        {error ? (
          <p style={{ color: '#d13438', fontSize: '14px', lineHeight: '1.5' }}>
            {error}
          </p>
        ) : (
          <p
            style={{
              margin: '0 0 20px 0',
              fontSize: '15px',
              lineHeight: '1.5',
            }}
          >
            {initialized
              ? 'Click the Save button below to add the Smart Interviewer panel to this meeting.'
              : 'Initializing Teams SDK…'}
          </p>
        )}
      </div>
    </div>
  );
}
