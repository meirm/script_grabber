"""Job management functionality for ScriptGrabber."""

import os
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import re
import aiofiles

from .models import (
    JobStatus, ClusterStatus, JobListItem, JobArchiveResponse,
    BulkArchiveResponse, JobScriptContent, StaleJobInfo,
    StaleJobDetectionResponse, JobStatusUpdateResponse
)


class JobManager:
    """Manages job submission, status, and cluster monitoring."""

    def __init__(self, cluster_path: str):
        """Initialize job manager with cluster path."""
        self.cluster_path = Path(cluster_path)
        self.queue_path = self.cluster_path / "queue"
        self.spool_path = self.cluster_path / "spool"
        self.log_path = self.cluster_path / "log"
        self.varlock_path = self.cluster_path / "varlock"
        self.archive_path = self.cluster_path / "archive"

        # Ensure directories exist
        self.queue_path.mkdir(parents=True, exist_ok=True)
        self.spool_path.mkdir(parents=True, exist_ok=True)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.varlock_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)

    async def submit_job(self, filename: str, content: bytes) -> str:
        """Submit a job to the queue.

        Args:
            filename: Original filename
            content: File content as bytes

        Returns:
            job_id: Unique job identifier
        """
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)

        # Generate unique job ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        job_id = f"{safe_filename}_{timestamp}"

        # Write to queue
        job_path = self.queue_path / job_id
        async with aiofiles.open(job_path, 'wb') as f:
            await f.write(content)

        return job_id

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal while preserving extension."""
        # Remove path separators and keep only safe characters
        safe = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        # Preserve original extension
        return safe

    async def get_job_status(self, job_id: str) -> JobStatus:
        """Get status of a specific job.

        Args:
            job_id: Job identifier

        Returns:
            JobStatus object with current status
        """
        # Check if job is in queue
        queue_file = self.queue_path / job_id
        if queue_file.exists():
            return JobStatus(
                job_id=job_id,
                status="queued",
                submitted_at=datetime.fromtimestamp(queue_file.stat().st_mtime)
            )

        # Search spool directories for job
        for grabber_spool in self.spool_path.glob("*"):
            if not grabber_spool.is_dir():
                continue

            grabber_name = grabber_spool.name

            # Check for job in various states
            for status_suffix, status_name in [
                ("-RUNNING", "running"),
                ("-DONE", "done"),
                ("-FAILED", "failed"),
                ("-TIMEOUT", "timeout"),
                ("-STALE", "stale"),
            ]:
                job_files = list(grabber_spool.glob(f"*{job_id}*{status_suffix}"))
                if job_files:
                    job_file = job_files[0]

                    # Read logs if available
                    # Log files are named {job_id}.out/.err/.log
                    stdout_file = self.log_path / f"{job_id}.out"
                    stderr_file = self.log_path / f"{job_id}.err"
                    log_file = self.log_path / f"{job_id}.log"

                    stdout_content = None
                    stderr_content = None
                    exit_code = None

                    if stdout_file.exists():
                        async with aiofiles.open(stdout_file, 'r') as f:
                            stdout_content = await f.read()

                    if stderr_file.exists():
                        async with aiofiles.open(stderr_file, 'r') as f:
                            stderr_content = await f.read()

                    if log_file.exists():
                        async with aiofiles.open(log_file, 'r') as f:
                            log_content = await f.read()
                            # Extract exit code from log
                            match = re.search(r'ExitCode\((\d+)\)', log_content)
                            if match:
                                exit_code = int(match.group(1))

                    return JobStatus(
                        job_id=job_id,
                        status=status_name,
                        grabber=grabber_name,
                        submitted_at=datetime.fromtimestamp(job_file.stat().st_ctime),
                        completed_at=datetime.fromtimestamp(job_file.stat().st_mtime) if status_name != "running" else None,
                        stdout=stdout_content,
                        stderr=stderr_content,
                        exit_code=exit_code
                    )

        # Job not found
        return JobStatus(
            job_id=job_id,
            status="not_found"
        )

    async def get_cluster_status(self) -> ClusterStatus:
        """Get overall cluster status.

        Returns:
            ClusterStatus with active grabbers and job counts
        """
        # Get active grabbers from lock files
        active_grabbers = []
        if self.varlock_path.exists():
            for lock_file in self.varlock_path.glob("*.lock"):
                grabber_name = lock_file.stem
                # Check if PID is still alive
                try:
                    async with aiofiles.open(lock_file, 'r') as f:
                        pid = int(await f.read())
                        # On Unix, os.kill with signal 0 checks if process exists
                        try:
                            os.kill(pid, 0)
                            active_grabbers.append(grabber_name)
                        except OSError:
                            pass  # Process not running
                except (ValueError, FileNotFoundError):
                    pass

        # Count jobs in queue (all files)
        jobs_queued = len(list(self.queue_path.glob("*")))

        # Count jobs in various states across all spools
        jobs_running = 0
        jobs_done = 0
        jobs_failed = 0
        jobs_timeout = 0

        if self.spool_path.exists():
            for grabber_spool in self.spool_path.glob("*"):
                if not grabber_spool.is_dir():
                    continue
                jobs_running += len(list(grabber_spool.glob("*-RUNNING")))
                jobs_done += len(list(grabber_spool.glob("*-DONE")))
                jobs_failed += len(list(grabber_spool.glob("*-FAILED")))
                jobs_timeout += len(list(grabber_spool.glob("*-TIMEOUT")))

        total_jobs = jobs_queued + jobs_running + jobs_done + jobs_failed + jobs_timeout

        return ClusterStatus(
            active_grabbers=active_grabbers,
            jobs_queued=jobs_queued,
            jobs_running=jobs_running,
            jobs_done=jobs_done,
            jobs_failed=jobs_failed,
            jobs_timeout=jobs_timeout,
            total_jobs=total_jobs
        )

    async def list_jobs(self, status_filter: Optional[str] = None, page: int = 1, page_size: int = 50) -> tuple[List[JobListItem], int]:
        """List all jobs with optional filtering and pagination.

        Args:
            status_filter: Filter by status (queued, running, done, failed, timeout)
            page: Page number (1-indexed)
            page_size: Number of jobs per page

        Returns:
            Tuple of (jobs list, total count)
        """
        all_jobs = []

        # Get queued jobs (all files)
        if not status_filter or status_filter == "queued":
            for job_file in self.queue_path.glob("*"):
                all_jobs.append(JobListItem(
                    job_id=job_file.name,
                    status="queued",
                    submitted_at=datetime.fromtimestamp(job_file.stat().st_mtime)
                ))

        # Get jobs from spools
        if self.spool_path.exists():
            for grabber_spool in self.spool_path.glob("*"):
                if not grabber_spool.is_dir():
                    continue
                grabber_name = grabber_spool.name

                for status_suffix, status_name in [
                    ("-RUNNING", "running"),
                    ("-DONE", "done"),
                    ("-FAILED", "failed"),
                    ("-TIMEOUT", "timeout"),
                    ("-STALE", "stale"),
                ]:
                    if status_filter and status_filter != status_name:
                        continue

                    for job_file in grabber_spool.glob(f"*{status_suffix}"):
                        # Extract original job ID
                        job_name = job_file.name.replace(status_suffix, "")
                        # Remove timestamp suffix added by grabber
                        job_id = re.sub(r'-\d{14}$', '', job_name)

                        all_jobs.append(JobListItem(
                            job_id=job_id,
                            status=status_name,
                            grabber=grabber_name,
                            submitted_at=datetime.fromtimestamp(job_file.stat().st_ctime),
                            is_archived=False,
                            is_stale=(status_name == "stale")
                        ))

        # Sort by submission time (newest first)
        all_jobs.sort(key=lambda x: x.submitted_at or datetime.min, reverse=True)

        # Pagination
        total = len(all_jobs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = all_jobs[start_idx:end_idx]

        return paginated_jobs, total

    async def rerun_job(self, job_id: str) -> tuple[str, str]:
        """Rerun an existing job by retrieving its script and resubmitting.

        Args:
            job_id: Original job identifier

        Returns:
            Tuple of (new_job_id, original_filename)

        Raises:
            FileNotFoundError: If job file cannot be found
            ValueError: If job_id is invalid
        """
        # Sanitize job_id to prevent path traversal
        if '..' in job_id or '/' in job_id or '\\' in job_id:
            raise ValueError(f"Invalid job_id: {job_id}")

        # Search for the job file in spool directories
        job_file_path = None

        if self.spool_path.exists():
            for grabber_spool in self.spool_path.glob("*"):
                if not grabber_spool.is_dir():
                    continue

                # Search for job with any terminal status suffix
                for status_suffix in ["-DONE", "-FAILED", "-TIMEOUT", "-RUNNING"]:
                    # Try to find files matching the pattern
                    matching_files = list(grabber_spool.glob(f"*{job_id}*{status_suffix}"))
                    if matching_files:
                        job_file_path = matching_files[0]
                        break

                if job_file_path:
                    break

        if not job_file_path or not job_file_path.exists():
            raise FileNotFoundError(f"Job file not found for job_id: {job_id}")

        # Read the original script content
        async with aiofiles.open(job_file_path, 'rb') as f:
            content = await f.read()

        # Extract original filename (remove timestamp and status suffix)
        # Job files are named like: script.py_20240101_120000_123456-20240101120001-DONE
        original_filename = job_id

        # Submit as a new job
        new_job_id = await self.submit_job(original_filename, content)

        return new_job_id, original_filename

    async def archive_job(self, job_id: str) -> JobArchiveResponse:
        """Archive a completed job.

        Args:
            job_id: Job identifier to archive

        Returns:
            JobArchiveResponse with status and details

        Raises:
            ValueError: If job_id is invalid or job is not in terminal state
            FileNotFoundError: If job cannot be found
        """
        # Sanitize job_id to prevent path traversal
        if '..' in job_id or '/' in job_id or '\\' in job_id:
            raise ValueError(f"Invalid job_id: {job_id}")

        # Find job in spool directories
        job_file_path = None
        grabber_name = None
        status_suffix = None

        if self.spool_path.exists():
            for grabber_spool in self.spool_path.glob("*"):
                if not grabber_spool.is_dir():
                    continue

                # Only archive terminal states or stale running jobs
                for suffix in ["-DONE", "-FAILED", "-TIMEOUT", "-STALE"]:
                    matching_files = list(grabber_spool.glob(f"*{job_id}*{suffix}"))
                    if matching_files:
                        job_file_path = matching_files[0]
                        grabber_name = grabber_spool.name
                        status_suffix = suffix
                        break

                if job_file_path:
                    break

        if not job_file_path or not grabber_name:
            raise FileNotFoundError(f"Job {job_id} not found or not in archivable state")

        # Create archive directory for this grabber
        archive_grabber_path = self.archive_path / grabber_name
        archive_grabber_path.mkdir(parents=True, exist_ok=True)

        # Move job file to archive
        archive_job_path = archive_grabber_path / job_file_path.name
        shutil.move(str(job_file_path), str(archive_job_path))

        # Move associated log files if they exist
        for log_ext in ['.out', '.err', '.log']:
            log_file = self.log_path / f"{job_id}{log_ext}"
            if log_file.exists():
                archive_log_path = archive_grabber_path / log_file.name
                shutil.move(str(log_file), str(archive_log_path))

        return JobArchiveResponse(
            job_id=job_id,
            status="success",
            message=f"Job {job_id} archived successfully",
            archived_at=datetime.now()
        )

    async def archive_jobs_bulk(self, job_ids: list[str]) -> BulkArchiveResponse:
        """Archive multiple jobs in bulk.

        Args:
            job_ids: List of job identifiers to archive

        Returns:
            BulkArchiveResponse with counts and detailed results
        """
        results = []
        archived_count = 0
        failed_count = 0

        for job_id in job_ids:
            try:
                response = await self.archive_job(job_id)
                results.append({
                    "job_id": job_id,
                    "status": "success",
                    "message": response.message
                })
                archived_count += 1
            except Exception as e:
                results.append({
                    "job_id": job_id,
                    "status": "failed",
                    "message": str(e)
                })
                failed_count += 1

        return BulkArchiveResponse(
            archived_count=archived_count,
            failed_count=failed_count,
            results=results
        )

    async def list_archived_jobs(
        self,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[JobListItem], int]:
        """List archived jobs with optional filtering and pagination.

        Args:
            status_filter: Filter by status (done, failed, timeout, stale)
            page: Page number (1-indexed)
            page_size: Number of jobs per page

        Returns:
            Tuple of (jobs list, total count)
        """
        all_archived_jobs = []

        if self.archive_path.exists():
            for grabber_archive in self.archive_path.glob("*"):
                if not grabber_archive.is_dir():
                    continue

                grabber_name = grabber_archive.name

                for status_suffix, status_name in [
                    ("-DONE", "done"),
                    ("-FAILED", "failed"),
                    ("-TIMEOUT", "timeout"),
                    ("-STALE", "stale"),
                ]:
                    if status_filter and status_filter != status_name:
                        continue

                    for job_file in grabber_archive.glob(f"*{status_suffix}"):
                        # Extract original job ID
                        job_name = job_file.name.replace(status_suffix, "")
                        job_id = re.sub(r'-\d{14}$', '', job_name)

                        all_archived_jobs.append(JobListItem(
                            job_id=job_id,
                            status=status_name,
                            grabber=grabber_name,
                            submitted_at=datetime.fromtimestamp(job_file.stat().st_ctime),
                            is_archived=True,
                            is_stale=(status_name == "stale")
                        ))

        # Sort by submission time (newest first)
        all_archived_jobs.sort(key=lambda x: x.submitted_at or datetime.min, reverse=True)

        # Pagination
        total = len(all_archived_jobs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = all_archived_jobs[start_idx:end_idx]

        return paginated_jobs, total

    async def read_job_script(self, job_id: str, is_archived: bool = False) -> JobScriptContent:
        """Read job script content.

        Args:
            job_id: Job identifier
            is_archived: Whether to search in archive or spool

        Returns:
            JobScriptContent with script details

        Raises:
            FileNotFoundError: If job file cannot be found
            ValueError: If job_id is invalid or file is too large
        """
        # Sanitize job_id to prevent path traversal
        if '..' in job_id or '/' in job_id or '\\' in job_id:
            raise ValueError(f"Invalid job_id: {job_id}")

        # Search in appropriate directory
        search_path = self.archive_path if is_archived else self.spool_path
        job_file_path = None

        if search_path.exists():
            for grabber_dir in search_path.glob("*"):
                if not grabber_dir.is_dir():
                    continue

                # Search for job with any status suffix
                for suffix in ["-RUNNING", "-DONE", "-FAILED", "-TIMEOUT", "-STALE", ""]:
                    matching_files = list(grabber_dir.glob(f"*{job_id}*{suffix}")) if suffix else list(grabber_dir.glob(f"*{job_id}*"))
                    if matching_files:
                        job_file_path = matching_files[0]
                        break

                if job_file_path:
                    break

        if not job_file_path or not job_file_path.exists():
            raise FileNotFoundError(f"Job script not found for job_id: {job_id}")

        # Check file size (10MB limit)
        file_size = job_file_path.stat().st_size
        if file_size > 10 * 1024 * 1024:
            raise ValueError(f"Script file too large: {file_size} bytes (10MB limit)")

        # Read file content
        try:
            async with aiofiles.open(job_file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
        except UnicodeDecodeError:
            raise ValueError("Cannot read binary file content")

        return JobScriptContent(
            job_id=job_id,
            filename=job_id,
            content=content,
            size=file_size
        )

    async def detect_stale_jobs(self) -> StaleJobDetectionResponse:
        """Detect jobs with dead grabber processes.

        Returns:
            StaleJobDetectionResponse with list of stale jobs
        """
        stale_jobs = []

        if self.spool_path.exists():
            for grabber_spool in self.spool_path.glob("*"):
                if not grabber_spool.is_dir():
                    continue

                grabber_name = grabber_spool.name

                # Check if grabber is alive
                lock_file = self.varlock_path / f"{grabber_name}.lock"
                grabber_alive = False

                if lock_file.exists():
                    try:
                        async with aiofiles.open(lock_file, 'r') as f:
                            pid = int(await f.read())
                            # Check if process exists
                            try:
                                os.kill(pid, 0)
                                grabber_alive = True
                            except OSError:
                                pass  # Process not running
                    except (ValueError, FileNotFoundError):
                        pass

                # If grabber is dead, all RUNNING jobs are stale
                if not grabber_alive:
                    for job_file in grabber_spool.glob("*-RUNNING"):
                        job_name = job_file.name.replace("-RUNNING", "")
                        job_id = re.sub(r'-\d{14}$', '', job_name)

                        # Calculate runtime duration
                        ctime = job_file.stat().st_ctime
                        mtime = job_file.stat().st_mtime
                        runtime_duration = mtime - ctime

                        stale_jobs.append(StaleJobInfo(
                            job_id=job_id,
                            grabber=grabber_name,
                            runtime_duration=runtime_duration,
                            submitted_at=datetime.fromtimestamp(ctime)
                        ))

        return StaleJobDetectionResponse(
            stale_jobs=stale_jobs,
            count=len(stale_jobs)
        )

    async def mark_job_as_stale(self, job_id: str) -> JobStatusUpdateResponse:
        """Mark a RUNNING job as STALE.

        Args:
            job_id: Job identifier

        Returns:
            JobStatusUpdateResponse with status change details

        Raises:
            FileNotFoundError: If job not found
            ValueError: If job is not in RUNNING state
        """
        # Sanitize job_id
        if '..' in job_id or '/' in job_id or '\\' in job_id:
            raise ValueError(f"Invalid job_id: {job_id}")

        # Find RUNNING job
        job_file_path = None
        if self.spool_path.exists():
            for grabber_spool in self.spool_path.glob("*"):
                if not grabber_spool.is_dir():
                    continue

                matching_files = list(grabber_spool.glob(f"*{job_id}*-RUNNING"))
                if matching_files:
                    job_file_path = matching_files[0]
                    break

        if not job_file_path:
            raise FileNotFoundError(f"RUNNING job not found for job_id: {job_id}")

        # Rename to STALE
        new_path = job_file_path.parent / job_file_path.name.replace("-RUNNING", "-STALE")
        job_file_path.rename(new_path)

        return JobStatusUpdateResponse(
            job_id=job_id,
            old_status="running",
            new_status="stale",
            message=f"Job {job_id} marked as stale"
        )

    async def mark_job_as_failed(self, job_id: str) -> JobStatusUpdateResponse:
        """Mark a RUNNING or STALE job as FAILED.

        Args:
            job_id: Job identifier

        Returns:
            JobStatusUpdateResponse with status change details

        Raises:
            FileNotFoundError: If job not found
            ValueError: If job is not in RUNNING or STALE state
        """
        # Sanitize job_id
        if '..' in job_id or '/' in job_id or '\\' in job_id:
            raise ValueError(f"Invalid job_id: {job_id}")

        # Find RUNNING or STALE job
        job_file_path = None
        old_status = None

        if self.spool_path.exists():
            for grabber_spool in self.spool_path.glob("*"):
                if not grabber_spool.is_dir():
                    continue

                # Check RUNNING first
                matching_files = list(grabber_spool.glob(f"*{job_id}*-RUNNING"))
                if matching_files:
                    job_file_path = matching_files[0]
                    old_status = "running"
                    break

                # Check STALE
                matching_files = list(grabber_spool.glob(f"*{job_id}*-STALE"))
                if matching_files:
                    job_file_path = matching_files[0]
                    old_status = "stale"
                    break

        if not job_file_path:
            raise FileNotFoundError(f"RUNNING or STALE job not found for job_id: {job_id}")

        # Rename to FAILED
        suffix = "-RUNNING" if old_status == "running" else "-STALE"
        new_path = job_file_path.parent / job_file_path.name.replace(suffix, "-FAILED")
        job_file_path.rename(new_path)

        return JobStatusUpdateResponse(
            job_id=job_id,
            old_status=old_status,
            new_status="failed",
            message=f"Job {job_id} marked as failed"
        )
