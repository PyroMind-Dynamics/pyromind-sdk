"""
SandBoxes API Client

This module provides a client for managing sandboxes via the PyroMind API.
"""

from typing import List, Optional, Dict, Any
from .base import PyroMindClient
from .models import (
    SandboxCreateRequest,
    SandboxUpdateRequest,
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
        converted_sandboxes = []
        for sandbox in sandboxes_data:
            if isinstance(sandbox, dict):
                converted_sandbox = self._convert_instance_data(sandbox)
                converted_sandboxes.append(SandboxResponse(**converted_sandbox))
            else:
                converted_sandboxes.append(sandbox)
        return converted_sandboxes
    
    def create(self, request: SandboxCreateRequest) -> SandboxResponse:
        """
        Create a new sandbox
        
        Args:
            request: SandboxCreateRequest with sandbox configuration
            
        Returns:
            SandboxResponse object
        """
        # Convert request to API format
        request_dict = request.model_dump()
        
        # API expects 'sandbox_type' instead of 'type'
        if 'type' in request_dict:
            type_value = request_dict.pop('type')
            # Convert our enum to API string values
            type_mapping = {
                "linux": "code",  # Map linux to code for API
                "windows": "win"
            }
            api_type = type_mapping.get(str(type_value), "code")
            request_dict['sandbox_type'] = api_type
        
        # Handle resource configuration - move resources to top level
        if 'configuration' in request_dict and request_dict['configuration']:
            config = request_dict['configuration']
            if 'resources' in config and config['resources']:
                resources = config['resources']
                # Convert memory from "4Gi" to "4" and move to top level
                if 'memory' in resources and resources['memory']:
                    memory_value = resources['memory']
                    if isinstance(memory_value, str) and memory_value.endswith('Gi'):
                        resources['memory'] = memory_value[:-2]  # Remove "Gi" suffix
                # Move resources to top level
                request_dict['resources'] = resources
                # Remove resources from configuration
                del config['resources']
                # If configuration is now empty, remove it
                if not config:
                    del request_dict['configuration']
            else:
                # If resources is None or empty, remove it from configuration
                if 'resources' in config:
                    del config['resources']
                # If configuration is now empty, remove it
                if not config:
                    del request_dict['configuration']
                        
        response = self.post("/sandboxes", json_data=request_dict)
        # API returns {success: True, data: {...}} format
        data = self._extract_data(response)
        
        # Backend returns the sandbox data directly in the data field
        if isinstance(data, dict):
            data = self._convert_instance_data(data)
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
        if isinstance(data, dict):
            data = self._convert_instance_data(data)
        return SandboxResponse(**data)
    
    def delete(self, sandbox_id: str) -> None:
        """
        Delete a sandbox
        
        Args:
            sandbox_id: ID of the sandbox to delete
        """
        self._request("DELETE", f"/sandboxes/{sandbox_id}")

    def update(self, sandbox_id: str, request: SandboxUpdateRequest) -> SandboxResponse:
        """
        Update a sandbox configuration.

        Args:
            sandbox_id: ID of the sandbox to update
            request: SandboxUpdateRequest with fields to update (name, resources, configuration)

        Returns:
            SandboxResponse object
        """
        response = self.put(f"/sandboxes/{sandbox_id}", json_data=request.model_dump(exclude_none=True))
        data = self._extract_data(response)
        if isinstance(data, dict):
            data = self._convert_instance_data(data)
        return SandboxResponse(**data)

    def pause(self, sandbox_id: str) -> SandboxResponse:
        """
        Pause a running sandbox.

        Args:
            sandbox_id: ID of the sandbox to pause

        Returns:
            SandboxResponse object (status will be stopped)
        """
        response = self.post(f"/sandboxes/{sandbox_id}/pause")
        data = self._extract_data(response)
        if isinstance(data, dict):
            data = self._convert_instance_data(data)
        return SandboxResponse(**data)

    def resume(self, sandbox_id: str) -> SandboxResponse:
        """
        Resume a paused sandbox.

        Args:
            sandbox_id: ID of the sandbox to resume

        Returns:
            SandboxResponse object (status will be pending then running)
        """
        response = self.post(f"/sandboxes/{sandbox_id}/resume")
        data = self._extract_data(response)
        if isinstance(data, dict):
            data = self._convert_instance_data(data)
        return SandboxResponse(**data)
    
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
        return vnc_response.connection_info.model_dump()

    def _convert_instance_data(self, instance_data) -> dict:
        if not isinstance(instance_data, dict):
            return instance_data

        # Handle field name mappings
        sandbox_id_value = instance_data.get("sandbox_id") or instance_data.get("id")
        # Handle ID format conversion: API uses sb_xxx for URLs but returns sb-xxx
        if isinstance(sandbox_id_value, str) and sandbox_id_value.startswith("sb-"):
            sandbox_id_value = sandbox_id_value.replace("sb-", "sb_")
        
        # Handle type conversion - API returns string values, we need SandboxType enum
        type_value = instance_data.get("type") or instance_data.get("sandbox_type")
        if isinstance(type_value, str):
            # Map API string values to our enum values
            type_mapping = {
                "linux": "linux",
                "win": "windows", 
                "mac": "linux",  # Map mac to linux for our enum
                "android": "linux",  # Map android to linux for our enum
                "code": "linux",  # Map code to linux for our enum
                "search": "linux"  # Map search to linux for our enum
            }
            type_value = type_mapping.get(type_value.lower(), "linux")
        
        # Handle status conversion - API may return various status values
        status_value = instance_data.get("status") or ""
        if isinstance(status_value, str):
            status_mapping = {
                "Pending": "creating",
                "pending": "creating",
                "Starting": "creating",
                "starting": "creating",
                "Running": "running",
                "running": "running",
                "Stopped": "stopped",
                "stopped": "stopped",
                "Error": "error",
                "error": "error"
            }
            status_value = status_mapping.get(status_value, status_value.lower())
        
        # Handle configuration - if None, create minimal configuration
        configuration_value = instance_data.get("configuration")
        if configuration_value is None:
            configuration_value = {"image": "default"}
        
        # Handle resources - if None, create empty resource config
        resources_value = instance_data.get("resources")
        if resources_value:
            configuration_value.update({"resources": resources_value})
        
        # Handle screen resolution
        screen_size_value = instance_data.get("screen_size") or instance_data.get("screen_resolution")
        if screen_size_value:
            configuration_value.update({"screen_size": screen_size_value})


        converted_instance = {
            "id": sandbox_id_value,
            "name": instance_data.get("name") or sandbox_id_value,
            "type": type_value,
            "status": status_value,
            "configuration": configuration_value,
            'usage':None,
            "created_at": instance_data.get("created_at"),
            "updated_at":None
        }
        # Remove None values for optional fields
        converted_instance = {
            k: v for k, v in converted_instance.items()
            if v is not None or k in ["sandbox_id", "sandbox_type", "status"]
        }
        return converted_instance
