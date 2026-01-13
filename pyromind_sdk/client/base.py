"""
Base client class for PyroMind API

This module provides the base client class that handles authentication,
HTTP requests, and error handling for all API clients.
"""

import os
import requests
from typing import Optional, Dict, Any, Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class PyroMindAPIError(Exception):
    """Base exception for PyroMind API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class PyroMindClient:
    """
    Base client class for PyroMind API
    
    Handles authentication, HTTP requests, and error handling.
    All resource-specific clients inherit from this class.
    
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
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://pyromind.ai/api/v1",
        timeout: int = 30,
        max_retries: int = 3
    ):
        # Get API key from parameter or environment variable
        if api_key is None:
            api_key = os.getenv("PYROMIND_API_KEY")
        
        if not api_key:
            raise ValueError(
                "API key is required. Please provide it either as a parameter "
                "or set the PYROMIND_API_KEY environment variable."
            )
        
        # Strip whitespace from API key
        api_key = api_key.strip()
        
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _extract_data(self, response: Dict[str, Any]) -> Any:
        """
        Extract data from API response
        
        API responses are wrapped in {success: True, data: {...}} format.
        This method extracts the actual data from the response.
        
        Args:
            response: API response dictionary
            
        Returns:
            Extracted data from response
        """
        if isinstance(response, dict):
            if "data" in response:
                return response["data"]
            # If response doesn't have 'data' field, return the whole response
            # (for backward compatibility)
            return response
        return response
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            json_data: JSON request body
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response JSON data as dictionary
            
        Raises:
            PyroMindAPIError: If the request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout,
                **kwargs
            )
            
            # Handle non-2xx responses
            if not response.ok:
                error_data = None
                try:
                    error_data = response.json()
                except:
                    error_data = {"message": response.text}
                
                # Provide more detailed error message for 401
                if response.status_code == 401:
                    error_message = (
                        "Authentication failed (401). Please check your API key. "
                        "The API key may be invalid, expired, or incorrectly formatted."
                    )
                    if error_data.get("message"):
                        error_message += f" Server message: {error_data.get('message')}"
                else:
                    error_message = error_data.get("message", f"API request failed with status {response.status_code}")
                
                raise PyroMindAPIError(
                    message=error_message,
                    status_code=response.status_code,
                    response=error_data
                )
            
            # Return JSON response
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            raise PyroMindAPIError(
                message=f"Request failed: {str(e)}",
                status_code=None
            )
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make a GET request"""
        return self._request("GET", endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make a POST request"""
        return self._request("POST", endpoint, json_data=json_data, **kwargs)
    
    def put(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make a PUT request"""
        return self._request("PUT", endpoint, json_data=json_data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a DELETE request"""
        return self._request("DELETE", endpoint, **kwargs)
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
