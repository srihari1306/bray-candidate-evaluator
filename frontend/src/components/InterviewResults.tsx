/**
 * Interview results panel — per-question breakdown, scores, recording link.
 */
import { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Typography, Box, Divider, Chip, Paper, useTheme,
  LinearProgress, Skeleton, Grid, Link as MuiLink,
} from '@mui/material';
import type { InterviewSession } from '../types';

interface InterviewResultsProps {
  open: boolean;
  onClose: () => void;
  session: InterviewSession;
}

function getScoreColor(score: number): string {
  if (score >= 8) return '#22c55e';
  if (score >= 6) return '#3b82f6';
  if (score >= 4) return '#f59e0b';
  return '#ef4444';
}

export default function InterviewResults({ open, onClose, session }: InterviewResultsProps) {
  const theme = useTheme();

  // Fetch fresh SAS URLs every time the modal opens so links never expire
  const [freshUrls, setFreshUrls] = useState<{
    recording_sas_url: string;
    camera_sas_url: string;
  } | null>(null);
  const [urlsLoading, setUrlsLoading] = useState(false);

  useEffect(() => {
    if (!open || !session?.session_id) return;

    setUrlsLoading(true);
    setFreshUrls(null);

    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${baseUrl}/interview/results/${session.session_id}`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        setFreshUrls({
          recording_sas_url: data.recording_sas_url || '',
          camera_sas_url: data.camera_sas_url || '',
        });
      })
      .catch(err => {
        console.error('Failed to fetch fresh recording URLs:', err);
      })
      .finally(() => setUrlsLoading(false));
  }, [open, session?.session_id]);

  const screenUrl = freshUrls?.recording_sas_url || session.recording_sas_url;
  const cameraUrl = freshUrls?.camera_sas_url || session.camera_sas_url;

  const handleOverride = async (status: 'clean' | 'flagged') => {
    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/interview/proctoring/${session.session_id}/override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ override_status: status })
      });
      if (!res.ok) throw new Error('Override failed');
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert('Failed to override status');
    }
  };

  const handleDownloadTranscript = () => {
    const lines = session.answers.map(
      (a) => `Question ${a.question_index + 1}: ${a.question_text}\n\nAnswer: ${a.transcript}\n\nScore: ${a.score}/10\nReasoning: ${a.score_reasoning}\n`
    );
    const content = `Interview Transcript — ${session.candidate_name}\n${'═'.repeat(50)}\n\n${lines.join('\n' + '─'.repeat(50) + '\n\n')}\n${'═'.repeat(50)}\nFinal Score: ${session.final_score}/10`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `interview_${session.candidate_name.replace(/\s+/g, '_')}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h6" fontWeight={700}>Interview Results</Typography>
            <Typography variant="body2" color="text.secondary">
              {session.candidate_name}
            </Typography>
          </Box>
          <Box sx={{ textAlign: 'right' }}>
            <Typography
              variant="h3"
              fontWeight={800}
              sx={{ color: getScoreColor(session.final_score || 0), lineHeight: 1 }}
            >
              {session.final_score ?? '—'}
            </Typography>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>
              out of 10
            </Typography>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, pt: 1 }}>
          {session.answers.map((answer) => (
            <Paper
              key={answer.question_index}
              elevation={0}
              sx={{
                p: 2.5,
                bgcolor: theme.palette.action.hover,
                borderRadius: 2,
                border: `1px solid ${theme.palette.divider}`,
              }}
            >
              {/* Question Header */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                <Box>
                  <Chip
                    label={`Q${answer.question_index + 1}`}
                    size="small"
                    sx={{
                      fontWeight: 700,
                      bgcolor: `${getScoreColor(answer.score)}20`,
                      color: getScoreColor(answer.score),
                      mb: 1,
                    }}
                  />
                  <Typography variant="subtitle1" fontWeight={600}>
                    {answer.question_text}
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center', minWidth: 56 }}>
                  <Typography variant="h5" fontWeight={800} sx={{ color: getScoreColor(answer.score) }}>
                    {answer.score}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">/10</Typography>
                </Box>
              </Box>

              {/* Score Bar */}
              <LinearProgress
                variant="determinate"
                value={answer.score * 10}
                sx={{
                  height: 6,
                  borderRadius: 3,
                  bgcolor: `${getScoreColor(answer.score)}15`,
                  mb: 1.5,
                  '& .MuiLinearProgress-bar': {
                    bgcolor: getScoreColor(answer.score),
                    borderRadius: 3,
                  },
                }}
              />

              {/* Reasoning */}
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontStyle: 'italic' }}>
                💡 {answer.score_reasoning}
              </Typography>

              <Divider sx={{ my: 1.5 }} />

              {/* Transcript */}
              <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Candidate Response
              </Typography>
              <Typography variant="body2" sx={{ mt: 0.5, lineHeight: 1.7 }}>
                {answer.transcript || 'No response recorded.'}
              </Typography>
            </Paper>
          ))}

          {/* PROCTORING REPORT */}
          {session.proctoring_report && (
            <Paper elevation={0} sx={{ p: 2.5, bgcolor: theme.palette.background.paper, border: `2px solid ${session.proctoring_report.overall_risk === 'high' ? '#ef4444' : session.proctoring_report.overall_risk === 'medium' ? '#f59e0b' : '#22c55e'}`, borderRadius: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" fontWeight={700}>PROCTORING REPORT</Typography>
                <Chip 
                  label={`Risk Score: ${session.proctoring_report.risk_score}/100    ${session.proctoring_report.overall_risk === 'high' ? '🔴 HIGH RISK' : session.proctoring_report.overall_risk === 'medium' ? '🟡 MEDIUM RISK' : '🟢 LOW RISK'}`}
                  color={session.proctoring_report.overall_risk === 'high' ? 'error' : session.proctoring_report.overall_risk === 'medium' ? 'warning' : 'success'}
                  sx={{ fontWeight: 700 }}
                />
              </Box>
              <Divider sx={{ mb: 2 }} />
              
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box>
                  <Typography variant="subtitle2" fontWeight={600}>🌐 Browser Activity</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 3 }}>
                    Tab switches / focus lost: {session.proctoring_report.browser.tab_switches}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 3 }}>
                    Fullscreen exits: {session.proctoring_report.browser.fullscreen_exits > 0 
                      ? `❌ ${session.proctoring_report.browser.fullscreen_exits} exit(s) detected`
                      : '✅ None'}
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" fontWeight={600}>💬 Transcript Analysis</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 3 }}>
                    Suspicion score: {session.proctoring_report.transcript.suspicion_score}/10
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 3, fontStyle: 'italic' }}>
                    "{session.proctoring_report.transcript.reasoning}"
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" fontWeight={600}>📷 Camera Analysis</Typography>
                  {session.proctoring_report.camera.frames_analyzed > 0 ? (
                    <Box sx={{ ml: 3, mt: 0.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                          Face coverage:
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          value={session.proctoring_report.camera.face_coverage_percent}
                          sx={{
                            flex: 1,
                            height: 8,
                            borderRadius: 4,
                            bgcolor: `${session.proctoring_report.camera.face_coverage_percent > 80 ? '#22c55e' : session.proctoring_report.camera.face_coverage_percent >= 50 ? '#f59e0b' : '#ef4444'}20`,
                            '& .MuiLinearProgress-bar': {
                              bgcolor: session.proctoring_report.camera.face_coverage_percent > 80 ? '#22c55e' : session.proctoring_report.camera.face_coverage_percent >= 50 ? '#f59e0b' : '#ef4444',
                              borderRadius: 4,
                            },
                          }}
                        />
                        <Typography variant="body2" fontWeight={600} sx={{
                          color: session.proctoring_report.camera.face_coverage_percent > 80 ? '#22c55e' : session.proctoring_report.camera.face_coverage_percent >= 50 ? '#f59e0b' : '#ef4444',
                          minWidth: 45,
                        }}>
                          {session.proctoring_report.camera.face_coverage_percent}%
                        </Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        Multiple faces: {session.proctoring_report.camera.multiple_faces_detected
                          ? `❌ Detected in ${session.proctoring_report.camera.multiple_faces_segments?.length || 0} segment(s)`
                          : '✅ None detected'}
                      </Typography>
                      {session.proctoring_report.camera.face_absent_segments && session.proctoring_report.camera.face_absent_segments.length > 0 && (
                        <Box sx={{ mt: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">
                            Face absent during:
                          </Typography>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                            {session.proctoring_report.camera.face_absent_segments.map((seg: any, i: number) => (
                              <Chip key={i} label={`${seg.start} – ${seg.end}`} size="small" variant="outlined" color="warning" />
                            ))}
                          </Box>
                        </Box>
                      )}
                      <Typography variant="caption" color="text.disabled" sx={{ mt: 0.5, display: 'block' }}>
                        {session.proctoring_report.camera.frames_analyzed} frames analyzed
                      </Typography>
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.disabled" sx={{ ml: 3, fontStyle: 'italic' }}>
                      Video analysis unavailable — recording may still be processing
                    </Typography>
                  )}
                </Box>

                <Box>
                  <Typography variant="subtitle2" fontWeight={600}>🖥️ Screen Analysis</Typography>
                  {session.proctoring_report.screen.frames_analyzed > 0 ? (
                    <Box sx={{ ml: 3, mt: 0.5 }}>
                      <Box sx={{ mb: 0.5 }}>
                        <Typography variant="body2" color="text.secondary" component="span">
                          Suspicious URLs:{' '}
                        </Typography>
                        {session.proctoring_report.screen.suspicious_urls_detected && session.proctoring_report.screen.suspicious_urls_detected.length > 0 ? (
                          <Box sx={{ display: 'inline-flex', flexWrap: 'wrap', gap: 0.5 }}>
                            {session.proctoring_report.screen.suspicious_urls_detected.map((url: string) => (
                              <Chip key={url} label={url} size="small" color="error" />
                            ))}
                          </Box>
                        ) : (
                          <Typography variant="body2" color="text.secondary" component="span">✅ None detected</Typography>
                        )}
                      </Box>
                      <Box sx={{ mb: 0.5 }}>
                        <Typography variant="body2" color="text.secondary" component="span">
                          Suspicious objects:{' '}
                        </Typography>
                        {session.proctoring_report.screen.suspicious_labels && session.proctoring_report.screen.suspicious_labels.length > 0 ? (
                          <Box sx={{ display: 'inline-flex', flexWrap: 'wrap', gap: 0.5 }}>
                            {session.proctoring_report.screen.suspicious_labels.map((label: string) => (
                              <Chip key={label} label={label} size="small" color="warning" />
                            ))}
                          </Box>
                        ) : (
                          <Typography variant="body2" color="text.secondary" component="span">✅ None detected</Typography>
                        )}
                      </Box>
                      <Typography variant="caption" color="text.disabled">
                        {session.proctoring_report.screen.suspicious_frame_count} / {session.proctoring_report.screen.frames_analyzed} frames flagged
                      </Typography>
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.disabled" sx={{ ml: 3, fontStyle: 'italic' }}>
                      Video analysis unavailable — recording may still be processing
                    </Typography>
                  )}
                </Box>
              </Box>

              <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 3 }}>
                <Button 
                  size="small" 
                  variant="outlined" 
                  color="success" 
                  onClick={() => handleOverride('clean')}
                >
                  [✓ Mark as Reviewed] Clean
                </Button>
                <Button 
                  size="small" 
                  variant="outlined" 
                  color="error" 
                  onClick={() => handleOverride('flagged')}
                >
                  [Override: Flagged]
                </Button>
              </Box>
            </Paper>
          )}

          {/* INLINE VIDEO PLAYERS */}
          {urlsLoading && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="overline" color="text.secondary">
                Recordings
              </Typography>
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12} md={6}>
                  <Skeleton variant="rectangular" width="100%" height={160} sx={{ borderRadius: '8px' }} />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Skeleton variant="rectangular" width="100%" height={160} sx={{ borderRadius: '8px' }} />
                </Grid>
              </Grid>
            </Box>
          )}

          {!urlsLoading && (screenUrl || cameraUrl) && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="overline" color="text.secondary">
                Recordings
              </Typography>
              <Grid container spacing={2} sx={{ mt: 1 }}>
                {screenUrl && screenUrl !== 'null' && screenUrl !== '' && (
                  <Grid item xs={12} md={cameraUrl && cameraUrl !== 'null' && cameraUrl !== '' ? 6 : 12}>
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                      📺 Screen Recording
                    </Typography>
                    <video
                      controls
                      preload="metadata"
                      style={{
                        width: '100%',
                        borderRadius: '8px',
                        backgroundColor: '#000',
                        maxHeight: '240px',
                      }}
                      src={screenUrl}
                    >
                      Your browser does not support the video tag.
                    </video>
                    <Box sx={{ textAlign: 'right', mt: 0.5 }}>
                      <MuiLink
                        href={screenUrl}
                        download
                        target="_blank"
                        variant="caption"
                        color="text.secondary"
                      >
                        ⬇ Download
                      </MuiLink>
                    </Box>
                  </Grid>
                )}
                {cameraUrl && cameraUrl !== 'null' && cameraUrl !== '' && (
                  <Grid item xs={12} md={screenUrl && screenUrl !== 'null' && screenUrl !== '' ? 6 : 12}>
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                      📷 Camera Recording
                    </Typography>
                    <video
                      controls
                      preload="metadata"
                      style={{
                        width: '100%',
                        borderRadius: '8px',
                        backgroundColor: '#000',
                        maxHeight: '240px',
                      }}
                      src={cameraUrl}
                    >
                      Your browser does not support the video tag.
                    </video>
                    <Box sx={{ textAlign: 'right', mt: 0.5 }}>
                      <MuiLink
                        href={cameraUrl}
                        download
                        target="_blank"
                        variant="caption"
                        color="text.secondary"
                      >
                        ⬇ Download
                      </MuiLink>
                    </Box>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}

        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2, gap: 1 }}>
        <Button
          variant="outlined"
          onClick={handleDownloadTranscript}
          startIcon={<span>📄</span>}
        >
          Download Transcript
        </Button>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
