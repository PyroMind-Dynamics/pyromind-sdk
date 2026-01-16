"""
Training API Client

This module provides a client for managing training tasks via the PyroMind API.
"""

from typing import List
from .base import PyroMindClient
from .models import (
    TrainingJobCreateRequest,
    TrainingJobResponse,
    TrainingJobListAPIResponse,
)


class TrainingClient(PyroMindClient):
    """
    Client for managing training tasks
    
    Provides methods for creating, listing, getting, deleting,
    and stopping training tasks.
    """
    
    def list(self) -> List[TrainingJobResponse]:
        """
        List all training tasks
        
        Returns:
            List of TrainingJobResponse objects
        """
        response = self.get("/training/tasks")
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
        Create a new training task
        
        Args:
            request: TrainingJobCreateRequest with task configuration
            
        Returns:
            TrainingJobResponse object
        """
        response = self.post("/training/tasks", json_data=request.model_dump())
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns the job data directly in the data field
        return TrainingJobResponse(**data)
    
    def get_job(self, job_id: str) -> TrainingJobResponse:
        """
        Get a specific training task by ID
        
        Args:
            job_id: ID of the training task to retrieve (can be int or str)
            
        Returns:
            TrainingJobResponse object
        """
        response = self.get(f"/training/tasks/{job_id}")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns the job data directly in the data field
        return TrainingJobResponse(**data)
    
    def delete(self, job_id: str, force: bool = False) -> None:
        """
        Delete a training task
        
        Args:
            job_id: ID of the training task to delete (can be int or str)
            force: If True, force delete even if task is running
        """
        params = {"force": force} if force else {}
        self._request("DELETE", f"/training/tasks/{job_id}", params=params)
    
    def stop(self, job_id: str) -> TrainingJobResponse:
        """
        Stop a running or paused training task
        
        Args:
            job_id: ID of the training task to stop (can be int or str)
            
        Returns:
            TrainingJobResponse object
        """
        response = self.post(f"/training/tasks/{job_id}/stop")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns task_id and status in the data field
        # Fetch the full task to return complete information
        if isinstance(data, dict) and "task_id" in data:
            return self.get_job(data["task_id"])
        # Fallback: try to construct from available data
        return TrainingJobResponse(**data)
