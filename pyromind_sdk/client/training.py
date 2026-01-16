"""
Training API Client

This module provides a client for managing training tasks via the PyroMind API.
"""

from typing import List
from .base import PyroMindClient
from .models import (
    TrainingTaskCreateRequest,
    TrainingTaskResponse,
    TrainingTaskListAPIResponse,
)


class TrainingClient(PyroMindClient):
    """
    Client for managing training tasks
    
    Provides methods for creating, listing, getting, deleting,
    and stopping training tasks.
    """
    
    def list(self) -> List[TrainingTaskResponse]:
        """
        List all training tasks
        
        Returns:
            List of TrainingTaskResponse objects
        """
        response = self.get("/training/tasks")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "tasks" in data:
            tasks_data = data["tasks"]
        elif isinstance(data, dict) and "jobs" in data:
            # Backward compatibility: support old "jobs" field
            tasks_data = data["jobs"]
        elif isinstance(data, list):
            tasks_data = data
        else:
            api_response = TrainingTaskListAPIResponse(**data)
            return api_response.tasks
        
        api_response = TrainingTaskListAPIResponse(tasks=tasks_data if isinstance(tasks_data, list) else [])
        return api_response.tasks
    
    def create(self, request: TrainingTaskCreateRequest) -> TrainingTaskResponse:
        """
        Create a new training task
        
        Args:
            request: TrainingTaskCreateRequest with task configuration
            
        Returns:
            TrainingTaskResponse object
        """
        response = self.post("/training/tasks", json_data=request.model_dump())
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns the job data directly in the data field
        return TrainingTaskResponse(**data)
    
    def get_job(self, task_id: str) -> TrainingTaskResponse:
        """
        Get a specific training task by ID
        
        Args:
            task_id: ID of the training task to retrieve (can be int or str)
            
        Returns:
            TrainingTaskResponse object
        """
        response = self.get(f"/training/tasks/{task_id}")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns the job data directly in the data field
        return TrainingTaskResponse(**data)
    
    def get_task(self, task_id: str) -> TrainingTaskResponse:
        """
        Get a specific training task by ID (alias for get_job)
        
        Args:
            task_id: ID of the training task to retrieve (can be int or str)
            
        Returns:
            TrainingTaskResponse object
        """
        return self.get_job(task_id)
    
    def delete(self, task_id: str, force: bool = False) -> None:
        """
        Delete a training task
        
        Args:
            task_id: ID of the training task to delete (can be int or str)
            force: If True, force delete even if task is running
        """
        params = {"force": force} if force else {}
        self._request("DELETE", f"/training/tasks/{task_id}", params=params)
    
    def stop(self, task_id: str) -> TrainingTaskResponse:
        """
        Stop a running or paused training task
        
        Args:
            task_id: ID of the training task to stop (can be int or str)
            
        Returns:
            TrainingTaskResponse object
        """
        response = self.post(f"/training/tasks/{task_id}/stop")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns task_id and status in the data field
        # Fetch the full task to return complete information
        if isinstance(data, dict) and "task_id" in data:
            return self.get_job(data["task_id"])
        # Fallback: try to construct from available data
        return TrainingTaskResponse(**data)
