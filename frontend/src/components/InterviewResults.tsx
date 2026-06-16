/**
 * Interview results panel — per-question breakdown, scores, recording link.
 */
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Typography, Box, Divider, Chip, Paper, useTheme,
  LinearProgress,
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
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
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
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2, gap: 1 }}>
        {session.recording_sas_url && session.recording_sas_url !== 'null' && session.recording_sas_url !== '' && (
          <Button
            variant="outlined"
            onClick={() => window.open(session.recording_sas_url, '_blank')}
            startIcon={<span>💻</span>}
          >
            Watch Screen Recording
          </Button>
        )}
        {session.camera_sas_url && session.camera_sas_url !== 'null' && session.camera_sas_url !== '' && (
          <Button
            variant="outlined"
            onClick={() => window.open(session.camera_sas_url, '_blank')}
            startIcon={<span>📷</span>}
          >
            Watch Camera Recording
          </Button>
        )}
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
