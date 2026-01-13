"""
Instance (Jupyter) API Client

This module provides a client for managing Jupyter instances via the PyroMind API.
"""

from typing import List, Optional
from .base import PyroMindClient
from .models import (
    JupyterRequest,
    JupyterResponse,
    JupyterListAPIResponse,
    JupyterAPIResponse,
)


class InstanceClient(PyroMindClient):
    """
    Client for managing Jupyter instances
    
    Provides methods for creating, listing, getting, updating, deleting,
    pausing, and resuming Jupyter instances.
    """
    
    def list(self) -> List[JupyterResponse]:
        """
        List all Jupyter instances
        
        Returns:
            List of JupyterResponse objects
        """
        response = self.get("/instance")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "instances" in data:
            instances_data = data["instances"]
        elif isinstance(data, list):
            instances_data = data
        else:
            api_response = JupyterListAPIResponse(**data)
            return api_response.instances
        
        api_response = JupyterListAPIResponse(instances=instances_data if isinstance(instances_data, list) else [])
        return api_response.instances
    
    def create(self, request: JupyterRequest) -> JupyterResponse:
        """
        Create a new Jupyter instance
        
        Args:
            request: JupyterRequest with instance configuration
            
        Returns:
            JupyterResponse object
        """
        response = self.post("/instance", json_data=request.model_dump())
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "instance" in data:
            instance_data = data["instance"]
        else:
            instance_data = data
        
        api_response = JupyterAPIResponse(instance=instance_data)
        return api_response.instance
    
    def get_instance(self, jupyter_id: str) -> JupyterResponse:
        """
        Get a specific Jupyter instance by ID
        
        Args:
            jupyter_id: ID of the Jupyter instance to retrieve
            
        Returns:
            JupyterResponse object
        """
        response = self.get(f"/instance/{jupyter_id}")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "instance" in data:
            instance_data = data["instance"]
        else:
            instance_data = data
        
        api_response = JupyterAPIResponse(instance=instance_data)
        return api_response.instance
    
    def update(self, jupyter_id: str, request: JupyterRequest) -> JupyterResponse:
        """
        Update a Jupyter instance
        
        Args:
            jupyter_id: ID of the Jupyter instance to update
            request: JupyterRequest with updated configuration
            
        Returns:
            JupyterResponse object
        """
        response = self.put(f"/instance/{jupyter_id}", json_data=request.model_dump())
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "instance" in data:
            instance_data = data["instance"]
        else:
            instance_data = data
        
        api_response = JupyterAPIResponse(instance=instance_data)
        return api_response.instance
    
    def delete(self, jupyter_id: str) -> None:
        """
        Delete a Jupyter instance
        
        Args:
            jupyter_id: ID of the Jupyter instance to delete
        """
        self._request("DELETE", f"/instance/{jupyter_id}")
    
    def pause(self, jupyter_id: str) -> JupyterResponse:
        """
        Pause a Jupyter instance
        
        Args:
            jupyter_id: ID of the Jupyter instance to pause
            
        Returns:
            JupyterResponse object
        """
        response = self.post(f"/instance/{jupyter_id}/pause")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "instance" in data:
            instance_data = data["instance"]
        else:
            instance_data = data
        
        api_response = JupyterAPIResponse(instance=instance_data)
        return api_response.instance
    
    def resume(self, jupyter_id: str) -> JupyterResponse:
        """
        Resume a paused Jupyter instance
        
        Args:
            jupyter_id: ID of the Jupyter instance to resume
            
        Returns:
            JupyterResponse object
        """
        response = self.post(f"/instance/{jupyter_id}/resume")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        if isinstance(data, dict) and "instance" in data:
            instance_data = data["instance"]
        else:
            instance_data = data
        
        api_response = JupyterAPIResponse(instance=instance_data)
        return api_response.instance
