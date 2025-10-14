/**
 * Main frontend application
 */
import { api } from './api';
// Auto-refresh interval (5 seconds)
const REFRESH_INTERVAL = 5000;
let refreshTimer = null;
let currentStatusFilter = 'active'; // Default to showing only queued and running
let currentArchivedStatusFilter = '';
let currentView = 'active';
/**
 * Initialize the application
 */
async function init() {
    setupFileUpload();
    setupFilters();
    setupRefreshButton();
    setupJobDetailsHandlers();
    setupRerunHandlers();
    setupBackButton();
    setupArchiveHandlers();
    setupBulkArchiveHandlers();
    setupTabNavigation();
    setupScriptViewerHandlers();
    setupStaleJobHandlers();
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
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
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
async function handleFileUpload(file) {
    const statusDiv = document.getElementById('upload-status');
    // File upload - no type restrictions
    if (file.size > 10 * 1024 * 1024) {
        showMessage(statusDiv, 'error', 'File too large. Maximum size is 10MB');
        return;
    }
    try {
        showMessage(statusDiv, 'info', 'Uploading...');
        const response = await api.submitJob(file);
        showMessage(statusDiv, 'success', `Job submitted successfully! Job ID: ${response.job_id}`);
        // Refresh lists
        await Promise.all([
            refreshClusterStatus(),
            refreshJobList(),
        ]);
    }
    catch (error) {
        const message = error.response?.data?.detail || error.message || 'Upload failed';
        showMessage(statusDiv, 'error', message);
    }
}
/**
 * Setup status filter
 */
function setupFilters() {
    const statusFilter = document.getElementById('status-filter');
    const archivedStatusFilter = document.getElementById('archived-status-filter');
    statusFilter.addEventListener('change', () => {
        currentStatusFilter = statusFilter.value;
        refreshJobList();
    });
    archivedStatusFilter.addEventListener('change', () => {
        currentArchivedStatusFilter = archivedStatusFilter.value;
        refreshArchivedJobList();
    });
}
/**
 * Setup refresh button
 */
function setupRefreshButton() {
    const refreshBtn = document.getElementById('refresh-btn');
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
    const jobsList = document.getElementById('jobs-list');
    const archivedJobsList = document.getElementById('archived-jobs-list');
    // Handle active jobs
    jobsList.addEventListener('click', (e) => {
        const target = e.target;
        // Check if clicked element is a view details button (but not view-script)
        if (target.tagName === 'BUTTON' && target.id.startsWith('view-') && !target.id.startsWith('view-script-')) {
            const jobId = target.id.replace('view-', '').replace('card-', '');
            navigateToJobDetails(jobId, false);
        }
    });
    // Handle archived jobs - show script instead of full details
    archivedJobsList.addEventListener('click', async (e) => {
        const target = e.target;
        // Check if clicked element is a view details button (but not view-script)
        if (target.tagName === 'BUTTON' && target.id.startsWith('view-') && !target.id.startsWith('view-script-')) {
            const jobId = target.id.replace('view-', '').replace('card-', '');
            // For archived jobs, show script viewer since full details aren't available
            await showJobScript(jobId, true);
        }
    });
}
/**
 * Setup rerun handlers using event delegation
 */
function setupRerunHandlers() {
    // Handler for rerun buttons in job list
    const jobsList = document.getElementById('jobs-list');
    jobsList.addEventListener('click', (e) => {
        const target = e.target;
        // Check if clicked element is a rerun button
        if (target.tagName === 'BUTTON' && target.id.startsWith('rerun-')) {
            const jobId = target.id.replace('rerun-', '').replace('card-', '');
            handleJobRerun(jobId);
        }
    });
    // Handler for rerun button in details view
    const detailsContent = document.getElementById('job-details-content');
    detailsContent.addEventListener('click', (e) => {
        const target = e.target;
        // Check if clicked element is the details rerun button
        if (target.id === 'rerun-details-btn') {
            const jobId = target.getAttribute('data-job-id');
            if (jobId) {
                handleJobRerun(jobId);
            }
        }
    });
}
/**
 * Handle job rerun
 */
async function handleJobRerun(jobId) {
    // Show confirmation dialog
    const confirmed = confirm(`Are you sure you want to rerun job "${jobId}"?`);
    if (!confirmed) {
        return;
    }
    const rerunMessageDiv = document.getElementById('rerun-message');
    try {
        // Show loading message
        if (rerunMessageDiv) {
            showMessage(rerunMessageDiv, 'info', 'Rerunning job...');
        }
        const response = await api.rerunJob(jobId);
        // Show success message
        if (rerunMessageDiv) {
            showMessage(rerunMessageDiv, 'success', `${response.message} Click <a href="#" id="view-new-job" style="color: inherit; text-decoration: underline;">here</a> to view the new job.`);
            // Add click handler for the link
            const viewNewJobLink = document.getElementById('view-new-job');
            if (viewNewJobLink) {
                viewNewJobLink.addEventListener('click', (e) => {
                    e.preventDefault();
                    navigateToJobDetails(response.new_job_id);
                });
            }
        }
        // Refresh cluster status and job list
        await Promise.all([
            refreshClusterStatus(),
            refreshJobList(),
        ]);
    }
    catch (error) {
        const message = error.response?.data?.detail || error.message || 'Rerun failed';
        if (rerunMessageDiv) {
            showMessage(rerunMessageDiv, 'error', message);
        }
    }
}
/**
 * Setup back button handler
 */
function setupBackButton() {
    const backBtn = document.getElementById('back-btn');
    backBtn.addEventListener('click', () => {
        navigateToMainView();
    });
}
/**
 * Refresh cluster status
 */
async function refreshClusterStatus() {
    const statusDiv = document.getElementById('cluster-status');
    try {
        const status = await api.getClusterStatus();
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
    }
    catch (error) {
        statusDiv.innerHTML = '<div class="error">Failed to load cluster status</div>';
    }
}
/**
 * Refresh job list
 */
async function refreshJobList() {
    const jobsDiv = document.getElementById('jobs-list');
    try {
        let allJobs = [];
        // Handle special "active" filter (queued + running only)
        if (currentStatusFilter === 'active') {
            // Fetch queued and running jobs in parallel
            const [queuedResponse, runningResponse] = await Promise.all([
                api.listJobs('queued', 1, 100),
                api.listJobs('running', 1, 100)
            ]);
            allJobs = [...queuedResponse.jobs, ...runningResponse.jobs];
            // Sort by submission time (newest first)
            allJobs.sort((a, b) => {
                const timeA = a.submitted_at ? new Date(a.submitted_at).getTime() : 0;
                const timeB = b.submitted_at ? new Date(b.submitted_at).getTime() : 0;
                return timeB - timeA;
            });
        }
        else {
            // Regular filter
            const response = await api.listJobs(currentStatusFilter || undefined, 1, 100);
            allJobs = response.jobs;
        }
        if (allJobs.length === 0) {
            jobsDiv.innerHTML = '<div class="loading">No jobs found</div>';
            return;
        }
        jobsDiv.innerHTML = `
      <table class="jobs-table">
        <thead>
          <tr>
            <th style="width: 40px;"></th>
            <th>Job ID</th>
            <th>Status</th>
            <th>Grabber</th>
            <th>Submitted</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${allJobs.map(job => renderJobRow(job)).join('')}
        </tbody>
      </table>
      <div class="jobs-cards">
        ${allJobs.map(job => renderJobCard(job)).join('')}
      </div>
    `;
        // Event listeners are handled by event delegation in setupJobDetailsHandlers()
    }
    catch (error) {
        jobsDiv.innerHTML = '<div class="error">Failed to load jobs</div>';
    }
}
/**
 * Render a job row (desktop table view)
 */
function renderJobRow(job) {
    const submittedDate = job.submitted_at
        ? new Date(job.submitted_at).toLocaleString()
        : 'N/A';
    // Show rerun button for terminal states
    const showRerunButton = ['done', 'failed', 'timeout'].includes(job.status);
    const rerunButtonHtml = showRerunButton
        ? `<button id="rerun-${job.job_id}" class="rerun-btn" style="padding: 6px 12px; font-size: 0.9em; margin-left: 8px;">🔄</button>`
        : '';
    // Show archive button for terminal states and stale
    const showArchiveButton = ['done', 'failed', 'timeout', 'stale'].includes(job.status);
    const archiveButtonHtml = showArchiveButton
        ? `<button id="archive-${job.job_id}" class="archive-btn">📦</button>`
        : '';
    // Show checkbox for archivable jobs
    const checkboxHtml = showArchiveButton
        ? `<input type="checkbox" class="job-checkbox" data-job-id="${job.job_id}" />`
        : '';
    return `
    <tr>
      <td>${checkboxHtml}</td>
      <td><code>${job.job_id}</code></td>
      <td><span class="status-badge status-${job.status}">${job.status}</span></td>
      <td>${job.grabber || '-'}</td>
      <td>${submittedDate}</td>
      <td>
        <button id="view-${job.job_id}" style="padding: 6px 12px; font-size: 0.9em;">
          View Details
        </button>
        <button id="view-script-${job.job_id}" style="padding: 6px 12px; font-size: 0.9em; margin-left: 8px;">
          📄
        </button>
        ${rerunButtonHtml}
        ${archiveButtonHtml}
      </td>
    </tr>
  `;
}
/**
 * Render a job card (mobile card view)
 */
function renderJobCard(job) {
    const submittedDate = job.submitted_at
        ? new Date(job.submitted_at).toLocaleString()
        : 'N/A';
    // Show rerun button for terminal states
    const showRerunButton = ['done', 'failed', 'timeout'].includes(job.status);
    const rerunButtonHtml = showRerunButton
        ? `<button id="rerun-card-${job.job_id}" class="rerun-btn">🔄 Rerun</button>`
        : '';
    // Show archive button for terminal states and stale
    const showArchiveButton = ['done', 'failed', 'timeout', 'stale'].includes(job.status);
    const archiveButtonHtml = showArchiveButton
        ? `<button id="archive-card-${job.job_id}" class="archive-btn">📦 Archive</button>`
        : '';
    // Show checkbox for archivable jobs
    const checkboxHtml = showArchiveButton
        ? `<input type="checkbox" class="job-checkbox" data-job-id="${job.job_id}" style="margin-bottom: 10px;" />`
        : '';
    return `
    <div class="job-card">
      <div class="job-card-header">
        ${checkboxHtml}
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
        <button id="view-script-card-${job.job_id}">📄</button>
        ${rerunButtonHtml}
        ${archiveButtonHtml}
      </div>
    </div>
  `;
}
/**
 * Navigate to job details view
 */
async function navigateToJobDetails(jobId, isArchived = false) {
    const mainView = document.getElementById('main-view');
    const detailsView = document.getElementById('details-view');
    const detailsContent = document.getElementById('job-details-content');
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
    }
    catch (error) {
        detailsContent.innerHTML = `<div class="error">Failed to load job details: ${error.message}</div>`;
    }
}
/**
 * Navigate back to main view
 */
function navigateToMainView() {
    const mainView = document.getElementById('main-view');
    const detailsView = document.getElementById('details-view');
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
function renderJobDetails(job) {
    const detailsContent = document.getElementById('job-details-content');
    const submittedDate = job.submitted_at
        ? new Date(job.submitted_at).toLocaleString()
        : 'N/A';
    const completedDate = job.completed_at
        ? new Date(job.completed_at).toLocaleString()
        : 'N/A';
    // Show rerun button for terminal states (done, failed, timeout)
    const showRerunButton = ['done', 'failed', 'timeout'].includes(job.status);
    const rerunButtonHtml = showRerunButton
        ? `<button id="rerun-details-btn" class="rerun-btn" data-job-id="${job.job_id}">🔄 Rerun Job</button>`
        : '';
    // Show archive button for terminal states and stale
    const showArchiveButton = ['done', 'failed', 'timeout', 'stale'].includes(job.status);
    const archiveButtonHtml = showArchiveButton
        ? `<button id="archive-details-btn" class="archive-btn" data-job-id="${job.job_id}">📦 Archive</button>`
        : '';
    // View script button (always shown)
    const viewScriptButtonHtml = `<button id="view-script-details-btn" style="padding: 10px 20px;" data-job-id="${job.job_id}" data-is-archived="${job.is_archived || false}">📄 View Script</button>`;
    detailsContent.innerHTML = `
    <div class="details-header-buttons">
      ${viewScriptButtonHtml}
      ${rerunButtonHtml}
      ${archiveButtonHtml}
    </div>

    <div id="rerun-message" class="rerun-message"></div>

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
function showMessage(container, type, message) {
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
    if (refreshTimer)
        return;
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
/**
 * Setup tab navigation between active and archived jobs
 */
function setupTabNavigation() {
    const activeTab = document.getElementById('active-tab');
    const archivedTab = document.getElementById('archived-tab');
    const activeView = document.getElementById('active-jobs-view');
    const archivedView = document.getElementById('archived-jobs-view');
    const staleDetection = document.getElementById('stale-jobs-detection');
    activeTab.addEventListener('click', () => {
        currentView = 'active';
        activeTab.classList.add('active');
        archivedTab.classList.remove('active');
        activeView.style.display = 'block';
        archivedView.style.display = 'none';
        staleDetection.style.display = 'block';
        refreshJobList();
    });
    archivedTab.addEventListener('click', () => {
        currentView = 'archived';
        archivedTab.classList.add('active');
        activeTab.classList.remove('active');
        archivedView.style.display = 'block';
        activeView.style.display = 'none';
        staleDetection.style.display = 'none';
        refreshArchivedJobList();
    });
}
/**
 * Setup archive button handlers using event delegation
 */
function setupArchiveHandlers() {
    const jobsList = document.getElementById('jobs-list');
    const archivedJobsList = document.getElementById('archived-jobs-list');
    const detailsContent = document.getElementById('job-details-content');
    // Handle archive buttons in active jobs list
    jobsList.addEventListener('click', async (e) => {
        const target = e.target;
        if (target.tagName === 'BUTTON' && target.id.startsWith('archive-')) {
            const jobId = target.id.replace('archive-', '').replace('card-', '');
            await handleJobArchive(jobId);
        }
    });
    // Handle archive buttons in archived jobs (for script view)
    archivedJobsList.addEventListener('click', async (e) => {
        const target = e.target;
        if (target.tagName === 'BUTTON' && target.id.startsWith('view-script-')) {
            const jobId = target.id.replace('view-script-', '').replace('card-', '');
            await showJobScript(jobId, true);
        }
    });
    // Handle archive button in details view
    detailsContent.addEventListener('click', async (e) => {
        const target = e.target;
        if (target.id === 'archive-details-btn') {
            const jobId = target.getAttribute('data-job-id');
            if (jobId) {
                await handleJobArchive(jobId);
                // After successful archive, go back to main view
                navigateToMainView();
            }
        }
    });
}
/**
 * Setup bulk archive handlers
 */
function setupBulkArchiveHandlers() {
    const selectAllCheckbox = document.getElementById('select-all-jobs');
    const bulkArchiveBtn = document.getElementById('bulk-archive-btn');
    const jobsList = document.getElementById('jobs-list');
    // Handle select all checkbox
    selectAllCheckbox.addEventListener('change', () => {
        const checkboxes = document.querySelectorAll('.job-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = selectAllCheckbox.checked;
        });
        updateBulkArchiveButton();
    });
    // Handle individual checkbox changes via delegation
    jobsList.addEventListener('change', (e) => {
        const target = e.target;
        if (target.classList.contains('job-checkbox')) {
            updateBulkArchiveButton();
        }
    });
    // Handle bulk archive button
    bulkArchiveBtn.addEventListener('click', async () => {
        await handleBulkArchive();
    });
}
/**
 * Update bulk archive button state
 */
function updateBulkArchiveButton() {
    const checkboxes = document.querySelectorAll('.job-checkbox:checked');
    const bulkArchiveBtn = document.getElementById('bulk-archive-btn');
    const count = checkboxes.length;
    bulkArchiveBtn.textContent = `📦 Archive Selected (${count})`;
    bulkArchiveBtn.disabled = count === 0;
}
/**
 * Setup script viewer handlers
 */
function setupScriptViewerHandlers() {
    const jobsList = document.getElementById('jobs-list');
    const archivedJobsList = document.getElementById('archived-jobs-list');
    const closeBtn = document.getElementById('close-script-viewer');
    const closeDetailsBtn = document.getElementById('close-details-script-viewer');
    const detailsContent = document.getElementById('job-details-content');
    // Handle view script buttons in active jobs
    jobsList.addEventListener('click', async (e) => {
        const target = e.target;
        if (target.tagName === 'BUTTON' && target.id.startsWith('view-script-')) {
            const jobId = target.id.replace('view-script-', '').replace('card-', '');
            await showJobScript(jobId, false);
        }
    });
    // Handle view script buttons in archived jobs
    archivedJobsList.addEventListener('click', async (e) => {
        const target = e.target;
        if (target.tagName === 'BUTTON' && target.id.startsWith('view-script-')) {
            const jobId = target.id.replace('view-script-', '').replace('card-', '');
            await showJobScript(jobId, true);
        }
    });
    // Handle view script button in details view
    detailsContent.addEventListener('click', async (e) => {
        const target = e.target;
        if (target.id === 'view-script-details-btn') {
            const jobId = target.getAttribute('data-job-id');
            const isArchived = target.getAttribute('data-is-archived') === 'true';
            if (jobId) {
                await showJobScriptInDetails(jobId, isArchived);
            }
        }
    });
    // Close script viewer
    closeBtn.addEventListener('click', () => {
        document.getElementById('script-viewer').style.display = 'none';
    });
    closeDetailsBtn.addEventListener('click', () => {
        document.getElementById('details-script-viewer').style.display = 'none';
    });
}
/**
 * Setup stale job detection handlers
 */
function setupStaleJobHandlers() {
    const detectBtn = document.getElementById('detect-stale-btn');
    const staleJobsList = document.getElementById('stale-jobs-list');
    detectBtn.addEventListener('click', async () => {
        await detectAndDisplayStaleJobs();
    });
    // Handle status update buttons via delegation
    staleJobsList.addEventListener('click', async (e) => {
        const target = e.target;
        if (target.tagName === 'BUTTON' && target.id.startsWith('mark-stale-')) {
            const jobId = target.id.replace('mark-stale-', '');
            await handleStatusUpdate(jobId, 'stale');
        }
        if (target.tagName === 'BUTTON' && target.id.startsWith('mark-failed-')) {
            const jobId = target.id.replace('mark-failed-', '');
            await handleStatusUpdate(jobId, 'failed');
        }
    });
}
/**
 * Handle single job archive
 */
async function handleJobArchive(jobId) {
    const messageDiv = document.getElementById('upload-status');
    try {
        showMessage(messageDiv, 'info', `Archiving job ${jobId}...`);
        const response = await api.archiveJob(jobId);
        showMessage(messageDiv, 'success', response.message);
        // Refresh job list
        await Promise.all([
            refreshClusterStatus(),
            refreshJobList(),
        ]);
    }
    catch (error) {
        const message = error.response?.data?.detail || error.message || 'Archive failed';
        showMessage(messageDiv, 'error', message);
    }
}
/**
 * Handle bulk archive
 */
async function handleBulkArchive() {
    const checkboxes = document.querySelectorAll('.job-checkbox:checked');
    const jobIds = Array.from(checkboxes).map(cb => cb.getAttribute('data-job-id'));
    if (jobIds.length === 0) {
        return;
    }
    const messageDiv = document.getElementById('upload-status');
    try {
        showMessage(messageDiv, 'info', `Archiving ${jobIds.length} jobs...`);
        const response = await api.archiveBulkJobs(jobIds);
        showMessage(messageDiv, 'success', `Archived ${response.archived_count} jobs successfully. ${response.failed_count} failed.`);
        // Clear selections
        const selectAllCheckbox = document.getElementById('select-all-jobs');
        selectAllCheckbox.checked = false;
        updateBulkArchiveButton();
        // Refresh job list
        await Promise.all([
            refreshClusterStatus(),
            refreshJobList(),
        ]);
    }
    catch (error) {
        const message = error.response?.data?.detail || error.message || 'Bulk archive failed';
        showMessage(messageDiv, 'error', message);
    }
}
/**
 * Refresh archived job list
 */
async function refreshArchivedJobList() {
    const archivedJobsDiv = document.getElementById('archived-jobs-list');
    try {
        const response = await api.listArchivedJobs(currentArchivedStatusFilter || undefined, 1, 100);
        if (response.jobs.length === 0) {
            archivedJobsDiv.innerHTML = '<div class="loading">No archived jobs found</div>';
            return;
        }
        archivedJobsDiv.innerHTML = `
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
          ${response.jobs.map(job => renderArchivedJobRow(job)).join('')}
        </tbody>
      </table>
      <div class="jobs-cards">
        ${response.jobs.map(job => renderArchivedJobCard(job)).join('')}
      </div>
    `;
    }
    catch (error) {
        archivedJobsDiv.innerHTML = '<div class="error">Failed to load archived jobs</div>';
    }
}
/**
 * Render archived job row
 */
function renderArchivedJobRow(job) {
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
        <button id="view-script-${job.job_id}" style="padding: 6px 12px; font-size: 0.9em; margin-left: 8px;">
          📄 Script
        </button>
      </td>
    </tr>
  `;
}
/**
 * Render archived job card
 */
function renderArchivedJobCard(job) {
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
        <button id="view-script-card-${job.job_id}">📄 Script</button>
      </div>
    </div>
  `;
}
/**
 * Show job script content
 */
async function showJobScript(jobId, isArchived) {
    const scriptViewer = document.getElementById('script-viewer');
    const scriptMeta = document.getElementById('script-meta');
    const scriptContent = document.getElementById('script-content');
    try {
        scriptMeta.innerHTML = '<div class="loading">Loading script...</div>';
        scriptContent.textContent = '';
        scriptViewer.style.display = 'block';
        const script = await api.readJobScript(jobId, isArchived);
        scriptMeta.innerHTML = `
      <strong>File:</strong> ${script.filename} |
      <strong>Size:</strong> ${(script.size / 1024).toFixed(2)} KB
    `;
        scriptContent.textContent = script.content;
    }
    catch (error) {
        const message = error.response?.data?.detail || error.message || 'Failed to load script';
        scriptMeta.innerHTML = `<div class="error">${message}</div>`;
        scriptContent.textContent = '';
    }
}
/**
 * Show job script in details view
 */
async function showJobScriptInDetails(jobId, isArchived) {
    const scriptViewer = document.getElementById('details-script-viewer');
    const scriptMeta = document.getElementById('details-script-meta');
    const scriptContent = document.getElementById('details-script-content');
    try {
        scriptMeta.innerHTML = '<div class="loading">Loading script...</div>';
        scriptContent.textContent = '';
        scriptViewer.style.display = 'block';
        const script = await api.readJobScript(jobId, isArchived);
        scriptMeta.innerHTML = `
      <strong>File:</strong> ${script.filename} |
      <strong>Size:</strong> ${(script.size / 1024).toFixed(2)} KB
    `;
        scriptContent.textContent = script.content;
    }
    catch (error) {
        const message = error.response?.data?.detail || error.message || 'Failed to load script';
        scriptMeta.innerHTML = `<div class="error">${message}</div>`;
        scriptContent.textContent = '';
    }
}
/**
 * Detect and display stale jobs
 */
async function detectAndDisplayStaleJobs() {
    const staleJobsList = document.getElementById('stale-jobs-list');
    const messageDiv = document.getElementById('upload-status');
    try {
        staleJobsList.innerHTML = '<div class="loading">Detecting stale jobs...</div>';
        const response = await api.detectStaleJobs();
        if (response.count === 0) {
            staleJobsList.innerHTML = '<div class="info">No stale jobs detected. All running jobs have active grabbers.</div>';
            return;
        }
        staleJobsList.innerHTML = `
      <div class="stale-jobs-section">
        <h3>⚠️ Found ${response.count} Stale Job(s)</h3>
        ${response.stale_jobs.map(job => `
          <div class="stale-job-item">
            <div class="stale-job-info">
              <strong>${job.job_id}</strong>
              <small>Grabber: ${job.grabber} | Runtime: ${job.runtime_duration ? (job.runtime_duration / 60).toFixed(1) + ' minutes' : 'N/A'}</small>
            </div>
            <div class="stale-job-actions">
              <button id="mark-stale-${job.job_id}" class="stale-btn">Mark as Stale</button>
              <button id="mark-failed-${job.job_id}" class="failed-btn">Mark as Failed</button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
    }
    catch (error) {
        const message = error.response?.data?.detail || error.message || 'Failed to detect stale jobs';
        staleJobsList.innerHTML = `<div class="error">${message}</div>`;
    }
}
/**
 * Handle status update (mark as stale or failed)
 */
async function handleStatusUpdate(jobId, action) {
    const messageDiv = document.getElementById('upload-status');
    try {
        showMessage(messageDiv, 'info', `Updating job status to ${action}...`);
        const response = action === 'stale'
            ? await api.markJobAsStale(jobId)
            : await api.markJobAsFailed(jobId);
        showMessage(messageDiv, 'success', response.message);
        // Refresh stale jobs list and job list
        await Promise.all([
            detectAndDisplayStaleJobs(),
            refreshJobList(),
        ]);
    }
    catch (error) {
        const message = error.response?.data?.detail || error.message || 'Status update failed';
        showMessage(messageDiv, 'error', message);
    }
}
// Initialize on page load
init();
// Stop auto-refresh when page is hidden
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        stopAutoRefresh();
    }
    else {
        startAutoRefresh();
    }
});
