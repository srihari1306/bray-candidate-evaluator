/**
 * Evaluation page — JD input, skill configuration, and evaluation trigger.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, TextField, Button, Paper, IconButton, Slider,
  Chip, CircularProgress, Alert, Snackbar, useTheme, LinearProgress,
  Grid, Card, CardContent, Divider, Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Science as EvalIcon,
  Psychology as AiIcon,
  Lightbulb as TipIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { useEvalContext } from '../App';
import api from '../services/api';
import type { SkillCategory } from '../types';

const EXAMPLE_SKILLS: SkillCategory[] = [
  { name: 'Cloud Engineering', weight: 40 },
  { name: 'Agentic AI', weight: 35 },
  { name: 'Terminal/Linux', weight: 25 },
];

const EXAMPLE_JD = `We are looking for a Senior AI Engineer with strong experience in:

1. Cloud Infrastructure — Azure, Kubernetes, Terraform, Docker, CI/CD pipelines
2. Agentic AI Systems — LangChain, CrewAI, AutoGen, RAG pipelines, multi-agent orchestration
3. Terminal & Linux — Bash scripting, Linux administration, SSH, Docker CLI

The ideal candidate has 5+ years of experience building production-grade AI systems on cloud infrastructure. They should be comfortable with end-to-end deployment, from model development to Kubernetes orchestration.

Requirements:
- Strong Python and cloud engineering skills
- Experience with LLM-based applications and agentic frameworks
- Proficiency in Linux/terminal environments
- Knowledge of CI/CD, IaC, and DevOps practices
- Experience with vector databases and semantic search`;

export default function EvaluationPage() {
  const theme = useTheme();
  const navigate = useNavigate();
  const { addEvaluation } = useEvalContext();

  const [jobTitle, setJobTitle] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [skills, setSkills] = useState<SkillCategory[]>([]);
  const [newSkillName, setNewSkillName] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMsg, setStatusMsg] = useState('');
  const [error, setError] = useState('');
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

  const addSkill = () => {
    const name = newSkillName.trim();
    if (!name || skills.find((s) => s.name.toLowerCase() === name.toLowerCase())) return;
    setSkills([...skills, { name, weight: Math.floor(100 / (skills.length + 1)) }]);
    setNewSkillName('');
  };

  const removeSkill = (index: number) => {
    setSkills(skills.filter((_, i) => i !== index));
  };

  const updateWeight = (index: number, weight: number) => {
    const updated = [...skills];
    updated[index] = { ...updated[index], weight };
    setSkills(updated);
  };

  const loadExample = () => {
    setJobTitle('Senior AI Engineer');
    setJobDescription(EXAMPLE_JD);
    setSkills([...EXAMPLE_SKILLS]);
  };

  const handleEvaluate = async () => {
    if (jobDescription.length < 50) {
      setError('Job description must be at least 50 characters');
      return;
    }

    setLoading(true);
    setProgress(0);
    setStatusMsg('Starting evaluation...');
    setError('');

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return prev;
        const step = Math.random() * 15;
        const next = Math.min(prev + step, 90);
        const messages = [
          'Fetching resumes from SharePoint...',
          'Parsing documents with AI...',
          'Generating embeddings...',
          'Indexing in Azure AI Search...',
          'Running AI evaluation with GPT-4o...',
          'Scoring candidates...',
          'Ranking results...',
        ];
        setStatusMsg(messages[Math.floor(next / 15)] || 'Processing...');
        return next;
      });
    }, 800);

    try {
      const response = await api.evaluate({
        job_description: jobDescription,
        job_title: jobTitle,
        skills: skills.length > 0 ? skills : EXAMPLE_SKILLS,
        max_candidates: 50,
        reindex: false,
      });

      clearInterval(progressInterval);
      setProgress(100);
      setStatusMsg('Evaluation complete!');

      addEvaluation(response.data);
      setToast({ open: true, message: `Evaluated ${response.data.total_resumes_processed} candidates!`, severity: 'success' });

      setTimeout(() => navigate('/'), 1000);
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(err.response?.data?.detail || err.message || 'Evaluation failed');
      setToast({ open: true, message: 'Evaluation failed. Check backend connection.', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const totalWeight = skills.reduce((sum, s) => sum + s.weight, 0);

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto' }} className="animate-fade-in">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={800} gutterBottom>
          <span className="gradient-text">New Evaluation</span>
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Define a job description and custom skill categories. Our AI will evaluate all candidates
          using semantic understanding — not just keyword matching.
        </Typography>
      </Box>

      {/* Quick Start */}
      <Card sx={{ mb: 3, border: `1px solid ${theme.palette.primary.main}22` }}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 2 }}>
          <TipIcon sx={{ color: theme.palette.secondary.main }} />
          <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
            New here? Load an example to see how it works.
          </Typography>
          <Button variant="outlined" size="small" onClick={loadExample}>
            Load Example
          </Button>
        </CardContent>
      </Card>

      {/* Job Description */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" fontWeight={600} gutterBottom>
          Job Description
        </Typography>
        <TextField
          label="Job Title"
          value={jobTitle}
          onChange={(e) => setJobTitle(e.target.value)}
          fullWidth
          sx={{ mb: 2 }}
          placeholder="e.g., Senior AI Engineer"
        />
        <TextField
          label="Job Description"
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          fullWidth
          multiline
          rows={8}
          placeholder="Paste the full job description here..."
          helperText={`${jobDescription.length} characters (minimum 50)`}
        />
      </Paper>

      {/* Skill Categories */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" fontWeight={600} gutterBottom>
          Custom Skill Categories
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Define skills to evaluate. The AI will score each candidate on these categories independently.
        </Typography>

        {/* Add skill input */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            size="small"
            value={newSkillName}
            onChange={(e) => setNewSkillName(e.target.value)}
            placeholder="e.g., Cloud Engineering"
            onKeyDown={(e) => e.key === 'Enter' && addSkill()}
            sx={{ flexGrow: 1 }}
          />
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={addSkill}
            disabled={!newSkillName.trim()}
          >
            Add
          </Button>
        </Box>

        {/* Skill list with weight sliders */}
        <AnimatePresence>
          {skills.map((skill, i) => (
            <motion.div
              key={skill.name}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 2,
                  py: 1.5,
                  px: 2,
                  mb: 1,
                  borderRadius: '10px',
                  bgcolor: theme.palette.action.hover,
                }}
              >
                <Chip label={skill.name} color="primary" variant="outlined" sx={{ minWidth: 160 }} />
                <Box sx={{ flexGrow: 1, mx: 2 }}>
                  <Slider
                    value={skill.weight}
                    onChange={(_, v) => updateWeight(i, v as number)}
                    min={0}
                    max={100}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(v) => `${v}%`}
                    size="small"
                  />
                </Box>
                <Typography variant="body2" fontWeight={600} sx={{ minWidth: 40, textAlign: 'right' }}>
                  {skill.weight}%
                </Typography>
                <IconButton size="small" onClick={() => removeSkill(i)} color="error">
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            </motion.div>
          ))}
        </AnimatePresence>

        {skills.length > 0 && (
          <Box sx={{ mt: 1, display: 'flex', justifyContent: 'flex-end' }}>
            <Chip
              label={`Total weight: ${totalWeight}%`}
              color={totalWeight === 100 ? 'success' : 'warning'}
              size="small"
            />
          </Box>
        )}
      </Paper>

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* Progress */}
      {loading && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <AiIcon sx={{ color: theme.palette.primary.main, animation: 'pulse 1.5s infinite' }} />
            <Typography variant="body1" fontWeight={500}>
              {statusMsg}
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: theme.palette.action.hover,
              '& .MuiLinearProgress-bar': {
                borderRadius: 4,
                background: 'linear-gradient(90deg, #667eea, #764ba2, #14b8a6)',
              },
            }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', textAlign: 'right' }}>
            {Math.round(progress)}%
          </Typography>
        </Paper>
      )}

      {/* Evaluate Button */}
      <Button
        variant="contained"
        size="large"
        startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <EvalIcon />}
        onClick={handleEvaluate}
        disabled={loading || jobDescription.length < 50}
        fullWidth
        sx={{
          py: 1.8,
          fontSize: '1.05rem',
          background: loading
            ? undefined
            : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          boxShadow: '0 6px 24px rgba(102, 126, 234, 0.3)',
        }}
      >
        {loading ? 'Evaluating...' : 'Evaluate Candidates'}
      </Button>

      {/* Toast */}
      <Snackbar
        open={toast.open}
        autoHideDuration={4000}
        onClose={() => setToast({ ...toast, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity={toast.severity} variant="filled" onClose={() => setToast({ ...toast, open: false })}>
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
