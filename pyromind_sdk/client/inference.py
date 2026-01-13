"""
Inference API Client

This module provides a client for managing inference jobs via the PyroMind API.
"""

from typing import List
from .base import PyroMindClient
from .models import (
    InferenceJobCreateRequest,
    InferenceJobResponse,
    InferenceJobListAPIResponse,
    InferenceJobAPIResponse,
    InferenceJobCreateAPIResponse,
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
        if isinstance(data, dict):
            # API returns {inference_jobs: [], page: 0, ...} format
            api_response = InferenceJobListAPIResponse(**data)
            return api_response.inference_jobs
        elif isinstance(data, list):
            # Fallback: if data is directly a list
            api_response = InferenceJobListAPIResponse(inference_jobs=data)
            return api_response.inference_jobs
        else:
            return []
    
    def create(self, request: InferenceJobCreateRequest) -> str:
        """
        Create a new inference job
        
        Args:
            request: InferenceJobCreateRequest with job configuration
            
        Returns:
            Job ID (str) of the created inference job
        """
        response = self.post("/inference", json_data=request.model_dump())
        # API returns {success: True, data: {job_id: "..."}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "job_id" in data:
            return data["job_id"]
        elif isinstance(data, dict):
            # Try to parse as InferenceJobCreateAPIResponse
            api_response = InferenceJobCreateAPIResponse(**data)
            return api_response.job_id
        else:
            raise ValueError(f"Unexpected response format: {data}")
    
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
        
        if isinstance(data, dict) and "job" in data:
            job_data = data["job"]
        else:
            job_data = data
        
        api_response = InferenceJobAPIResponse(job=job_data)
        return api_response.job
    
    def delete(self, job_id: str) -> None:
        """
        Delete an inference job
        
        Args:
            job_id: ID of the inference job to delete
        """
        self._request("DELETE", f"/inference/{job_id}")
