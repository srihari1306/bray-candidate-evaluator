/**
 * TypeScript interfaces for the Candidate Evaluator application.
 */

export type RecommendationType =
  | 'Strong Match'
  | 'Good Match'
  | 'Moderate Match'
  | 'Weak Match'
  | 'Not Recommended';

export type ConfidenceLevel = 'High' | 'Medium' | 'Low';

export type EvaluationStatus =
  | 'pending'
  | 'fetching_resumes'
  | 'parsing'
  | 'embedding'
  | 'indexing'
  | 'evaluating'
  | 'completed'
  | 'failed';

export interface SkillCategory {
  name: string;
  weight: number;
}

export interface EvaluationRequest {
  job_description: string;
  job_title: string;
  skills: SkillCategory[];
  max_candidates: number;
  reindex: boolean;
}

export interface SkillScore {
  skill: string;
  score: number;
  confidence: ConfidenceLevel;
  evidence: string[];
}

export interface ParsedProfile {
  name: string;
  email: string;
  phone: string;
  skills: string[];
  experience_years: number | null;
  education: string[];
  certifications: string[];
  work_history: string[];
  projects: string[];
  technologies: string[];
}

export interface CandidateResult {
  id: string;
  candidate_name: string;
  email: string;
  overall_score: number;
  overall_recommendation: RecommendationType;
  skill_scores: SkillScore[];
  missing_skills: string[];
  strengths: string[];
  weaknesses: string[];
  summary: string;
  recommendation: string;
  interview_questions: string[];
  resume_url: string;
  resume_filename: string;
  shortlisted: boolean;
  notes: string[];
  parsed_profile: ParsedProfile | null;
}

export interface EvaluationResponse {
  evaluation_id: string;
  status: EvaluationStatus;
  job_title: string;
  job_description_preview: string;
  skills_evaluated: string[];
  total_resumes_processed: number;
  candidates: CandidateResult[];
  created_at: string;
  completed_at: string | null;
  processing_time_seconds: number | null;
}

export interface CandidateListResponse {
  candidates: CandidateResult[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EvaluationHistoryItem {
  evaluation_id: string;
  job_title: string;
  skills_evaluated: string[];
  total_candidates: number;
  top_candidate: string;
  top_score: number;
  created_at: string;
  status: EvaluationStatus;
}

export interface HealthResponse {
  status: string;
  version: string;
  services: Record<string, string>;
}

// ─── Smart Interviewer Types ────────────────────────────────────────────────

export type InterviewStatusType =
  | 'none'
  | 'scheduled'
  | 'in_progress'
  | 'completed'
  | 'failed';

export interface InterviewAnswer {
  question_index: number;
  question_text: string;
  transcript: string;
  score: number;
  score_reasoning: string;
}

export interface InterviewSession {
  session_id: string;
  candidate_id: string;
  candidate_name: string;
  status: InterviewStatusType;
  scheduled_time: string;
  final_score: number | null;
  answers: InterviewAnswer[];
  recording_sas_url: string;
  camera_sas_url?: string;
  completed_at: string | null;
}
