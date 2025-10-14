/**
 * API client for ScriptGrabber backend
 */

import axios from 'axios';
import type {
  JobSubmitResponse,
  JobStatus,
  ClusterStatus,
  JobListResponse,
  JobRerunResponse,
  JobArchiveResponse,
  BulkArchiveResponse,
  JobScriptContent,
  StaleJobDetectionResponse,
  JobStatusUpdateResponse,
} from './types';

const API_BASE = '/api';

export const api = {
  /**
   * Submit a Python script for execution
   */
  async submitJob(file: File): Promise<JobSubmitResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axios.post<JobSubmitResponse>(
      `${API_BASE}/jobs`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  /**
   * Get status of a specific job
   */
  async getJobStatus(jobId: string): Promise<JobStatus> {
    const response = await axios.get<JobStatus>(`${API_BASE}/jobs/${jobId}`);
    return response.data;
  },

  /**
   * List all jobs with optional filtering
   */
  async listJobs(
    status?: string,
    page: number = 1,
    pageSize: number = 50
  ): Promise<JobListResponse> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    const response = await axios.get<JobListResponse>(`${API_BASE}/jobs?${params}`);
    return response.data;
  },

  /**
   * Get cluster status
   */
  async getClusterStatus(): Promise<ClusterStatus> {
    const response = await axios.get<ClusterStatus>(`${API_BASE}/status`);
    return response.data;
  },

  /**
   * Health check
   */
  async health(): Promise<{ status: string }> {
    const response = await axios.get(`${API_BASE}/health`);
    return response.data;
  },

  /**
   * Rerun an existing job
   */
  async rerunJob(jobId: string): Promise<JobRerunResponse> {
    const response = await axios.post<JobRerunResponse>(
      `${API_BASE}/jobs/${jobId}/rerun`
    );
    return response.data;
  },

  /**
   * Archive a completed job
   */
  async archiveJob(jobId: string): Promise<JobArchiveResponse> {
    const response = await axios.post<JobArchiveResponse>(
      `${API_BASE}/jobs/${jobId}/archive`
    );
    return response.data;
  },

  /**
   * Archive multiple jobs in bulk
   */
  async archiveBulkJobs(jobIds: string[]): Promise<BulkArchiveResponse> {
    const response = await axios.post<BulkArchiveResponse>(
      `${API_BASE}/jobs/archive/bulk`,
      { job_ids: jobIds }
    );
    return response.data;
  },

  /**
   * List archived jobs
   */
  async listArchivedJobs(
    status?: string,
    page: number = 1,
    pageSize: number = 50
  ): Promise<JobListResponse> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    const response = await axios.get<JobListResponse>(
      `${API_BASE}/jobs/archived?${params}`
    );
    return response.data;
  },

  /**
   * Read job script content
   */
  async readJobScript(
    jobId: string,
    isArchived: boolean = false
  ): Promise<JobScriptContent> {
    const params = new URLSearchParams();
    params.append('is_archived', isArchived.toString());

    const response = await axios.get<JobScriptContent>(
      `${API_BASE}/jobs/${jobId}/script?${params}`
    );
    return response.data;
  },

  /**
   * Detect stale jobs (jobs with dead grabber processes)
   */
  async detectStaleJobs(): Promise<StaleJobDetectionResponse> {
    const response = await axios.get<StaleJobDetectionResponse>(
      `${API_BASE}/jobs/stale`
    );
    return response.data;
  },

  /**
   * Mark a RUNNING job as STALE
   */
  async markJobAsStale(jobId: string): Promise<JobStatusUpdateResponse> {
    const response = await axios.post<JobStatusUpdateResponse>(
      `${API_BASE}/jobs/${jobId}/mark-stale`
    );
    return response.data;
  },

  /**
   * Mark a RUNNING or STALE job as FAILED
   */
  async markJobAsFailed(jobId: string): Promise<JobStatusUpdateResponse> {
    const response = await axios.post<JobStatusUpdateResponse>(
      `${API_BASE}/jobs/${jobId}/mark-failed`
    );
    return response.data;
  },
};
