/**
 * Interview scheduling modal — date/time picker for recruiter.
 */
import { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Button, Typography, Box, Alert, CircularProgress,
} from '@mui/material';
import { interviewApi, type SchedulePayload } from '../services/interviewApi';

interface InterviewModalProps {
  open: boolean;
  onClose: () => void;
  candidateId: string;
  candidateName: string;
  candidateEmail: string;
  evaluationId: string;
  onScheduled: (sessionId: string, scheduledTime: string) => void;
}

export default function InterviewModal({
  open, onClose, candidateId, candidateName, candidateEmail,
  evaluationId, onScheduled,
}: InterviewModalProps) {
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleConfirm = async () => {
    if (!date || !time) {
      setError('Please select both date and time.');
      return;
    }

    const scheduledTime = new Date(`${date}T${time}`).toISOString();
    setLoading(true);
    setError('');

    try {
      const payload: SchedulePayload = {
        candidate_id: candidateId,
        candidate_name: candidateName,
        candidate_email: candidateEmail,
        scheduled_time: scheduledTime,
        job_description_id: evaluationId,
        evaluation_id: evaluationId,
      };

      const response = await interviewApi.schedule(payload);
      onScheduled(response.data.session_id, scheduledTime);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to schedule interview. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setDate('');
      setTime('');
      setError('');
      onClose();
    }
  };

  // Get today's local date as minimum
  const today = new Date();
  const minDate = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().split('T')[0];

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ pb: 1 }}>
        <Typography variant="h6" fontWeight={700}>Schedule Interview</Typography>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
          <TextField
            label="Candidate"
            value={candidateName}
            disabled
            fullWidth
            size="small"
            InputProps={{
              sx: { fontWeight: 600 },
            }}
          />

          {candidateEmail && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: -1.5 }}>
              Email: {candidateEmail}
            </Typography>
          )}

          <TextField
            label="Interview Date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            fullWidth
            size="small"
            inputProps={{ min: minDate }}
            InputLabelProps={{ shrink: true }}
          />

          <TextField
            label="Interview Time"
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
          />

          {error && (
            <Alert severity="error" variant="outlined" sx={{ py: 0.5 }}>
              {error}
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ p: 2, pt: 1 }}>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={loading || !date || !time}
          startIcon={loading ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {loading ? 'Scheduling...' : 'Confirm'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
