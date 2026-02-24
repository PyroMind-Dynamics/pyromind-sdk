"""
Inference API Client

This module provides a client for managing inference jobs via the PyroMind API.
"""

from typing import List
from .base import PyroMindClient
from .models import (
    InferenceJobCreateRequest,
    InferenceJobUpdateRequest,
    InferenceJobResponse,
)


class InferenceClient(PyroMindClient):
    """
    Client for managing inference jobs
    
    Provides methods for creating, listing, getting, and deleting inference jobs.
    """
    
    def list(self) -> List[InferenceJobResponse]:
        """
        List all inference jobs
        
        Returns:
            List of InferenceJobResponse objects
        """
        response = self.get("/inference")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Handle different possible data structures
        if isinstance(data, dict) and "inference_jobs" in data:
            jobs_data = data["inference_jobs"]
        elif isinstance(data, dict) and "pagination" in data:
            # Response format: {inference_jobs: [...], pagination: {...}}
            jobs_data = data.get("inference_jobs", [])
        elif isinstance(data, list):
            jobs_data = data
        else:
            jobs_data = []
        
        # Convert each job data to InferenceJobResponse
        converted_jobs = []
        for job in jobs_data:
            if isinstance(job, dict):
                converted_job = self._convert_instance_data(job)
                converted_jobs.append(InferenceJobResponse(**converted_job))
            else:
                converted_jobs.append(job)
        return converted_jobs
    
    def create(self, request: InferenceJobCreateRequest) -> InferenceJobResponse:
        """
        Create a new inference job
        
        Args:
            request: InferenceJobCreateRequest with job configuration
            
        Returns:
            InferenceJobResponse object
        """
        response = self.post("/inference", json_data=request.model_dump())
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)

        if isinstance(data, dict) and "instance" in data:
            instance_data = data["instance"]
        else:
            instance_data = data

        # Convert to InferenceJobResponse
        if isinstance(instance_data, dict):
            instance_data = self._convert_instance_data(instance_data)
        
        # Backend returns the job data directly in the data field
        return InferenceJobResponse(**instance_data)
    
    def get_job(self, job_id: str) -> InferenceJobResponse:
        """
        Get a specific inference job by ID
        
        Args:
            job_id: ID of the inference job to retrieve
            
        Returns:
            InferenceJobResponse object
        """
        response = self.get(f"/inference/{job_id}")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)

        if isinstance(data, dict) and "instance" in data:
            instance_data = data["instance"]
        else:
            instance_data = data

        # Convert to InferenceJobResponse
        if isinstance(instance_data, dict):
            instance_data = self._convert_instance_data(instance_data)
        
        # Backend returns the job data directly in the data field
        return InferenceJobResponse(**instance_data)
    
    def delete(self, job_id: str) -> None:
        """
        Delete an inference job
        
        Args:
            job_id: ID of the inference job to delete
        """
        self._request("DELETE", f"/inference/{job_id}")

    def update(self, job_id: str, request: InferenceJobUpdateRequest) -> InferenceJobResponse:
        """
        Update an inference job configuration.

        Args:
            job_id: ID of the inference job to update
            request: InferenceJobUpdateRequest with fields to update (name, resources, model_path, etc.)

        Returns:
            InferenceJobResponse object
        """
        response = self.put(f"/inference/{job_id}", json_data=request.model_dump(exclude_none=True))
        data = self._extract_data(response)
        if isinstance(data, dict):
            data = self._convert_instance_data(data)
        return InferenceJobResponse(**data)

    def pause(self, job_id: str) -> InferenceJobResponse:
        """
        Pause a running inference job.

        Args:
            job_id: ID of the inference job to pause

        Returns:
            InferenceJobResponse object (status will be stopped)
        """
        response = self.post(f"/inference/{job_id}/pause")
        data = self._extract_data(response)
        if isinstance(data, dict):
            data = self._convert_instance_data(data)
        return InferenceJobResponse(**data)

    def resume(self, job_id: str) -> InferenceJobResponse:
        """
        Resume a paused inference job.

        Args:
            job_id: ID of the inference job to resume

        Returns:
            InferenceJobResponse object (status will be pending then running)
        """
        response = self.post(f"/inference/{job_id}/resume")
        data = self._extract_data(response)
        if isinstance(data, dict):
            data = self._convert_instance_data(data)
        return InferenceJobResponse(**data)


    def _convert_instance_data(self, instance_data) -> dict:
        if not isinstance(instance_data, dict):
            return instance_data


        jupyter_id_value = instance_data.get("job_id") or instance_data.get("id")
        converted_instance = {
            "id": jupyter_id_value,
            "name": instance_data.get("name") or jupyter_id_value,
            "model_path": instance_data.get("model_path"),
            "image": instance_data.get("image") or instance_data.get("image_name"),
            "status": instance_data.get("status") or "",
            "resources": instance_data.get("resources"),
            "endpoint_url": instance_data.get("endpoint_url"),
            "created_at": instance_data.get("created_at"),
            "updated_at": instance_data.get("updated_at") or instance_data.get("last_activity"),
            "uid": instance_data.get("uid"),
        }
        # Remove None values for optional fields, but keep required fields
        converted_instance = {
            k: v for k, v in converted_instance.items()
            if v is not None or k in ["id", "name", "status"]
        }
        return converted_instance
