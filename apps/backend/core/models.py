"""Pydantic models for API requests and responses."""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class JobSubmitResponse(BaseModel):
    """Response for job submission."""
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    """Job status information."""
    job_id: str
    status: Literal["queued", "running", "done", "failed", "timeout", "not_found", "stale"]
    grabber: Optional[str] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    is_archived: bool = False


class ClusterStatus(BaseModel):
    """Cluster-wide status information."""
    active_grabbers: list[str]
    jobs_queued: int
    jobs_running: int
    jobs_done: int
    jobs_failed: int
    jobs_timeout: int
    total_jobs: int


class JobListItem(BaseModel):
    """Job list item for pagination."""
    job_id: str
    status: Literal["queued", "running", "done", "failed", "timeout", "stale"]
    grabber: Optional[str] = None
    submitted_at: Optional[datetime] = None
    is_archived: bool = False
    is_stale: bool = False


class JobListResponse(BaseModel):
    """Paginated job list response."""
    jobs: list[JobListItem]
    total: int
    page: int
    page_size: int


class JobRerunResponse(BaseModel):
    """Response for job rerun request."""
    new_job_id: str
    original_job_id: str
    status: str
    message: str


class JobArchiveResponse(BaseModel):
    """Response for job archive request."""
    job_id: str
    status: str
    message: str
    archived_at: Optional[datetime] = None


class BulkArchiveRequest(BaseModel):
    """Request for bulk job archiving."""
    job_ids: list[str]


class BulkArchiveResponse(BaseModel):
    """Response for bulk archive request."""
    archived_count: int
    failed_count: int
    results: list[dict]


class ArchivedJobListResponse(BaseModel):
    """Paginated archived job list response."""
    jobs: list[JobListItem]
    total: int
    page: int
    page_size: int


class JobScriptContent(BaseModel):
    """Job script content information."""
    job_id: str
    filename: str
    content: str
    size: int


class StaleJobInfo(BaseModel):
    """Information about a stale job."""
    job_id: str
    grabber: str
    runtime_duration: Optional[float] = None  # in seconds
    submitted_at: Optional[datetime] = None


class StaleJobDetectionResponse(BaseModel):
    """Response for stale job detection."""
    stale_jobs: list[StaleJobInfo]
    count: int


class JobStatusUpdateResponse(BaseModel):
    """Response for job status update."""
    job_id: str
    old_status: str
    new_status: str
    message: str
