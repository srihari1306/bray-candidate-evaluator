/**
 * Dashboard page — candidate rankings, charts, and detailed views.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Paper, Chip, Avatar, IconButton, TextField,
  Button, useTheme, Grid, Card, CardContent, Tooltip, Dialog,
  DialogTitle, DialogContent, DialogActions, Divider, Tabs, Tab,
  InputAdornment, Snackbar, Alert, CircularProgress,
} from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import {
  Search as SearchIcon,
  Download as DownloadIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Visibility as ViewIcon,
  EmojiEvents as TrophyIcon,
  People as PeopleIcon,
  TrendingUp as TrendIcon,
  Assessment as AssessIcon,
  Science as EvalIcon,
  VideoCall as InterviewIcon,
} from '@mui/icons-material';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, Cell, Legend,
} from 'recharts';
import { motion } from 'framer-motion';
import { useEvalContext } from '../App';
import type { CandidateResult, SkillScore, InterviewSession, InterviewStatusType } from '../types';
import api from '../services/api';
import interviewApi from '../services/interviewApi';
import InterviewModal from '../components/InterviewModal';
import InterviewResults from '../components/InterviewResults';

const CHART_COLORS = ['#667eea', '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

function getScoreColor(score: number): string {
  if (score >= 80) return '#22c55e';
  if (score >= 60) return '#3b82f6';
  if (score >= 40) return '#f59e0b';
  return '#ef4444';
}

function getRecommendationColor(rec: string): 'success' | 'info' | 'warning' | 'error' {
  if (rec === 'Strong Match') return 'success';
  if (rec === 'Good Match') return 'info';
  if (rec === 'Moderate Match') return 'warning';
  return 'error';
}

// ─── Score Card Component ───
function ScoreCard({ title, value, icon, color, subtitle }: {
  title: string; value: string | number; icon: React.ReactNode;
  color: string; subtitle?: string;
}) {
  const theme = useTheme();
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      <Card sx={{ height: '100%' }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <Box>
              <Typography variant="body2" color="text.secondary" fontWeight={500}>
                {title}
              </Typography>
              <Typography variant="h4" fontWeight={800} sx={{ my: 0.5, color }}>
                {value}
              </Typography>
              {subtitle && (
                <Typography variant="caption" color="text.secondary">
                  {subtitle}
                </Typography>
              )}
            </Box>
            <Box
              sx={{
                width: 48, height: 48, borderRadius: '14px',
                background: `${color}18`, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
              }}
            >
              {icon}
            </Box>
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function DashboardPage() {
  const theme = useTheme();
  const navigate = useNavigate();
  const { currentEvaluation } = useEvalContext();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateResult | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailTab, setDetailTab] = useState(0);
  const [toast, setToast] = useState({ open: false, message: '' });

  // ─── Smart Interviewer State ───
  const [interviewSessions, setInterviewSessions] = useState<Record<string, InterviewSession>>({});
  const [interviewModalOpen, setInterviewModalOpen] = useState(false);
  const [interviewModalCandidate, setInterviewModalCandidate] = useState<CandidateResult | null>(null);
  const [interviewResultsOpen, setInterviewResultsOpen] = useState(false);
  const [selectedInterviewSession, setSelectedInterviewSession] = useState<InterviewSession | null>(null);
  const [pollingSessionIds, setPollingSessionIds] = useState<Set<string>>(new Set());

  // Load interview sessions for all candidates on mount
  useEffect(() => {
    if (!currentEvaluation?.candidates?.length) return;

    const loadSessions = async () => {
      const sessions: Record<string, InterviewSession> = {};
      for (const candidate of currentEvaluation.candidates) {
        try {
          const response = await interviewApi.getCandidateSession(candidate.id, currentEvaluation.evaluation_id);
          if (response.data.session) {
            sessions[candidate.id] = response.data.session;
            // Start polling for non-completed sessions
            const s = response.data.session;
            if (s.status === 'scheduled' || s.status === 'in_progress') {
              setPollingSessionIds((prev) => new Set([...prev, s.session_id]));
            }
          }
        } catch {
          // No session for this candidate
        }
      }
      setInterviewSessions(sessions);
    };

    loadSessions();
  }, [currentEvaluation]);

  // Poll for active sessions
  useEffect(() => {
    if (pollingSessionIds.size === 0) return;

    const interval = setInterval(async () => {
      for (const sessionId of pollingSessionIds) {
        try {
          const response = await interviewApi.getResults(sessionId, currentEvaluation?.evaluation_id);
          const data = response.data;
          if (data.status === 'completed' || data.status === 'failed') {
            setInterviewSessions((prev) => ({
              ...prev,
              [data.candidate_id]: data,
            }));
            setPollingSessionIds((prev) => {
              const next = new Set(prev);
              next.delete(sessionId);
              return next;
            });
            if (data.status === 'completed') {
              setToast({ open: true, message: `Interview completed for ${data.candidate_name}! Score: ${data.final_score}/10` });
            }
          }
        } catch {
          // Will retry next poll
        }
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [pollingSessionIds]);

  const handleInterviewScheduled = (candidateId: string, sessionId: string, scheduledTime: string) => {
    setInterviewSessions((prev) => ({
      ...prev,
      [candidateId]: {
        session_id: sessionId,
        candidate_id: candidateId,
        candidate_name: interviewModalCandidate?.candidate_name || '',
        status: 'scheduled' as InterviewStatusType,
        scheduled_time: scheduledTime,
        final_score: null,
        answers: [],
        recording_sas_url: '',
        completed_at: null,
      },
    }));
    setPollingSessionIds((prev) => new Set([...prev, sessionId]));
    setToast({ open: true, message: 'Interview scheduled successfully!' });
  };

  // No evaluation yet
  if (!currentEvaluation || currentEvaluation.candidates.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 12 }} className="animate-fade-in">
        <EvalIcon sx={{ fontSize: 80, color: theme.palette.text.secondary, opacity: 0.3, mb: 2 }} />
        <Typography variant="h5" fontWeight={700} gutterBottom>
          No Evaluation Results Yet
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: 400, mx: 'auto' }}>
          Start a new evaluation to see candidate rankings, charts, and AI-powered insights.
        </Typography>
        <Button
          variant="contained"
          size="large"
          startIcon={<EvalIcon />}
          onClick={() => navigate('/evaluate')}
        >
          Start New Evaluation
        </Button>
      </Box>
    );
  }

  const candidates = currentEvaluation.candidates;
  const skillNames = currentEvaluation.skills_evaluated;

  // Filter
  const filtered = candidates.filter((c) =>
    c.candidate_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Stats
  const topCandidate = candidates[0];
  const strongMatches = candidates.filter((c) => c.overall_score >= 75).length;

  // Chart data
  const barData = filtered.map((c) => ({
    name: c.candidate_name.split(' ')[0],
    score: c.overall_score,
  }));

  const radarData = skillNames.map((skill) => {
    const entry: any = { skill };
    filtered.forEach((c) => {
      const ss = c.skill_scores.find((s) => s.skill === skill);
      entry[c.candidate_name.split(' ')[0]] = ss?.score || 0;
    });
    return entry;
  });

  // Heatmap data
  const heatmapData = filtered.map((c) => ({
    name: c.candidate_name,
    ...Object.fromEntries(c.skill_scores.map((s) => [s.skill, s.score])),
  }));

  // DataGrid columns
  const columns: GridColDef[] = [
    {
      field: 'rank',
      headerName: '#',
      width: 60,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%' }}>
          {params.row._rank <= 3 ? (
            <TrophyIcon sx={{ color: ['#fbbf24', '#94a3b8', '#cd7f32'][params.row._rank - 1], fontSize: 20 }} />
          ) : (
            <Typography variant="body2" color="text.secondary">{params.row._rank}</Typography>
          )}
        </Box>
      ),
    },
    {
      field: 'candidate_name',
      headerName: 'Candidate',
      flex: 1,
      minWidth: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, height: '100%' }}>
          <Avatar sx={{ width: 32, height: 32, bgcolor: getScoreColor(params.row.overall_score), fontSize: '0.75rem' }}>
            {params.row.candidate_name.split(' ').map((n: string) => n[0]).join('').slice(0, 2)}
          </Avatar>
          <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <Typography variant="body2" fontWeight={600} sx={{ lineHeight: 1.2 }}>{params.row.candidate_name}</Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, lineHeight: 1.2 }}>{params.row.email}</Typography>
          </Box>
        </Box>
      ),
    },
    {
      field: 'overall_score',
      headerName: 'Overall',
      width: 100,
      align: 'center',
      headerAlign: 'center',
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value}
          size="small"
          sx={{
            fontWeight: 700,
            bgcolor: `${getScoreColor(params.value as number)}20`,
            color: getScoreColor(params.value as number),
            border: `1px solid ${getScoreColor(params.value as number)}40`,
          }}
        />
      ),
    },
    ...skillNames.map((skill) => ({
      field: `skill_${skill}`,
      headerName: skill,
      width: 130,
      align: 'center' as const,
      headerAlign: 'center' as const,
      valueGetter: (_value: any, row: any) => {
        const ss = (row.skill_scores as SkillScore[])?.find((s) => s.skill === skill);
        return ss?.score || 0;
      },
      renderCell: (params: GridRenderCellParams) => (
        <Typography
          variant="body2"
          fontWeight={600}
          sx={{ color: getScoreColor(params.value as number) }}
        >
          {params.value}
        </Typography>
      ),
    })),
    {
      field: 'overall_recommendation',
      headerName: 'Match',
      width: 140,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value}
          size="small"
          color={getRecommendationColor(params.value as string)}
          variant="outlined"
        />
      ),
    },
    {
      field: 'interview',
      headerName: 'Interview',
      width: 170,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => {
        const candidateId = params.row.id;
        const session = interviewSessions[candidateId];

        if (!session || session.status === 'none') {
          return (
            <Button
              variant="outlined"
              size="small"
              startIcon={<InterviewIcon />}
              onClick={() => {
                setInterviewModalCandidate(params.row as CandidateResult);
                setInterviewModalOpen(true);
              }}
              sx={{ textTransform: 'none', fontWeight: 600, fontSize: 12 }}
            >
              Start Interview
            </Button>
          );
        }

        if (session.status === 'scheduled') {
          const dt = new Date(session.scheduled_time);
          return (
            <Chip
              label={`Scheduled ${dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`}
              size="small"
              color="info"
              variant="outlined"
              sx={{ fontWeight: 600 }}
            />
          );
        }

        if (session.status === 'in_progress') {
          return (
            <Chip
              label="In Progress"
              size="small"
              color="warning"
              variant="outlined"
              icon={<CircularProgress size={12} color="inherit" />}
              sx={{ fontWeight: 600 }}
            />
          );
        }

        if (session.status === 'completed') {
          return (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Chip
                label={`${session.final_score}/10`}
                size="small"
                sx={{
                  fontWeight: 700,
                  bgcolor: `${session.final_score && session.final_score >= 7 ? '#22c55e' : session.final_score && session.final_score >= 5 ? '#f59e0b' : '#ef4444'}20`,
                  color: session.final_score && session.final_score >= 7 ? '#22c55e' : session.final_score && session.final_score >= 5 ? '#f59e0b' : '#ef4444',
                }}
              />
              <Tooltip title="View Results">
                <IconButton
                  size="small"
                  onClick={() => {
                    setSelectedInterviewSession(session);
                    setInterviewResultsOpen(true);
                  }}
                >
                  <ViewIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          );
        }

        return <Chip label="Failed" size="small" color="error" variant="outlined" />;
      },
    },
    {
      field: 'actions',
      headerName: '',
      width: 100,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Tooltip title="View Details">
            <IconButton
              size="small"
              onClick={() => {
                setSelectedCandidate(params.row as CandidateResult);
                setDetailOpen(true);
                setDetailTab(0);
              }}
            >
              <ViewIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title={params.row.shortlisted ? 'Remove from shortlist' : 'Shortlist'}>
            <IconButton size="small" color={params.row.shortlisted ? 'warning' : 'default'}>
              {params.row.shortlisted ? <StarIcon fontSize="small" /> : <StarBorderIcon fontSize="small" />}
            </IconButton>
          </Tooltip>
        </Box>
      ),
    },
  ];

  const rows = filtered.map((c, i) => ({ ...c, _rank: i + 1 }));

  // Export handler
  const handleExport = async (format: 'csv' | 'xlsx') => {
    try {
      const response = await api.exportResults(currentEvaluation.evaluation_id, format);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `candidates.${format}`;
      link.click();
      window.URL.revokeObjectURL(url);
      setToast({ open: true, message: `Exported as ${format.toUpperCase()}` });
    } catch {
      setToast({ open: true, message: 'Export failed — ensure backend is running' });
    }
  };

  return (
    <Box className="animate-fade-in">
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" fontWeight={800} color="primary">
            Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {currentEvaluation.job_title || 'Evaluation'} • {candidates.length} candidates •{' '}
            {currentEvaluation.processing_time_seconds?.toFixed(1)}s
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" size="small" startIcon={<DownloadIcon />} onClick={() => handleExport('xlsx')}>
            Excel
          </Button>
          <Button variant="outlined" size="small" startIcon={<DownloadIcon />} onClick={() => handleExport('csv')}>
            CSV
          </Button>
        </Box>
      </Box>

      {/* Score Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <ScoreCard title="Total Candidates" value={candidates.length} subtitle="Resumes evaluated"
            icon={<PeopleIcon sx={{ color: '#667eea' }} />} color="#667eea" />
        </Grid>
        <Grid item xs={12} md={4}>
          <ScoreCard title="Top Score" value={topCandidate?.overall_score || 0} subtitle={topCandidate?.candidate_name}
            icon={<TrophyIcon sx={{ color: '#22c55e' }} />} color="#22c55e" />
        </Grid>
        <Grid item xs={12} md={4}>
          <ScoreCard title="Strong Matches" value={strongMatches} subtitle="Score ≥ 75"
            icon={<AssessIcon sx={{ color: '#14b8a6' }} />} color="#14b8a6" />
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {/* Bar Chart */}
        <Grid item xs={12} md={12}>
          <Paper sx={{ p: 3, height: 360 }}>
            <Typography variant="h6" fontWeight={600} gutterBottom>Candidate Scores</Typography>
            <ResponsiveContainer width="100%" height={290}>
              <BarChart data={barData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                <RTooltip
                  contentStyle={{
                    background: theme.palette.background.paper,
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: 8,
                  }}
                />
                <Legend />
                <Bar dataKey="score" name="Overall Score" radius={[6, 6, 0, 0]}>
                  {barData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Skill Heatmap */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" fontWeight={600} gutterBottom>Skill Heatmap</Typography>
        <Box sx={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: theme.palette.text.secondary, fontSize: 13 }}>Candidate</th>
                {skillNames.map((s) => (
                  <th key={s} style={{ textAlign: 'center', padding: '8px 12px', color: theme.palette.text.secondary, fontSize: 13 }}>{s}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id}>
                  <td style={{ padding: '6px 12px', fontWeight: 500, fontSize: 14 }}>{c.candidate_name}</td>
                  {skillNames.map((skill) => {
                    const ss = c.skill_scores.find((s) => s.skill === skill);
                    const score = ss?.score || 0;
                    const bg = score >= 80 ? '#22c55e' : score >= 60 ? '#3b82f6' : score >= 40 ? '#f59e0b' : '#ef4444';
                    return (
                      <td key={skill} style={{
                        textAlign: 'center', padding: '6px 12px',
                        background: `${bg}18`, color: bg, fontWeight: 700, fontSize: 14,
                        borderRadius: 4,
                      }}>
                        {score}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </Box>
      </Paper>

      {/* Search + Data Table */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" fontWeight={600}>Candidate Rankings</Typography>
          <TextField
            size="small"
            placeholder="Search candidates..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment>,
            }}
            sx={{ width: 260 }}
          />
        </Box>
        <DataGrid
          rows={rows}
          columns={columns}
          rowHeight={64}
          pageSizeOptions={[5, 10, 25]}
          initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
          disableRowSelectionOnClick
          autoHeight
          sx={{
            border: 'none',
            '& .MuiDataGrid-cell': { borderBottom: `1px solid ${theme.palette.divider}` },
            '& .MuiDataGrid-columnHeaders': { bgcolor: theme.palette.action.hover, borderRadius: '10px' },
            '& .MuiDataGrid-row:hover': { bgcolor: `${theme.palette.primary.main}08` },
          }}
        />
      </Paper>

      {/* ─── Candidate Detail Dialog ─── */}
      <Dialog open={detailOpen} onClose={() => setDetailOpen(false)} maxWidth="md" fullWidth>
        {selectedCandidate && (
          <>
            <DialogTitle sx={{ pb: 0 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Avatar sx={{ width: 48, height: 48, bgcolor: getScoreColor(selectedCandidate.overall_score), fontWeight: 700 }}>
                  {selectedCandidate.candidate_name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                </Avatar>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h6" fontWeight={700}>{selectedCandidate.candidate_name}</Typography>
                  <Typography variant="body2" color="text.secondary">{selectedCandidate.email}</Typography>
                </Box>
                <Box sx={{ textAlign: 'right' }}>
                  <Typography variant="h4" fontWeight={800} sx={{ color: getScoreColor(selectedCandidate.overall_score) }}>
                    {selectedCandidate.overall_score}
                  </Typography>
                  <Chip label={selectedCandidate.overall_recommendation} size="small"
                    color={getRecommendationColor(selectedCandidate.overall_recommendation)} />
                </Box>
              </Box>
            </DialogTitle>
            <DialogContent>
              <Tabs value={detailTab} onChange={(_, v) => setDetailTab(v)} sx={{ mb: 2 }}>
                <Tab label="Overview" />
                <Tab label="Skills" />
                <Tab label="AI Insights" />
              </Tabs>

              {detailTab === 0 && (
                <Box>
                  <Typography variant="body1" sx={{ mb: 2 }}>{selectedCandidate.summary}</Typography>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="subtitle2" fontWeight={600} gutterBottom>Recommendation</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{selectedCandidate.recommendation}</Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="subtitle2" fontWeight={600} color="success.main" gutterBottom>Strengths</Typography>
                      {selectedCandidate.strengths.map((s, i) => (
                        <Typography key={i} variant="body2" sx={{ mb: 0.5 }}>• {s}</Typography>
                      ))}
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="subtitle2" fontWeight={600} color="error.main" gutterBottom>Weaknesses</Typography>
                      {selectedCandidate.weaknesses.map((w, i) => (
                        <Typography key={i} variant="body2" sx={{ mb: 0.5 }}>• {w}</Typography>
                      ))}
                    </Grid>
                  </Grid>
                </Box>
              )}

              {detailTab === 1 && (
                <Box>
                  {selectedCandidate.skill_scores.map((ss) => (
                    <Box key={ss.skill} sx={{ mb: 3 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="subtitle2" fontWeight={600}>{ss.skill}</Typography>
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                          <Chip label={ss.confidence} size="small" variant="outlined" />
                          <Typography variant="h6" fontWeight={700} sx={{ color: getScoreColor(ss.score) }}>
                            {ss.score}
                          </Typography>
                        </Box>
                      </Box>
                      <Box sx={{ bgcolor: theme.palette.action.hover, borderRadius: 2, p: 1.5 }}>
                        {ss.evidence.map((e, i) => (
                          <Typography key={i} variant="body2" sx={{ mb: 0.3 }}>• {e}</Typography>
                        ))}
                      </Box>
                    </Box>
                  ))}
                  {selectedCandidate.missing_skills.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" fontWeight={600} color="error.main" gutterBottom>Missing Skills</Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {selectedCandidate.missing_skills.map((s) => (
                          <Chip key={s} label={s} size="small" color="error" variant="outlined" />
                        ))}
                      </Box>
                    </Box>
                  )}
                </Box>
              )}

              {detailTab === 2 && (
                <Box>
                  <Typography variant="subtitle2" fontWeight={600} gutterBottom>AI-Generated Interview Questions</Typography>
                  {selectedCandidate.interview_questions.map((q, i) => (
                    <Paper key={i} sx={{ p: 2, mb: 1.5, bgcolor: theme.palette.action.hover }}>
                      <Typography variant="body2"><strong>Q{i + 1}.</strong> {q}</Typography>
                    </Paper>
                  ))}
                </Box>
              )}
            </DialogContent>
            <DialogActions sx={{ p: 2 }}>
              {selectedCandidate.resume_url && (
                <Button 
                  variant="outlined" 
                  onClick={() => window.open(selectedCandidate.resume_url, '_blank')}
                >
                  View Resume
                </Button>
              )}
              <Button onClick={() => setDetailOpen(false)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* ─── Interview Modal ─── */}
      {interviewModalCandidate && (
        <InterviewModal
          open={interviewModalOpen}
          onClose={() => {
            setInterviewModalOpen(false);
            setInterviewModalCandidate(null);
          }}
          candidateId={interviewModalCandidate.id}
          candidateName={interviewModalCandidate.candidate_name}
          candidateEmail={interviewModalCandidate.email}
          evaluationId={currentEvaluation?.evaluation_id || ''}
          onScheduled={(sessionId, scheduledTime) => {
            handleInterviewScheduled(interviewModalCandidate.id, sessionId, scheduledTime);
          }}
        />
      )}

      {/* ─── Interview Results ─── */}
      {selectedInterviewSession && (
        <InterviewResults
          open={interviewResultsOpen}
          onClose={() => {
            setInterviewResultsOpen(false);
            setSelectedInterviewSession(null);
          }}
          session={selectedInterviewSession}
        />
      )}

      <Snackbar open={toast.open} autoHideDuration={3000} onClose={() => setToast({ ...toast, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity="info" variant="filled">{toast.message}</Alert>
      </Snackbar>
    </Box>
  );
}
