/**
 * Interview API client — handles all interview-related API calls.
 */
import axios from 'axios';
import type { InterviewSession } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Request interceptor for auth token
apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('api_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface SchedulePayload {
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  scheduled_time: string;
  job_description_id: string;
  evaluation_id: string;
}

export interface ScheduleResponse {
  session_id: string;
  status: string;
  teams_link: string;
  message: string;
}

export const interviewApi = {
  /**
   * Schedule an interview for a candidate.
   */
  schedule: (payload: SchedulePayload) =>
    apiClient.post<ScheduleResponse>('/interview/schedule', payload),

  /**
   * Get the latest interview session for a candidate.
   */
  getCandidateSession: (candidateId: string, evaluationId?: string) =>
    apiClient.get<{ session: InterviewSession | null }>(
      `/interview/candidate/${candidateId}`,
      { params: evaluationId ? { evaluation_id: evaluationId } : undefined }
    ),

  /**
   * Get interview results by session ID.
   */
  getResults: (sessionId: string, evaluationId?: string) =>
    apiClient.get<InterviewSession>(
      `/interview/results/${sessionId}`,
      { params: evaluationId ? { evaluation_id: evaluationId } : undefined }
    ),
};

export default interviewApi;
