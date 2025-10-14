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
  status: 'queued' | 'running' | 'done' | 'failed' | 'timeout' | 'not_found' | 'stale';
  grabber?: string;
  submitted_at?: string;
  completed_at?: string;
  stdout?: string;
  stderr?: string;
  exit_code?: number;
  is_archived?: boolean;
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
  status: 'queued' | 'running' | 'done' | 'failed' | 'timeout' | 'stale';
  grabber?: string;
  submitted_at?: string;
  is_archived?: boolean;
  is_stale?: boolean;
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

export interface JobArchiveResponse {
  job_id: string;
  status: string;
  message: string;
  archived_at?: string;
}

export interface BulkArchiveResponse {
  archived_count: number;
  failed_count: number;
  results: Array<{
    job_id: string;
    status: string;
    message: string;
  }>;
}

export interface JobScriptContent {
  job_id: string;
  filename: string;
  content: string;
  size: number;
}

export interface StaleJobInfo {
  job_id: string;
  grabber: string;
  runtime_duration?: number;
  submitted_at?: string;
}

export interface StaleJobDetectionResponse {
  stale_jobs: StaleJobInfo[];
  count: number;
}

export interface JobStatusUpdateResponse {
  job_id: string;
  old_status: string;
  new_status: string;
  message: string;
}
