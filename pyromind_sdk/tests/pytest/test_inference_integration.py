#!/usr/bin/env python3
"""
Integration tests for Inference Job Management Example

This module provides pytest-based integration tests for the inference_example.py
functions, using real API calls (no mocks).

Environment variables required:
- PYROMIND_API_KEY: API key for authentication
- PYROMIND_BASE_URL: Base URL for the API (optional, defaults to https://pyromind.ai/api/v1)

These tests will create, manage, and delete actual inference jobs.
"""

import os
import time

import pytest

from pyromind_sdk import PyroMindAPIClient, PyroMindAPIError
from pyromind_sdk.examples.openapi.inference_example import (
    create_inference_job_example,
    list_inference_jobs_example,
    get_inference_job_example,
    delete_inference_job_example,
    stop_inference_job_example,
    resume_inference_job_example,
    update_inference_job_example,
)


@pytest.fixture(scope="module")
def job_tracker():
    """Track all created job IDs for cleanup after tests"""
    tracker = []
    yield tracker
    # Cleanup: Delete all tracked jobs after all tests complete
    print(f"\n[CLEANUP] Cleaning up {len(tracker)} tracked inference jobs...")
    api_key = os.getenv("PYROMIND_API_KEY")
    base_url = os.getenv("PYROMIND_BASE_URL", "https://pyromind.ai/api/v1")
    if api_key:
        try:
            cleanup_client = PyroMindAPIClient(api_key=api_key, base_url=base_url)
            for job_id in tracker:
                try:
                    # Try to get job status
                    job = cleanup_client.inference.get_job(job_id)
                    current_status = job.status.lower()
                    print(f"[CLEANUP] Job {job_id} status: {current_status}")

                    # If running, stop first
                    if current_status == 'running':
                        print(f"[CLEANUP] Stopping job {job_id}...")
                        cleanup_client.inference.pause(job_id)
                        time.sleep(5)

                    # Delete the job
                    print(f"[CLEANUP] Deleting job {job_id}...")
                    cleanup_client.inference.delete(job_id)
                    print(f"[CLEANUP] Successfully deleted job {job_id}")
                except PyroMindAPIError as e:
                    if "not found" in str(e.message).lower() or e.status_code == 404:
                        print(f"[CLEANUP] Job {job_id} already deleted or not found")
                    else:
                        print(f"[CLEANUP] Error cleaning up job {job_id}: {e.message}")
                except Exception as e:
                    print(f"[CLEANUP] Unexpected error cleaning up job {job_id}: {e}")
        except Exception as e:
            print(f"[CLEANUP] Failed to create cleanup client: {e}")
    else:
        print("[CLEANUP] No API key available for cleanup")


@pytest.fixture(scope="module")
def api_key():
    """Get API key from environment variable"""
    api_key = os.getenv("PYROMIND_API_KEY")
    if not api_key:
        pytest.skip(
            "PYROMIND_API_KEY environment variable not set. "
            "Please set this environment variable to run integration tests."
        )
    print(f"[INFO] Using API key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '***'}")
    return api_key


@pytest.fixture(scope="module")
def base_url():
    """Get base URL from environment variable or use default"""
    url = os.getenv("PYROMIND_BASE_URL", "https://pyromind.ai/api/v1")
    print(f"[INFO] Using base URL: {url}")
    return url


@pytest.fixture(scope="module")
def client(api_key, base_url):
    """Create a PyroMind API client"""
    return PyroMindAPIClient(api_key=api_key, base_url=base_url)


def wait_for_job_status(
    client: PyroMindAPIClient,
    job_id: str,
    target_status: str,
    timeout: int = 1800,
    check_interval: int = 3
) -> bool:
    waited = 0
    while waited < timeout:
        try:
            job = get_inference_job_example(job_id)
            current_status = job.status.lower()
            print(f"[WAIT] Job {job_id} status: {current_status} (target: {target_status}, waited {waited}s)")
            
            if current_status == target_status.lower():
                print(f"[WAIT] Job {job_id} reached target status: {target_status}")
                return True
            # Handle error cases
            elif current_status == 'failed':
                print(f"[WAIT] Job {job_id} is in failed state, stopping wait")
                return False
        except Exception as e:
            print(f"[WAIT] Error checking job status: {type(e).__name__}: {str(e)}")
        
        time.sleep(check_interval)
        waited += check_interval
    
    print(f"[WAIT] Timeout waiting for job {job_id} to reach status {target_status} after {timeout}s")
    return False

def test_create_job(client, job_tracker):
    """Test creating an inference job"""
    # Step 1: Create job
    job_id = create_inference_job_example()
    assert job_id is not None
    job_tracker.append(job_id)

    # Step 2: Get job
    job = client.inference.get_job(job_id)
    assert job.id == job_id

    # Wait for job to be running
    if not wait_for_job_status(client, job_id, 'running'):
        pytest.skip(f"Job {job_id} did not reach running state, skipping test")


def test_stop_job(client, job_tracker):
    """Test stopping an inference job"""
    # List all jobs
    jobs = list_inference_jobs_example()
    # Find a running job
    job_id = None
    for job in jobs:
        if job.status.lower() == 'running':
            # Stop the job
            job_id = job.id
            stop_inference_job_example(job_id=job_id)
            break

    # Verify job status
    if job_id:
        assert wait_for_job_status(client, job_id, 'stopped')


def test_resume_job(client, job_tracker):
    """Test resuming a stopped inference job"""
    # List all jobs
    jobs = list_inference_jobs_example()
    # Find a stopped job
    job_id = None
    for job in jobs:
        if job.status.lower() == 'stopped':
            # Resume the job
            job_id = job.id
            resume_inference_job_example(job_id=job_id)
            break

    # Verify job status
    if job_id:
        assert wait_for_job_status(client, job_id, 'running')


def test_delete_job(client, job_tracker):
    """Test deleting an inference job"""
    # List all jobs
    jobs = list_inference_jobs_example()
    # Find a stopped or failed job with 'example-' prefix
    job_id = None
    for job in jobs:
        if job.status.lower() in ('stopped', 'failed') and job.name.startswith('example-'):
            # Delete the job
            job_id = job.id
            delete_inference_job_example(job_id=job_id)
            break
        if job.status.lower() == 'running' and job.name.startswith('example-'):
            test_stop_job(client, job_tracker)
            # Delete the job
            job_id = job.id
            delete_inference_job_example(job_id=job_id)
            break

    if job_id is None:
        test_create_job(client, job_tracker)
        test_stop_job(client, job_tracker)

    # Verify job is deleted (404 means success)
    try:
        job = get_inference_job_example(job_id=job_id)
    except PyroMindAPIError as e:
        # 404 is expected, means job was successfully deleted
        assert e.status_code == 404
        print(f"Job {job_id} successfully deleted, e:{e.message}")
    except Exception as e:
        # Other errors should be raised
        print(f"Error while deleting job {job_id}: {e}")
        raise


def test_edit_job(client, job_tracker):
    """Test editing an inference job"""
    # List all jobs
    jobs = list_inference_jobs_example()
    # Find a job that's not failed or pending
    job_id = None
    for job in jobs:
        if job.status.lower() not in ('failed', 'pending'):
            # Edit the job
            job_id = job.id
            update_inference_job_example(job_id=job_id)
            break

    # If we couldn't find a job to edit, create one first
    if job_id is None:
        job_id = create_inference_job_example()
        if job_id:
            # Wait for job to be in a state where it can be updated
            wait_for_job_status(client, job_id, 'running')
            # Now try to update it
            update_inference_job_example(job_id=job_id)

    if job_id:
        job_updated = get_inference_job_example(job_id=job_id)
        assert job_updated is not None
        resources = job_updated.resources


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
