"""
Training API Client

This module provides a client for managing training jobs via the PyroMind API.
"""

from typing import List
from .base import PyroMindClient
from .models import (
    TrainingJobCreateRequest,
    TrainingJobResponse,
    TrainingJobListAPIResponse,
    TrainingJobAPIResponse,
)


class TrainingClient(PyroMindClient):
    """
    Client for managing training jobs
    
    Provides methods for creating, listing, getting, deleting,
    pausing, and resuming training jobs.
    """
    
    def list(self) -> List[TrainingJobResponse]:
        """
        List all training jobs
        
        Returns:
            List of TrainingJobResponse objects
        """
        response = self.get("/training/jobs")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "jobs" in data:
            jobs_data = data["jobs"]
        elif isinstance(data, list):
            jobs_data = data
        else:
            api_response = TrainingJobListAPIResponse(**data)
            return api_response.jobs
        
        api_response = TrainingJobListAPIResponse(jobs=jobs_data if isinstance(jobs_data, list) else [])
        return api_response.jobs
    
    def create(self, request: TrainingJobCreateRequest) -> TrainingJobResponse:
        """
        Create a new training job
        
        Args:
            request: TrainingJobCreateRequest with job configuration
            
        Returns:
            TrainingJobResponse object
        """
        response = self.post("/training/jobs", json_data=request.model_dump())
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "job" in data:
            job_data = data["job"]
        else:
            job_data = data
        
        api_response = TrainingJobAPIResponse(job=job_data)
        return api_response.job
    
    def get_job(self, job_id: str) -> TrainingJobResponse:
        """
        Get a specific training job by ID
        
        Args:
            job_id: ID of the training job to retrieve
            
        Returns:
            TrainingJobResponse object
        """
        response = self.get(f"/training/jobs/{job_id}")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "job" in data:
            job_data = data["job"]
        else:
            job_data = data
        
        api_response = TrainingJobAPIResponse(job=job_data)
        return api_response.job
    
    def delete(self, job_id: str) -> None:
        """
        Delete a training job
        
        Args:
            job_id: ID of the training job to delete
        """
        self._request("DELETE", f"/training/jobs/{job_id}")
    
    def pause(self, job_id: str) -> TrainingJobResponse:
        """
        Pause a training job
        
        Args:
            job_id: ID of the training job to pause
            
        Returns:
            TrainingJobResponse object
        """
        response = self.post(f"/training/jobs/{job_id}/pause")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "job" in data:
            job_data = data["job"]
        else:
            job_data = data
        
        api_response = TrainingJobAPIResponse(job=job_data)
        return api_response.job
    
    def resume(self, job_id: str) -> TrainingJobResponse:
        """
        Resume a paused training job
        
        Args:
            job_id: ID of the training job to resume
            
        Returns:
            TrainingJobResponse object
        """
        response = self.post(f"/training/jobs/{job_id}/resume")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "job" in data:
            job_data = data["job"]
        else:
            job_data = data
        
        api_response = TrainingJobAPIResponse(job=job_data)
        return api_response.job
