#!/usr/bin/env python3
"""
Pytest test cases for Jupyter Instance Management Example

This module provides pytest-based unit tests for the jupyter_instance_example.py
functions, using mocks to avoid actual API calls.
"""

import pytest
import time
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Optional

from pyromind_sdk import PyroMindAPIClient, PyroMindAPIError
from pyromind_sdk.client.models import (
    JupyterRequest,
    JupyterResponse,
    ResourceConfig,
)


# Import the example functions
import sys
from pathlib import Path

# Add examples directory to path
# From pyromind_sdk/tests/pytest/ to pyromind_sdk/examples/openapi/
# Go up 3 levels: pyromind_sdk/tests/pytest -> pyromind_sdk/tests -> pyromind_sdk -> workspace root
# Then go to pyromind_sdk/examples/openapi/
EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples" / "openapi"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

# Import using importlib to handle module loading
import importlib.util
jupyter_example_path = EXAMPLES_DIR / "jupyter_instance_example.py"
if not jupyter_example_path.exists():
    raise FileNotFoundError(f"Example file not found: {jupyter_example_path}")

spec = importlib.util.spec_from_file_location(
    "jupyter_instance_example",
    jupyter_example_path
)
jupyter_instance_example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jupyter_instance_example)

# Import functions from the module
create_jupyter_example = jupyter_instance_example.create_jupyter_example
list_jupyter_example = jupyter_instance_example.list_jupyter_example
get_jupyter_example = jupyter_instance_example.get_jupyter_example
update_jupyter_example = jupyter_instance_example.update_jupyter_example
pause_jupyter_example = jupyter_instance_example.pause_jupyter_example
resume_jupyter_example = jupyter_instance_example.resume_jupyter_example
delete_jupyter_example = jupyter_instance_example.delete_jupyter_example
wait_for_status = jupyter_instance_example.wait_for_status
check_url = jupyter_instance_example.check_url


# Set up environment variable for API key (required by PyroMindAPIClient)
# This is needed even though we're mocking the client, because the client
# initialization checks for the API key before we can mock it
@pytest.fixture(autouse=True)
def setup_env():
    """Set up environment variables for tests"""
    os.environ['PYROMIND_API_KEY'] = 'test-api-key'
    yield
    # Cleanup: remove the environment variable after test
    if 'PYROMIND_API_KEY' in os.environ:
        del os.environ['PYROMIND_API_KEY']


class TestCreateJupyterExample:
    """Test cases for create_jupyter_example function"""
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_create_jupyter_success(self, mock_client_class):
        """Test successful Jupyter instance creation"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_instance = Mock()
        mock_instance.id = "test-instance-123"
        mock_instance.name = "example-jupyter"
        mock_instance.status = "creating"
        mock_instance.url = "https://jupyter.example.com"
        
        mock_client.instance.create.return_value = mock_instance
        
        # Execute
        result = create_jupyter_example()
        
        # Verify
        assert result == "test-instance-123"
        mock_client.instance.create.assert_called_once()
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_create_jupyter_failure(self, mock_client_class):
        """Test Jupyter instance creation failure"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.instance.create.side_effect = PyroMindAPIError(
            message="Failed to create instance",
            status_code=400
        )
        
        # Execute
        result = create_jupyter_example()
        
        # Verify
        assert result is None
        mock_client.close.assert_called_once()


class TestListJupyterExample:
    """Test cases for list_jupyter_example function"""
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_list_jupyter_success(self, mock_client_class):
        """Test successful Jupyter instance listing"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_instance1 = Mock()
        mock_instance1.name = "instance-1"
        mock_instance1.id = "id-1"
        mock_instance1.status = "running"
        mock_instance1.url = "https://jupyter1.example.com"
        
        mock_instance2 = Mock()
        mock_instance2.name = "instance-2"
        mock_instance2.id = "id-2"
        mock_instance2.status = "stopped"
        mock_instance2.url = None
        
        mock_client.instance.list.return_value = [mock_instance1, mock_instance2]
        
        # Execute
        result = list_jupyter_example()
        
        # Verify
        assert len(result) == 2
        assert result[0].name == "instance-1"
        assert result[1].name == "instance-2"
        mock_client.instance.list.assert_called_once()
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_list_jupyter_empty(self, mock_client_class):
        """Test listing when no instances exist"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.instance.list.return_value = []
        
        # Execute
        result = list_jupyter_example()
        
        # Verify
        assert result == []
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_list_jupyter_failure(self, mock_client_class):
        """Test listing failure"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.instance.list.side_effect = PyroMindAPIError(
            message="Failed to list instances",
            status_code=500
        )
        
        # Execute
        result = list_jupyter_example()
        
        # Verify
        assert result == []
        mock_client.close.assert_called_once()


class TestGetJupyterExample:
    """Test cases for get_jupyter_example function"""
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_get_jupyter_success(self, mock_client_class):
        """Test successful Jupyter instance retrieval"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_instance = Mock()
        mock_instance.name = "test-instance"
        mock_instance.status = "running"
        mock_instance.password = "test-password"
        mock_instance.resources = Mock()
        mock_instance.resources.cpu = "2"
        mock_instance.resources.memory = "4Gi"
        mock_instance.resources.gpu = 0
        mock_instance.url = "https://jupyter.example.com"
        
        mock_client.instance.get_instance.return_value = mock_instance
        
        # Execute
        result = get_jupyter_example("test-instance-123")
        
        # Verify
        assert result is not None
        assert result.name == "test-instance"
        assert result.status == "running"
        mock_client.instance.get_instance.assert_called_once_with("test-instance-123")
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_get_jupyter_failure(self, mock_client_class):
        """Test Jupyter instance retrieval failure"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.instance.get_instance.side_effect = PyroMindAPIError(
            message="Instance not found",
            status_code=404
        )
        
        # Execute
        result = get_jupyter_example("non-existent-id")
        
        # Verify
        assert result is None
        mock_client.close.assert_called_once()


class TestUpdateJupyterExample:
    """Test cases for update_jupyter_example function"""
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_update_jupyter_success(self, mock_client_class):
        """Test successful Jupyter instance update"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_instance = Mock()
        mock_instance.name = "updated-jupyter"
        mock_instance.resources = Mock()
        mock_instance.resources.cpu = "4"
        mock_instance.resources.memory = "32Gi"
        mock_instance.resources.gpu = 1
        
        mock_client.instance.update.return_value = mock_instance
        
        # Execute
        result = update_jupyter_example("test-instance-123")
        
        # Verify
        assert result is not None
        assert result.name == "updated-jupyter"
        assert result.resources.gpu == 1
        mock_client.instance.update.assert_called_once()
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_update_jupyter_failure(self, mock_client_class):
        """Test Jupyter instance update failure"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.instance.update.side_effect = PyroMindAPIError(
            message="Update failed",
            status_code=400,
            response={"detail": "Invalid resource configuration"}
        )
        
        # Execute
        result = update_jupyter_example("test-instance-123")
        
        # Verify
        assert result is None
        mock_client.close.assert_called_once()


class TestPauseJupyterExample:
    """Test cases for pause_jupyter_example function"""
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_pause_jupyter_success(self, mock_client_class):
        """Test successful Jupyter instance pause"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_instance = Mock()
        mock_instance.status = "stopped"
        
        mock_client.instance.pause.return_value = mock_instance
        
        # Execute
        result = pause_jupyter_example("test-instance-123")
        
        # Verify
        assert result is not None
        assert result.status == "stopped"
        mock_client.instance.pause.assert_called_once_with("test-instance-123")
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_pause_jupyter_failure(self, mock_client_class):
        """Test Jupyter instance pause failure"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.instance.pause.side_effect = PyroMindAPIError(
            message="Pause failed",
            status_code=400
        )
        
        # Execute
        result = pause_jupyter_example("test-instance-123")
        
        # Verify
        assert result is None
        mock_client.close.assert_called_once()


class TestResumeJupyterExample:
    """Test cases for resume_jupyter_example function"""
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    @patch.object(jupyter_instance_example.time, 'sleep')
    def test_resume_jupyter_success(self, mock_sleep, mock_client_class):
        """Test successful Jupyter instance resume"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_instance = Mock()
        mock_instance.status = "running"
        
        mock_client.instance.resume.return_value = mock_instance
        
        # Execute
        result = resume_jupyter_example("test-instance-123", max_retries=3, retry_interval=1)
        
        # Verify
        assert result is not None
        assert result.status == "running"
        mock_client.instance.resume.assert_called_once_with("test-instance-123")
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    @patch.object(jupyter_instance_example.time, 'sleep')
    def test_resume_jupyter_with_retry(self, mock_sleep, mock_client_class):
        """Test Jupyter instance resume with retry logic"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_instance = Mock()
        mock_instance.status = "running"
        
        # First call fails with status error, second succeeds
        mock_client.instance.resume.side_effect = [
            PyroMindAPIError(
                message="Instance status is pending",
                status_code=400
            ),
            mock_instance
        ]
        
        # Execute
        result = resume_jupyter_example("test-instance-123", max_retries=3, retry_interval=0.1)
        
        # Verify
        assert result is not None
        assert result.status == "running"
        assert mock_client.instance.resume.call_count == 2
        assert mock_sleep.call_count == 1  # Should sleep once before retry
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    @patch.object(jupyter_instance_example.time, 'sleep')
    def test_resume_jupyter_max_retries_exceeded(self, mock_sleep, mock_client_class):
        """Test Jupyter instance resume when max retries exceeded"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Always fail with status error
        mock_client.instance.resume.side_effect = PyroMindAPIError(
            message="Instance status is pending",
            status_code=400
        )
        
        # Execute
        result = resume_jupyter_example("test-instance-123", max_retries=2, retry_interval=0.1)
        
        # Verify
        assert result is None
        assert mock_client.instance.resume.call_count == 2
        assert mock_sleep.call_count == 1  # Should sleep once before giving up
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_resume_jupyter_other_error(self, mock_client_class):
        """Test Jupyter instance resume with non-retryable error"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Fail with non-status error (should not retry)
        mock_client.instance.resume.side_effect = PyroMindAPIError(
            message="Unauthorized",
            status_code=401
        )
        
        # Execute
        result = resume_jupyter_example("test-instance-123", max_retries=3, retry_interval=1)
        
        # Verify
        assert result is None
        mock_client.instance.resume.assert_called_once()  # Should not retry
        mock_client.close.assert_called_once()


class TestDeleteJupyterExample:
    """Test cases for delete_jupyter_example function"""
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_delete_jupyter_success(self, mock_client_class):
        """Test successful Jupyter instance deletion"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.instance.delete.return_value = None
        
        # Execute (should not raise exception)
        delete_jupyter_example("test-instance-123")
        
        # Verify
        mock_client.instance.delete.assert_called_once_with("test-instance-123")
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    def test_delete_jupyter_failure(self, mock_client_class):
        """Test Jupyter instance deletion failure"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.instance.delete.side_effect = PyroMindAPIError(
            message="Delete failed",
            status_code=404
        )
        
        # Execute (should handle error gracefully)
        delete_jupyter_example("non-existent-id")
        
        # Verify
        mock_client.close.assert_called_once()


class TestWaitForStatus:
    """Test cases for wait_for_status function"""
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    @patch.object(jupyter_instance_example.time, 'sleep')
    def test_wait_for_status_success(self, mock_sleep, mock_client_class):
        """Test successful status wait"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_instance = Mock()
        mock_instance.status = "running"
        
        mock_client.instance.get_instance.return_value = mock_instance
        
        # Execute
        result = wait_for_status("test-instance-123", "running", max_wait_time=10, check_interval=1)
        
        # Verify
        assert result == "running"
        mock_client.instance.get_instance.assert_called_once()
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    @patch.object(jupyter_instance_example.time, 'sleep')
    @patch.object(jupyter_instance_example.time, 'time')
    def test_wait_for_status_timeout(self, mock_time, mock_sleep, mock_client_class):
        """Test status wait timeout"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_instance = Mock()
        mock_instance.status = "creating"  # Never reaches "running"
        
        mock_client.instance.get_instance.return_value = mock_instance
        
        # Mock time to simulate timeout
        mock_time.side_effect = [0, 11]  # Start at 0, then timeout at 11 seconds
        
        # Execute
        result = wait_for_status("test-instance-123", "running", max_wait_time=10, check_interval=1)
        
        # Verify
        assert result is None
        mock_client.close.assert_called_once()
    
    @patch.object(jupyter_instance_example, 'PyroMindAPIClient')
    @patch.object(jupyter_instance_example.time, 'sleep')
    def test_wait_for_status_error(self, mock_sleep, mock_client_class):
        """Test status wait with API error"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.instance.get_instance.side_effect = PyroMindAPIError(
            message="Instance not found",
            status_code=404
        )
        
        # Execute
        result = wait_for_status("non-existent-id", "running", max_wait_time=10, check_interval=1)
        
        # Verify
        assert result is None
        mock_client.close.assert_called_once()


class TestCheckUrl:
    """Test cases for check_url function"""
    
    @patch.object(jupyter_instance_example.requests, 'get')
    def test_check_url_success(self, mock_get):
        """Test successful URL check"""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Execute
        result = check_url("https://example.com", timeout=10)
        
        # Verify
        assert result is True
        mock_get.assert_called_once_with("https://example.com", timeout=10, allow_redirects=True)
    
    @patch.object(jupyter_instance_example.requests, 'get')
    def test_check_url_error_status(self, mock_get):
        """Test URL check with error status code"""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        # Execute
        result = check_url("https://example.com/not-found", timeout=10)
        
        # Verify
        assert result is False
    
    @patch.object(jupyter_instance_example.requests, 'get')
    def test_check_url_raise_on_error(self, mock_get):
        """Test URL check with raise_on_error=True"""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Execute and verify exception is raised
        with pytest.raises(RuntimeError):
            check_url("https://example.com", timeout=10, raise_on_error=True)
    
    @patch.object(jupyter_instance_example.requests, 'get')
    def test_check_url_request_exception(self, mock_get):
        """Test URL check with request exception"""
        # Setup mock
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        # Execute
        result = check_url("https://example.com", timeout=10)
        
        # Verify
        assert result is False
    
    @patch.object(jupyter_instance_example.requests, 'get')
    def test_check_url_request_exception_raise(self, mock_get):
        """Test URL check with request exception and raise_on_error=True"""
        # Setup mock
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        # Execute and verify exception is raised
        with pytest.raises(RuntimeError):
            check_url("https://example.com", timeout=10, raise_on_error=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
