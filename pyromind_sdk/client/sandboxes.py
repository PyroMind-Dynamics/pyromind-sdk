"""
SandBoxes API Client

This module provides a client for managing sandboxes via the PyroMind API.
"""

from typing import List, Optional, Dict, Any
from .base import PyroMindClient
from .models import (
    SandboxCreateRequest,
    SandboxResponse,
    ActionRequest,
    ActionResponse,
    BatchActionRequest,
    VNCResponse,
    VNCConnectionInfo,
)


class SandboxesClient(PyroMindClient):
    """
    Client for managing sandboxes
    
    Provides methods for creating, listing, getting, deleting sandboxes,
    executing actions, and managing VNC connections.
    """
    
    def list(self) -> List[SandboxResponse]:
        """
        List all sandboxes
        
        Returns:
            List of SandboxResponse objects
        """
        response = self.get("/sandboxes")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Handle different response formats
        if isinstance(data, dict) and "sandboxes" in data:
            sandboxes_data = data["sandboxes"]
        elif isinstance(data, dict) and "pagination" in data:
            # Response format: {sandboxes: [...], pagination: {...}}
            sandboxes_data = data.get("sandboxes", [])
        elif isinstance(data, list):
            sandboxes_data = data
        else:
            sandboxes_data = []
        
        # Convert each sandbox data to SandboxResponse
        return [SandboxResponse(**sandbox) if isinstance(sandbox, dict) else sandbox for sandbox in sandboxes_data]
    
    def create(self, request: SandboxCreateRequest) -> SandboxResponse:
        """
        Create a new sandbox
        
        Args:
            request: SandboxCreateRequest with sandbox configuration
            
        Returns:
            SandboxResponse object
        """
        response = self.post("/sandboxes", json_data=request.model_dump())
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns the sandbox data directly in the data field
        return SandboxResponse(**data)
    
    def get_sandbox(self, sandbox_id: str) -> SandboxResponse:
        """
        Get a specific sandbox by ID
        
        Args:
            sandbox_id: ID of the sandbox to retrieve
            
        Returns:
            SandboxResponse object
        """
        response = self.get(f"/sandboxes/{sandbox_id}")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns the sandbox data directly in the data field
        return SandboxResponse(**data)
    
    def delete(self, sandbox_id: str) -> None:
        """
        Delete a sandbox
        
        Args:
            sandbox_id: ID of the sandbox to delete
        """
        self._request("DELETE", f"/sandboxes/{sandbox_id}")
    
    def execute_action(self, sandbox_id: str, request: ActionRequest) -> ActionResponse:
        """
        Execute an action in a sandbox
        
        Args:
            sandbox_id: ID of the sandbox
            request: ActionRequest with action details
            
        Returns:
            ActionResponse object
        """
        response = self.post(
            f"/sandboxes/{sandbox_id}/actions",
            json_data=request.model_dump()
        )
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns the action data directly in the data field
        return ActionResponse(**data)
    
    def execute_batch_actions(self, sandbox_id: str, request: BatchActionRequest) -> List[ActionResponse]:
        """
        Execute multiple actions in a sandbox
        
        Args:
            sandbox_id: ID of the sandbox
            request: BatchActionRequest with list of actions
            
        Returns:
            List of ActionResponse objects
        """
        response = self.post(
            f"/sandboxes/{sandbox_id}/actions/batch",
            json_data=request.model_dump()
        )
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Handle batch response format
        if isinstance(data, dict) and "results" in data:
            results = data["results"]
        elif isinstance(data, list):
            results = data
        else:
            results = []
        
        # Convert each result to ActionResponse
        return [ActionResponse(**result) if isinstance(result, dict) else result for result in results]
    
    def get_vnc(self, sandbox_id: str) -> Dict[str, Any]:
        """
        Get VNC connection information for a sandbox
        
        Args:
            sandbox_id: ID of the sandbox
            
        Returns:
            Dictionary with VNC connection information
        """
        response = self.get(f"/sandboxes/{sandbox_id}/vnc")
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns the VNC data directly in the data field
        vnc_response = VNCResponse(**data)
        return vnc_response.connection.model_dump()
