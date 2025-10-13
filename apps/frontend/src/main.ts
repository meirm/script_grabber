/**
 * Main frontend application
 */

import { api } from './api';
import type { JobListItem, ClusterStatus } from './types';

// Auto-refresh interval (5 seconds)
const REFRESH_INTERVAL = 5000;

let refreshTimer: number | null = null;
let currentStatusFilter = '';

/**
 * Initialize the application
 */
async function init() {
  setupFileUpload();
  setupFilters();
  setupRefreshButton();
  setupJobDetailsHandlers();
  setupBackButton();

  // Initial load
  await Promise.all([
    refreshClusterStatus(),
    refreshJobList(),
  ]);

  // Start auto-refresh
  startAutoRefresh();
}

/**
 * Setup file upload functionality
 */
function setupFileUpload() {
  const dropZone = document.getElementById('drop-zone')!;
  const fileInput = document.getElementById('file-input') as HTMLInputElement;

  // Click to browse
  dropZone.addEventListener('click', () => {
    fileInput.click();
  });

  // File selected
  fileInput.addEventListener('change', async () => {
    const file = fileInput.files?.[0];
    if (file) {
      await handleFileUpload(file);
      fileInput.value = ''; // Reset input
    }
  });

  // Drag & drop
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');

    const file = e.dataTransfer?.files?.[0];
    if (file) {
      await handleFileUpload(file);
    }
  });
}

/**
 * Handle file upload
 */
async function handleFileUpload(file: File) {
  const statusDiv = document.getElementById('upload-status')!;

  // Validate file
  if (!file.name.endsWith('.py')) {
    showMessage(statusDiv, 'error', 'Please select a Python (.py) file');
    return;
  }

  if (file.size > 10 * 1024 * 1024) {
    showMessage(statusDiv, 'error', 'File too large. Maximum size is 10MB');
    return;
  }

  try {
    showMessage(statusDiv, 'info', 'Uploading...');

    const response = await api.submitJob(file);

    showMessage(
      statusDiv,
      'success',
      `Job submitted successfully! Job ID: ${response.job_id}`
    );

    // Refresh lists
    await Promise.all([
      refreshClusterStatus(),
      refreshJobList(),
    ]);

  } catch (error: any) {
    const message = error.response?.data?.detail || error.message || 'Upload failed';
    showMessage(statusDiv, 'error', message);
  }
}

/**
 * Setup status filter
 */
function setupFilters() {
  const statusFilter = document.getElementById('status-filter') as HTMLSelectElement;

  statusFilter.addEventListener('change', () => {
    currentStatusFilter = statusFilter.value;
    refreshJobList();
  });
}

/**
 * Setup refresh button
 */
function setupRefreshButton() {
  const refreshBtn = document.getElementById('refresh-btn')!;

  refreshBtn.addEventListener('click', async () => {
    await Promise.all([
      refreshClusterStatus(),
      refreshJobList(),
    ]);
  });
}

/**
 * Setup job details handlers using event delegation
 */
function setupJobDetailsHandlers() {
  const jobsList = document.getElementById('jobs-list')!;

  jobsList.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;

    // Check if clicked element is a view details button
    if (target.tagName === 'BUTTON' && target.id.startsWith('view-')) {
      const jobId = target.id.replace('view-', '').replace('card-', '');
      navigateToJobDetails(jobId);
    }
  });
}

/**
 * Setup back button handler
 */
function setupBackButton() {
  const backBtn = document.getElementById('back-btn')!;
  backBtn.addEventListener('click', () => {
    navigateToMainView();
  });
}

/**
 * Refresh cluster status
 */
async function refreshClusterStatus() {
  const statusDiv = document.getElementById('cluster-status')!;

  try {
    const status: ClusterStatus = await api.getClusterStatus();

    statusDiv.innerHTML = `
      <div class="stat-card">
        <div class="stat-value">${status.active_grabbers.length}</div>
        <div class="stat-label">Active Grabbers</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${status.jobs_queued}</div>
        <div class="stat-label">Queued</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${status.jobs_running}</div>
        <div class="stat-label">Running</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${status.jobs_done}</div>
        <div class="stat-label">Done</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${status.jobs_failed}</div>
        <div class="stat-label">Failed</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${status.total_jobs}</div>
        <div class="stat-label">Total Jobs</div>
      </div>
    `;
  } catch (error) {
    statusDiv.innerHTML = '<div class="error">Failed to load cluster status</div>';
  }
}

/**
 * Refresh job list
 */
async function refreshJobList() {
  const jobsDiv = document.getElementById('jobs-list')!;

  try {
    const response = await api.listJobs(currentStatusFilter || undefined, 1, 100);

    if (response.jobs.length === 0) {
      jobsDiv.innerHTML = '<div class="loading">No jobs found</div>';
      return;
    }

    jobsDiv.innerHTML = `
      <table class="jobs-table">
        <thead>
          <tr>
            <th>Job ID</th>
            <th>Status</th>
            <th>Grabber</th>
            <th>Submitted</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${response.jobs.map(job => renderJobRow(job)).join('')}
        </tbody>
      </table>
      <div class="jobs-cards">
        ${response.jobs.map(job => renderJobCard(job)).join('')}
      </div>
    `;

    // Event listeners are handled by event delegation in setupJobDetailsHandlers()

  } catch (error) {
    jobsDiv.innerHTML = '<div class="error">Failed to load jobs</div>';
  }
}

/**
 * Render a job row (desktop table view)
 */
function renderJobRow(job: JobListItem): string {
  const submittedDate = job.submitted_at
    ? new Date(job.submitted_at).toLocaleString()
    : 'N/A';

  return `
    <tr>
      <td><code>${job.job_id}</code></td>
      <td><span class="status-badge status-${job.status}">${job.status}</span></td>
      <td>${job.grabber || '-'}</td>
      <td>${submittedDate}</td>
      <td>
        <button id="view-${job.job_id}" style="padding: 6px 12px; font-size: 0.9em;">
          View Details
        </button>
      </td>
    </tr>
  `;
}

/**
 * Render a job card (mobile card view)
 */
function renderJobCard(job: JobListItem): string {
  const submittedDate = job.submitted_at
    ? new Date(job.submitted_at).toLocaleString()
    : 'N/A';

  return `
    <div class="job-card">
      <div class="job-card-header">
        <div class="job-card-id">${job.job_id}</div>
      </div>
      <div class="job-card-body">
        <div class="job-card-field">
          <span class="job-card-label">Status:</span>
          <span class="job-card-value">
            <span class="status-badge status-${job.status}">${job.status}</span>
          </span>
        </div>
        <div class="job-card-field">
          <span class="job-card-label">Grabber:</span>
          <span class="job-card-value">${job.grabber || '-'}</span>
        </div>
        <div class="job-card-field">
          <span class="job-card-label">Submitted:</span>
          <span class="job-card-value">${submittedDate}</span>
        </div>
      </div>
      <div class="job-card-actions">
        <button id="view-card-${job.job_id}">View Details</button>
      </div>
    </div>
  `;
}

/**
 * Navigate to job details view
 */
async function navigateToJobDetails(jobId: string) {
  const mainView = document.getElementById('main-view')!;
  const detailsView = document.getElementById('details-view')!;
  const detailsContent = document.getElementById('job-details-content')!;

  // Show details view, hide main view
  mainView.style.display = 'none';
  detailsView.style.display = 'block';

  // Stop auto-refresh when viewing details
  stopAutoRefresh();

  // Scroll to top
  window.scrollTo(0, 0);

  // Load job details
  detailsContent.innerHTML = '<div class="loading">Loading job details...</div>';

  try {
    const job = await api.getJobStatus(jobId);
    renderJobDetails(job);
  } catch (error: any) {
    detailsContent.innerHTML = `<div class="error">Failed to load job details: ${error.message}</div>`;
  }
}

/**
 * Navigate back to main view
 */
function navigateToMainView() {
  const mainView = document.getElementById('main-view')!;
  const detailsView = document.getElementById('details-view')!;

  // Show main view, hide details view
  mainView.style.display = 'block';
  detailsView.style.display = 'none';

  // Restart auto-refresh
  startAutoRefresh();

  // Scroll to top
  window.scrollTo(0, 0);

  // Refresh job list
  refreshJobList();
}

/**
 * Render job details page
 */
function renderJobDetails(job: any) {
  const detailsContent = document.getElementById('job-details-content')!;

  const submittedDate = job.submitted_at
    ? new Date(job.submitted_at).toLocaleString()
    : 'N/A';

  const completedDate = job.completed_at
    ? new Date(job.completed_at).toLocaleString()
    : 'N/A';

  detailsContent.innerHTML = `
    <div class="detail-card">
      <div class="detail-row">
        <div class="detail-label">Job ID</div>
        <div class="detail-value"><code>${job.job_id}</code></div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Status</div>
        <div class="detail-value">
          <span class="status-badge status-${job.status}">${job.status}</span>
        </div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Grabber</div>
        <div class="detail-value">${job.grabber || 'N/A'}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Submitted At</div>
        <div class="detail-value">${submittedDate}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Completed At</div>
        <div class="detail-value">${completedDate}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Exit Code</div>
        <div class="detail-value">${job.exit_code !== null ? job.exit_code : 'N/A'}</div>
      </div>
    </div>

    <div class="output-section">
      <h3>Standard Output (stdout)</h3>
      <div class="output-box ${!job.stdout ? 'empty' : ''}">
${job.stdout || '(empty)'}
      </div>
    </div>

    <div class="output-section">
      <h3>Standard Error (stderr)</h3>
      <div class="output-box ${!job.stderr ? 'empty' : ''}">
${job.stderr || '(empty)'}
      </div>
    </div>
  `;
}

/**
 * Show a message
 */
function showMessage(container: HTMLElement, type: 'info' | 'success' | 'error', message: string) {
  const className = type === 'error' ? 'error' : type === 'success' ? 'success' : 'info';
  container.innerHTML = `<div class="${className}">${message}</div>`;

  // Auto-clear after 5 seconds
  setTimeout(() => {
    container.innerHTML = '';
  }, 5000);
}

/**
 * Start auto-refresh
 */
function startAutoRefresh() {
  if (refreshTimer) return;

  refreshTimer = window.setInterval(async () => {
    await Promise.all([
      refreshClusterStatus(),
      refreshJobList(),
    ]);
  }, REFRESH_INTERVAL);
}

/**
 * Stop auto-refresh
 */
function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

// Initialize on page load
init();

// Stop auto-refresh when page is hidden
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    stopAutoRefresh();
  } else {
    startAutoRefresh();
  }
});
