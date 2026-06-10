import { useState, useCallback } from 'react';
import { app } from '@microsoft/teams-js';

/**
 * useTeamsContext — Extracts session_id from the Teams meeting context.
 *
 * Resolution order:
 *   1. ?session_id= URL query param (works for localhost / direct links)
 *   2. ?context={...session_id...} URL query param (email-style deep link)
 *   3. Teams SDK context → page.subPageId (set via subEntityId at config time)
 *   4. Teams SDK context → meeting join URL params (the context param in the join link)
 */
export function useTeamsContext() {
  const [sessionId, setSessionId] = useState(null);
  const [isTeams, setIsTeams] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const resolveSessionId = useCallback(async () => {
    setLoading(true);
    setError(null);
    let resolvedId = null;

    try {
      // ── 1. Check URL query params first (always works, standalone & Teams) ──
      const params = new URLSearchParams(window.location.search);
      let sid = params.get('session_id');

      // ── 2. Check ?context={"session_id":"..."} (email deep-link format) ──
      if (!sid) {
        const ctxParam = params.get('context');
        if (ctxParam) {
          try {
            const parsed = JSON.parse(decodeURIComponent(ctxParam));
            sid = parsed.session_id || parsed.sessionId;
          } catch {
            // Not valid JSON — ignore
          }
        }
      }

      // ── 3. Try Teams SDK context ──
      try {
        await app.initialize();
        setIsTeams(true);
        console.log('[useTeamsContext] Teams SDK initialized');

        const context = await app.getContext();
        console.log('[useTeamsContext] Teams context:', JSON.stringify(context, null, 2));

        // subPageId is populated from subEntityId set during config
        if (!sid && context?.page?.subPageId) {
          sid = context.page.subPageId;
        }

        // Also try the meeting join URL for a context param
        if (!sid && context?.meeting?.id) {
          console.log('[useTeamsContext] Meeting ID:', context.meeting.id);
        }
      } catch (teamsErr) {
        console.log('[useTeamsContext] Not running inside Teams:', teamsErr.message);
        // Not inside Teams — that's fine, fall through to URL params
      }

      if (sid) {
        console.log('[useTeamsContext] Resolved session_id:', sid);
        setSessionId(sid);
        resolvedId = sid;
      } else {
        setError('No session ID found. Please use the interview link from your email.');
      }
    } catch (err) {
      console.error('[useTeamsContext] Error resolving session:', err);
      setError(err.message || 'Failed to resolve session context.');
    } finally {
      setLoading(false);
    }

    return resolvedId;
  }, []);

  return { sessionId, isTeams, loading, error, resolveSessionId };
}
