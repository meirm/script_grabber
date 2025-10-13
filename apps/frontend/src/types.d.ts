/**
 * Type definitions for ScriptGrabber frontend
 */

export interface JobSubmitResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'failed' | 'timeout' | 'not_found';
  grabber?: string;
  submitted_at?: string;
  completed_at?: string;
  stdout?: string;
  stderr?: string;
  exit_code?: number;
}

export interface ClusterStatus {
  active_grabbers: string[];
  jobs_queued: number;
  jobs_running: number;
  jobs_done: number;
  jobs_failed: number;
  jobs_timeout: number;
  total_jobs: number;
}

export interface JobListItem {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'failed' | 'timeout';
  grabber?: string;
  submitted_at?: string;
}

export interface JobListResponse {
  jobs: JobListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobRerunResponse {
  new_job_id: string;
  original_job_id: string;
  status: string;
  message: string;
}
