"""
SandBoxes API Client

This module provides a client for managing sandboxes via the PyroMind API.
"""

from typing import List, Optional, Dict, Any
from .base import PyroMindClient
from .models import (
    SandboxCreateRequest,
    SandboxResponse,
    SandboxListAPIResponse,
    SandboxAPIResponse,
    ActionRequest,
    ActionResponse,
    ActionAPIResponse,
    BatchActionRequest,
    BatchActionAPIResponse,
    VncAPIResponse,
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
        
        if isinstance(data, dict) and "sandboxes" in data:
            sandboxes_data = data["sandboxes"]
        elif isinstance(data, list):
            sandboxes_data = data
        else:
            api_response = SandboxListAPIResponse(**data)
            return api_response.sandboxes
        
        api_response = SandboxListAPIResponse(sandboxes=sandboxes_data if isinstance(sandboxes_data, list) else [])
        return api_response.sandboxes
    
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
        
        if isinstance(data, dict) and "sandbox" in data:
            sandbox_data = data["sandbox"]
        else:
            sandbox_data = data
        
        api_response = SandboxAPIResponse(sandbox=sandbox_data)
        return api_response.sandbox
    
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
        
        if isinstance(data, dict) and "sandbox" in data:
            sandbox_data = data["sandbox"]
        else:
            sandbox_data = data
        
        api_response = SandboxAPIResponse(sandbox=sandbox_data)
        return api_response.sandbox
    
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
        
        if isinstance(data, dict) and "action" in data:
            action_data = data["action"]
        else:
            action_data = data
        
        api_response = ActionAPIResponse(action=action_data)
        return api_response.action
    
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
        
        if isinstance(data, dict) and "actions" in data:
            actions_data = data["actions"]
        elif isinstance(data, list):
            actions_data = data
        else:
            actions_data = []
        
        api_response = BatchActionAPIResponse(actions=actions_data if isinstance(actions_data, list) else [])
        return api_response.actions
    
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
        
        if isinstance(data, dict) and "vnc" in data:
            vnc_data = data["vnc"]
        else:
            vnc_data = data
        
        api_response = VncAPIResponse(vnc=vnc_data)
        return api_response.vnc.connection.model_dump()
