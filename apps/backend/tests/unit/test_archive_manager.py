"""Unit tests for archive functionality."""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from core.job_manager import JobManager


@pytest.fixture
def job_manager(tmp_path):
    """Create a job manager with temporary cluster path."""
    return JobManager(str(tmp_path))


@pytest.fixture
def completed_job(job_manager, tmp_path):
    """Create a completed job for testing."""
    # Create a grabber spool directory
    grabber_spool = tmp_path / "spool" / "test-grabber"
    grabber_spool.mkdir(parents=True, exist_ok=True)

    # Create a DONE job file
    job_id = "test_script.py_20240101_120000_123456"
    job_file = grabber_spool / f"{job_id}-20240101120001-DONE"
    job_file.write_text("#!/usr/bin/env python3\nprint('test')\n")

    # Create log files
    log_path = tmp_path / "log"
    log_path.mkdir(parents=True, exist_ok=True)
    (log_path / f"{job_id}.out").write_text("test output")
    (log_path / f"{job_id}.err").write_text("test error")
    (log_path / f"{job_id}.log").write_text("ExitCode(0)")

    return job_id


@pytest.mark.asyncio
async def test_archive_job_success(job_manager, completed_job, tmp_path):
    """Test archiving a completed job successfully."""
    response = await job_manager.archive_job(completed_job)

    assert response.status == "success"
    assert response.job_id == completed_job
    assert response.message == f"Job {completed_job} archived successfully"
    assert response.archived_at is not None

    # Verify job moved to archive
    archive_path = tmp_path / "archive" / "test-grabber"
    assert archive_path.exists()

    # Verify job file exists in archive
    archived_files = list(archive_path.glob(f"*{completed_job}*-DONE"))
    assert len(archived_files) == 1

    # Verify log files moved
    assert (archive_path / f"{completed_job}.out").exists()
    assert (archive_path / f"{completed_job}.err").exists()
    assert (archive_path / f"{completed_job}.log").exists()


@pytest.mark.asyncio
async def test_archive_job_not_found(job_manager):
    """Test archiving a non-existent job."""
    with pytest.raises(FileNotFoundError):
        await job_manager.archive_job("nonexistent_job")


@pytest.mark.asyncio
async def test_archive_jobs_bulk(job_manager, completed_job, tmp_path):
    """Test bulk archiving multiple jobs."""
    # Create a second completed job
    grabber_spool = tmp_path / "spool" / "test-grabber"
    job_id_2 = "test_script2.py_20240101_120000_123457"
    job_file_2 = grabber_spool / f"{job_id_2}-20240101120002-DONE"
    job_file_2.write_text("#!/usr/bin/env python3\nprint('test2')\n")

    # Archive both jobs
    response = await job_manager.archive_jobs_bulk([completed_job, job_id_2])

    assert response.archived_count == 2
    assert response.failed_count == 0
    assert len(response.results) == 2


@pytest.mark.asyncio
async def test_list_archived_jobs(job_manager, completed_job, tmp_path):
    """Test listing archived jobs."""
    # Archive the job first
    await job_manager.archive_job(completed_job)

    # List archived jobs
    jobs, total = await job_manager.list_archived_jobs()

    assert total == 1
    assert len(jobs) == 1
    assert jobs[0].job_id == completed_job
    assert jobs[0].is_archived is True
    assert jobs[0].status == "done"


@pytest.mark.asyncio
async def test_read_job_script(job_manager, completed_job, tmp_path):
    """Test reading job script content."""
    # Read active job script
    content = await job_manager.read_job_script(completed_job, is_archived=False)

    assert content.job_id == completed_job
    assert content.filename == completed_job
    assert "print('test')" in content.content
    assert content.size > 0


@pytest.mark.asyncio
async def test_read_archived_job_script(job_manager, completed_job, tmp_path):
    """Test reading archived job script content."""
    # Archive the job first
    await job_manager.archive_job(completed_job)

    # Read archived job script
    content = await job_manager.read_job_script(completed_job, is_archived=True)

    assert content.job_id == completed_job
    assert "print('test')" in content.content


@pytest.mark.asyncio
async def test_detect_stale_jobs(job_manager, tmp_path):
    """Test detecting stale jobs."""
    # Create a RUNNING job without a live grabber
    grabber_spool = tmp_path / "spool" / "dead-grabber"
    grabber_spool.mkdir(parents=True, exist_ok=True)

    job_id = "stale_job.py_20240101_120000_123456"
    job_file = grabber_spool / f"{job_id}-20240101120001-RUNNING"
    job_file.write_text("#!/usr/bin/env python3\nprint('running')\n")

    # Detect stale jobs
    response = await job_manager.detect_stale_jobs()

    assert response.count == 1
    assert len(response.stale_jobs) == 1
    assert response.stale_jobs[0].job_id == job_id
    assert response.stale_jobs[0].grabber == "dead-grabber"


@pytest.mark.asyncio
async def test_mark_job_as_stale(job_manager, tmp_path):
    """Test marking a RUNNING job as STALE."""
    # Create a RUNNING job
    grabber_spool = tmp_path / "spool" / "test-grabber"
    grabber_spool.mkdir(parents=True, exist_ok=True)

    job_id = "running_job.py_20240101_120000_123456"
    job_file = grabber_spool / f"{job_id}-20240101120001-RUNNING"
    job_file.write_text("#!/usr/bin/env python3\nprint('running')\n")

    # Mark as stale
    response = await job_manager.mark_job_as_stale(job_id)

    assert response.old_status == "running"
    assert response.new_status == "stale"
    assert response.job_id == job_id

    # Verify file renamed
    stale_files = list(grabber_spool.glob(f"*{job_id}*-STALE"))
    assert len(stale_files) == 1


@pytest.mark.asyncio
async def test_mark_job_as_failed(job_manager, tmp_path):
    """Test marking a STALE job as FAILED."""
    # Create a STALE job
    grabber_spool = tmp_path / "spool" / "test-grabber"
    grabber_spool.mkdir(parents=True, exist_ok=True)

    job_id = "stale_job.py_20240101_120000_123456"
    job_file = grabber_spool / f"{job_id}-20240101120001-STALE"
    job_file.write_text("#!/usr/bin/env python3\nprint('stale')\n")

    # Mark as failed
    response = await job_manager.mark_job_as_failed(job_id)

    assert response.old_status == "stale"
    assert response.new_status == "failed"
    assert response.job_id == job_id

    # Verify file renamed
    failed_files = list(grabber_spool.glob(f"*{job_id}*-FAILED"))
    assert len(failed_files) == 1
