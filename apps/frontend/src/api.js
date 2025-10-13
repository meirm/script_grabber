/**
 * API client for ScriptGrabber backend
 */
import axios from 'axios';
const API_BASE = '/api';
export const api = {
    /**
     * Submit a Python script for execution
     */
    async submitJob(file) {
        const formData = new FormData();
        formData.append('file', file);
        const response = await axios.post(`${API_BASE}/jobs`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },
    /**
     * Get status of a specific job
     */
    async getJobStatus(jobId) {
        const response = await axios.get(`${API_BASE}/jobs/${jobId}`);
        return response.data;
    },
    /**
     * List all jobs with optional filtering
     */
    async listJobs(status, page = 1, pageSize = 50) {
        const params = new URLSearchParams();
        if (status)
            params.append('status', status);
        params.append('page', page.toString());
        params.append('page_size', pageSize.toString());
        const response = await axios.get(`${API_BASE}/jobs?${params}`);
        return response.data;
    },
    /**
     * Get cluster status
     */
    async getClusterStatus() {
        const response = await axios.get(`${API_BASE}/status`);
        return response.data;
    },
    /**
     * Health check
     */
    async health() {
        const response = await axios.get(`${API_BASE}/health`);
        return response.data;
    },
    /**
     * Rerun an existing job
     */
    async rerunJob(jobId) {
        const response = await axios.post(`${API_BASE}/jobs/${jobId}/rerun`);
        return response.data;
    },
};
