/**
 * History page — view past evaluations.
 */
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Paper, Chip, Button, useTheme, Card, CardContent,
  Grid, IconButton, Tooltip,
} from '@mui/material';
import {
  History as HistoryIcon,
  Replay as ReplayIcon,
  Visibility as ViewIcon,
  EmojiEvents as TrophyIcon,
  Science as EvalIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useEvalContext } from '../App';

export default function HistoryPage() {
  const theme = useTheme();
  const navigate = useNavigate();
  const { evaluationHistory, setCurrentEvaluation } = useEvalContext();

  if (evaluationHistory.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 12 }} className="animate-fade-in">
        <HistoryIcon sx={{ fontSize: 80, color: theme.palette.text.secondary, opacity: 0.3, mb: 2 }} />
        <Typography variant="h5" fontWeight={700} gutterBottom>
          No Evaluation History
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: 400, mx: 'auto' }}>
          Your past evaluations will appear here after you run your first evaluation.
        </Typography>
        <Button
          variant="contained"
          size="large"
          startIcon={<EvalIcon />}
          onClick={() => navigate('/evaluate')}
          sx={{ background: 'linear-gradient(135deg, #667eea, #764ba2)' }}
        >
          Start First Evaluation
        </Button>
      </Box>
    );
  }

  return (
    <Box className="animate-fade-in">
      <Typography variant="h4" fontWeight={800} gutterBottom>
        <span className="gradient-text">Evaluation History</span>
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Review past evaluations and revisit candidate rankings.
      </Typography>

      <Grid container spacing={2}>
        {evaluationHistory.map((evalData, i) => (
          <Grid item xs={12} md={6} key={evalData.evaluation_id}>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
              <Card
                sx={{
                  cursor: 'pointer',
                  '&:hover': { borderColor: theme.palette.primary.main },
                  border: `1px solid ${theme.palette.divider}`,
                }}
                onClick={() => {
                  setCurrentEvaluation(evalData);
                  navigate('/');
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box>
                      <Typography variant="h6" fontWeight={700}>
                        {evalData.job_title || 'Untitled Evaluation'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(evalData.created_at).toLocaleDateString('en-US', {
                          year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                        })}
                      </Typography>
                    </Box>
                    <Chip
                      label={evalData.status}
                      size="small"
                      color={evalData.status === 'completed' ? 'success' : 'warning'}
                    />
                  </Box>

                  <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                    {evalData.skills_evaluated.map((s) => (
                      <Chip key={s} label={s} size="small" variant="outlined" />
                    ))}
                  </Box>

                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box sx={{ display: 'flex', gap: 3 }}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">Candidates</Typography>
                        <Typography variant="h6" fontWeight={700}>{evalData.candidates.length}</Typography>
                      </Box>
                      {evalData.candidates[0] && (
                        <Box>
                          <Typography variant="caption" color="text.secondary">Top Score</Typography>
                          <Typography variant="h6" fontWeight={700} sx={{ color: '#22c55e' }}>
                            {evalData.candidates[0].overall_score}
                          </Typography>
                        </Box>
                      )}
                    </Box>
                    <Tooltip title="View Results">
                      <IconButton color="primary">
                        <ViewIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </CardContent>
              </Card>
            </motion.div>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
