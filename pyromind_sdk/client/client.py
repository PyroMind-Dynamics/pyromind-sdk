"""
Main PyroMind API Client

This module provides the main client class that integrates all resource clients.
"""

import os
from typing import Optional
from .base import PyroMindClient
from .sandboxes import SandboxesClient
from .instance import InstanceClient
from .inference import InferenceClient
from .training import TrainingClient


class PyroMindAPIClient:
    """
    Main PyroMind API Client
    
    This class provides a unified interface to all PyroMind API resources.
    It integrates all resource-specific clients (Sandboxes, Instance, Inference, Training).
    
    Args:
        api_key: Bearer token for API authentication. If not provided, will try to
                read from PYROMIND_API_KEY environment variable. If neither is
                provided, will raise ValueError.
        base_url: Base URL for the API (default: https://pyromind.ai/api/v1)
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum number of retries for failed requests (default: 3)
    
    Raises:
        ValueError: If api_key is not provided and PYROMIND_API_KEY environment
                   variable is not set.
    
    Example:
        ```python
        from pyromind_sdk import PyroMindAPIClient
        
        client = PyroMindAPIClient(api_key="your-api-key")
        
        # List all sandboxes
        sandboxes = client.sandboxes.list()
        
        # Create a Jupyter instance
        from pyromind_sdk.client.models import JupyterRequest, ResourceConfig
        jupyter = client.instance.create(
            JupyterRequest(
                name="my-jupyter",
                image="jupyter/scipy-notebook:latest",
                resources=ResourceConfig(cpu="2", memory="4Gi")
            )
        )
        ```
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://pyromind.ai/api/v1",
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize the PyroMind API Client
        
        Args:
            api_key: Bearer token for API authentication. If not provided, will try to
                    read from PYROMIND_API_KEY environment variable.
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        # Get API key from parameter or environment variable
        if api_key is None:
            api_key = os.getenv("PYROMIND_API_KEY")
        
        if not api_key:
            raise ValueError(
                "API key is required. Please provide it either as a parameter "
                "or set the PYROMIND_API_KEY environment variable."
            )
        
        self._base_client = PyroMindClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries
        )
        
        # Initialize resource clients
        self.sandboxes = SandboxesClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries
        )
        self.instance = InstanceClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries
        )
        self.inference = InferenceClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries
        )
        self.training = TrainingClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries
        )
    
    def close(self):
        """Close all client sessions"""
        self._base_client.close()
        self.sandboxes.close()
        self.instance.close()
        self.inference.close()
        self.training.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
