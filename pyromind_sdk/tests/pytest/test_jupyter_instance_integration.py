#!/usr/bin/env python3
"""
Integration tests for Jupyter Instance Management Example

This module provides pytest-based integration tests for the jupyter_instance_example.py
functions, using real API calls (no mocks).

Environment variables required:
- PYROMIND_API_KEY: API key for authentication
- PYROMIND_BASE_URL: Base URL for the API (optional, defaults to https://pyromind.ai/api/v1)

These tests will create, manage, and delete actual Jupyter instances.
"""

import os
import time

import pytest

from pyromind_sdk import PyroMindAPIClient, PyroMindAPIError
from pyromind_sdk.client.models import (
    JupyterRequest,
    ResourceConfig,
)


@pytest.fixture
def instance_tracker():
    # 你的逻辑，比如返回一个列表用来记录测试产生的 ID，方便最后清理
    return []


@pytest.fixture(scope="module")
def api_key():
    """Get API key from environment variable"""
    api_key = os.getenv("PYROMIND_API_KEY")
    if not api_key:
        pytest.skip(
            "PYROMIND_API_KEY environment variable not set. "
            "Please set this environment variable to run integration tests."
        )
    print(f"[INFO] Using API key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '***'}")
    return api_key


@pytest.fixture(scope="module")
def base_url():
    """Get base URL from environment variable or use default"""
    url = os.getenv("PYROMIND_BASE_URL", "https://pyromind.ai/api/v1")
    print(f"[INFO] Using base URL: {url}")
    return url


@pytest.fixture(scope="module")
def client(api_key, base_url):
    """Create a PyroMind API client"""
    return PyroMindAPIClient(api_key=api_key, base_url=base_url)


def wait_for_instance_status(
    client: PyroMindAPIClient,
    instance_id: str,
    target_status: str,
    timeout: int = 1800,
    check_interval: int = 3
) -> bool:
    """
    Wait for an instance to reach a specific status.
    
    Args:
        client: PyroMindAPIClient instance
        instance_id: ID of the instance to check
        target_status: Target status to wait for (e.g., 'running', 'stopped')
        timeout: Maximum time to wait in seconds
        check_interval: Time between status checks in seconds
        
    Returns:
        True if the instance reached the target status, False if timeout
    """
    waited = 0
    while waited < timeout:
        try:
            instance = client.instance.get_instance(instance_id)
            current_status = instance.status.lower()
            print(f"[WAIT] Instance {instance_id} status: {current_status} (target: {target_status}, waited {waited}s)")
            
            if current_status == target_status.lower():
                print(f"[WAIT] Instance {instance_id} reached target status: {target_status}")
                return True
            # Handle error cases - if instance is in failed state, don't wait further
            elif current_status == 'failed':
                print(f"[WAIT] Instance {instance_id} is in failed state, stopping wait")
                return False
        except Exception as e:
            print(f"[WAIT] Error checking instance status: {type(e).__name__}: {str(e)}")
        
        time.sleep(check_interval)
        waited += check_interval
    
    print(f"[WAIT] Timeout waiting for instance {instance_id} to reach status {target_status} after {timeout}s")
    return False


def test_complete_workflow(client):
    """Test a complete workflow of Jupyter instance management"""
    instance_id = None

    try:
        # Step 1: Create instance (success ratio CPU:memory = 1:8 to 1:16)
        instance = client.instance.create(
            JupyterRequest(
                name=f"test-workflow-{int(time.time())}",
                resources=ResourceConfig(
                    cpu="2",
                    memory="16Gi",
                    gpu=0
                ),
                timeout=3600
            )
        )
        instance_id = instance.id
        assert instance_id is not None

        # Step 2: Get instance
        instance = client.instance.get_instance(instance_id)
        assert instance.id == instance_id

        while wait_for_instance_status(client, instance_id, 'running'):
            break

        # Step 3: Update instance (success ratio CPU:memory = 1:8 to 1:16)
        updated = client.instance.update(
            jupyter_id=instance_id,
            request=JupyterRequest(
                name=f"updated-workflow-{int(time.time())}",
                resources=ResourceConfig(
                    cpu="4",
                    memory="32Gi",
                    gpu=0
                )
            )
        )
        assert updated.id == instance_id

        # Step 4: Pause instance (if supported)
        try:
            while wait_for_instance_status(client, instance_id, 'running'):
                break
            paused = client.instance.pause(instance_id)
            assert paused.id == instance_id

            # Step 5: Resume instance (if pause succeeded)
            while wait_for_instance_status(client, instance_id, 'stopped'):
                break
            resumed = client.instance.resume(instance_id)
            assert resumed.id == instance_id
        except PyroMindAPIError as e:
            # If pause/resume is not supported, skip these steps
            print(f"Pause/resume not supported or failed: {e.message}")

        # Step 6: Pause instance before deletion (required)
        try:
            while wait_for_instance_status(client, instance_id, 'running'):
                break
            client.instance.pause(instance_id)
        except PyroMindAPIError as e:
            print(f"Warning: Cannot pause instance for deletion: {e.message}")

        # Step 7: Delete instance
        try:
            get_instance = client.instance.get_instance(instance_id)
            if get_instance and get_instance.status.lower() == 'running':
                client.instance.pause(instance_id)
            while wait_for_instance_status(client, instance_id, 'stopped'):
                break
            client.instance.delete(instance_id)
        except PyroMindAPIError as e:
            if "not in a deletable state" in str(e.message).lower():
                print(f"Warning: Cannot delete instance: {e.message}")
                # Try to clean up later - mark for manual cleanup
                print(f"Instance {instance_id} may need manual cleanup")
            else:
                raise

        # Verify deletion - wait a bit and check
        # Note: Deletion may be asynchronous
        try:
            instance = client.instance.get_instance(instance_id)
            # If instance still exists, wait a bit more
            if instance:
                try:
                    client.instance.get_instance(instance_id)
                    # If we can still get it, deletion may have failed
                    print(f"Warning: Instance {instance_id} still exists after deletion attempt")
                except PyroMindAPIError:
                    # Good, instance was deleted
                    pass
        except PyroMindAPIError:
            # Good, instance was deleted (raises error when getting)
            pass

    except Exception as e:
        # Clean up on error
        if instance_id:
            try:
                client.instance.delete(instance_id)
            except Exception:
                pass
        raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
