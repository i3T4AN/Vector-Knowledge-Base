# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Background job tracking for async operations
# =======================================================================

"""
Job Tracking Module - Manages background task status and results
"""
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Status values for background jobs"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    """Types of background jobs"""
    CLUSTERING = "clustering"
    BATCH_UPLOAD = "batch_upload"
    CACHE_BUILD = "cache_build"


# In-memory job storage (could be replaced with Redis for production)
_jobs: Dict[str, Dict[str, Any]] = {}


def create_job(job_id: str, job_type: JobType, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Create a new job entry.
    
    Args:
        job_id: Unique identifier for the job
        job_type: Type of job (clustering, batch_upload, etc.)
        metadata: Optional additional metadata
    
    Returns:
        The created job dict
    """
    job = {
        "id": job_id,
        "type": job_type.value,
        "status": JobStatus.PENDING.value,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "progress": 0,
        "result": None,
        "error": None,
        "metadata": metadata or {}
    }
    _jobs[job_id] = job
    logger.info(f"Created job {job_id} of type {job_type.value}")
    return job


def update_job(
    job_id: str,
    status: Optional[JobStatus] = None,
    progress: Optional[int] = None,
    result: Any = None,
    error: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Update an existing job's status/progress/result.
    
    Args:
        job_id: ID of the job to update
        status: New status (optional)
        progress: Progress percentage 0-100 (optional)
        result: Result data if completed (optional)
        error: Error message if failed (optional)
    
    Returns:
        The updated job dict, or None if not found
    """
    if job_id not in _jobs:
        logger.warning(f"Attempted to update non-existent job: {job_id}")
        return None
    
    job = _jobs[job_id]
    
    if status is not None:
        job["status"] = status.value
    if progress is not None:
        job["progress"] = min(100, max(0, progress))
    if result is not None:
        job["result"] = result
    if error is not None:
        job["error"] = error
    
    job["updated_at"] = datetime.now().isoformat()
    
    logger.info(f"Updated job {job_id}: status={job['status']}, progress={job['progress']}%")
    return job


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a job by ID.
    
    Args:
        job_id: ID of the job to retrieve
    
    Returns:
        The job dict, or None if not found
    """
    return _jobs.get(job_id)


def list_jobs(job_type: Optional[JobType] = None, limit: int = 50) -> list:
    """
    List recent jobs, optionally filtered by type.
    
    Args:
        job_type: Optional filter by job type
        limit: Maximum number of jobs to return
    
    Returns:
        List of job dicts
    """
    jobs = list(_jobs.values())
    
    if job_type:
        jobs = [j for j in jobs if j["type"] == job_type.value]
    
    # Sort by created_at descending (most recent first)
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return jobs[:limit]


def cleanup_old_jobs(max_age_hours: int = 24) -> int:
    """
    Remove jobs older than max_age_hours.
    
    Args:
        max_age_hours: Maximum age in hours
    
    Returns:
        Number of jobs removed
    """
    from datetime import timedelta
    
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    jobs_to_remove = []
    
    for job_id, job in _jobs.items():
        created_at = datetime.fromisoformat(job["created_at"])
        if created_at < cutoff:
            jobs_to_remove.append(job_id)
    
    for job_id in jobs_to_remove:
        del _jobs[job_id]
    
    if jobs_to_remove:
        logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
    
    return len(jobs_to_remove)
