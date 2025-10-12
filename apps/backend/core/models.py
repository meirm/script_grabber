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
    status: Literal["queued", "running", "done", "failed", "timeout", "not_found"]
    grabber: Optional[str] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None


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
    status: Literal["queued", "running", "done", "failed", "timeout"]
    grabber: Optional[str] = None
    submitted_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    """Paginated job list response."""
    jobs: list[JobListItem]
    total: int
    page: int
    page_size: int
