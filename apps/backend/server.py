"""FastAPI server for ScriptGrabber job management."""

import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import uvicorn

from core.job_manager import JobManager
from core.models import (
    JobSubmitResponse,
    JobStatus,
    ClusterStatus,
    JobListResponse,
    JobRerunResponse
)

# Load environment variables
load_dotenv()

# Configuration
CLUSTER_PATH = os.getenv("CLUSTER_PATH", "/cluster")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  # 10MB default
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Initialize FastAPI app
app = FastAPI(
    title="ScriptGrabber API",
    description="Job management API for distributed Python script execution",
    version="0.1.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize job manager
job_manager = JobManager(CLUSTER_PATH)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ScriptGrabber API",
        "version": "0.1.0",
        "cluster_path": CLUSTER_PATH,
        "endpoints": {
            "submit_job": "POST /api/jobs",
            "get_job_status": "GET /api/jobs/{job_id}",
            "list_jobs": "GET /api/jobs",
            "cluster_status": "GET /api/status",
            "health": "GET /api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "cluster_path": CLUSTER_PATH}


@app.post("/api/jobs", response_model=JobSubmitResponse)
async def submit_job(file: UploadFile = File(...)):
    """Submit a Python script for execution.

    Args:
        file: Python script file (.py)

    Returns:
        JobSubmitResponse with job_id and status
    """
    # Validate file extension
    if not file.filename or not file.filename.endswith('.py'):
        raise HTTPException(
            status_code=400,
            detail="Only Python files (.py) are accepted"
        )

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE} bytes"
        )

    # Validate content (basic check)
    try:
        content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be valid UTF-8 text"
        )

    # Submit job
    try:
        job_id = await job_manager.submit_job(file.filename, content)
        return JobSubmitResponse(
            job_id=job_id,
            status="queued",
            message=f"Job {job_id} submitted successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit job: {str(e)}"
        )


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a specific job.

    Args:
        job_id: Job identifier

    Returns:
        JobStatus with current status and details
    """
    try:
        status = await job_manager.get_job_status(job_id)
        if status.status == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@app.get("/api/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Jobs per page")
):
    """List all jobs with optional filtering and pagination.

    Args:
        status: Filter by status (queued, running, done, failed, timeout)
        page: Page number (1-indexed)
        page_size: Number of jobs per page

    Returns:
        JobListResponse with paginated job list
    """
    try:
        jobs, total = await job_manager.list_jobs(status, page, page_size)
        return JobListResponse(
            jobs=jobs,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list jobs: {str(e)}"
        )


@app.get("/api/status", response_model=ClusterStatus)
async def get_cluster_status():
    """Get cluster-wide status and metrics.

    Returns:
        ClusterStatus with active grabbers and job counts
    """
    try:
        status = await job_manager.get_cluster_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cluster status: {str(e)}"
        )


@app.post("/api/jobs/{job_id}/rerun", response_model=JobRerunResponse)
async def rerun_job(job_id: str):
    """Rerun an existing job by retrieving its script and resubmitting.

    Args:
        job_id: Job identifier to rerun

    Returns:
        JobRerunResponse with new job ID and status
    """
    try:
        new_job_id, original_filename = await job_manager.rerun_job(job_id)
        return JobRerunResponse(
            new_job_id=new_job_id,
            original_job_id=job_id,
            status="queued",
            message=f"Job rerun successfully. New job ID: {new_job_id}"
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rerun job: {str(e)}"
        )


def main():
    """Start the FastAPI server."""
    print(f"Starting ScriptGrabber API server...")
    print(f"Cluster path: {CLUSTER_PATH}")
    print(f"Server: http://{HOST}:{PORT}")
    print(f"API docs: http://{HOST}:{PORT}/docs")

    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
