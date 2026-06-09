/**
 * Axios-based API client for backend communication.
 */
import axios, { AxiosInstance } from 'axios';
import type {
  EvaluationRequest,
  EvaluationResponse,
  CandidateListResponse,
  CandidateResult,
  HealthResponse,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 300000, // 5 min for evaluation
});

// Request interceptor for auth token
apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('api_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const api = {
  // Health
  health: () => apiClient.get<HealthResponse>('/health'),

  // Evaluation
  evaluate: (data: EvaluationRequest) =>
    apiClient.post<EvaluationResponse>('/api/evaluate', data),

  // Candidates
  getCandidates: (params?: {
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: string;
    search?: string;
    min_score?: number;
    evaluation_id?: string;
  }) => apiClient.get<CandidateListResponse>('/api/candidates', { params }),

  getCandidate: (id: string) =>
    apiClient.get<CandidateResult>(`/api/candidate/${id}`),

  shortlistCandidate: (id: string, shortlisted: boolean) =>
    apiClient.post(`/api/candidates/${id}/shortlist`, { shortlisted }),

  addNote: (id: string, content: string) =>
    apiClient.post(`/api/candidates/${id}/notes`, { content }),

  // Export
  exportResults: (evaluationId: string, format: 'csv' | 'xlsx' = 'xlsx') =>
    apiClient.get(`/api/export/${evaluationId}`, {
      params: { format },
      responseType: 'blob',
    }),

  // History
  getHistory: () =>
    apiClient.get<EvaluationResponse[]>('/api/history'),

  deleteEvaluation: (evaluationId: string) =>
    apiClient.delete<{ message: string; evaluation_id: string }>(`/api/history/${evaluationId}`),

  // Reindex
  reindex: () => apiClient.post('/api/reindex'),
};

export default api;
