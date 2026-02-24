#!/usr/bin/env python3
"""
Integration tests for Sandbox Management Example

This module provides pytest-based integration tests for the sandbox_example.py
functions, using real API calls (no mocks).

Environment variables required:
- PYROMIND_API_KEY: API key for authentication
- PYROMIND_BASE_URL: Base URL for the API (optional, defaults to https://pyromind.ai/api/v1)

These tests will create, manage, and delete actual sandboxes.
"""

import os
import time

import pytest

from pyromind_sdk import PyroMindAPIClient, PyroMindAPIError
from pyromind_sdk.examples.openapi.sandbox_example import (
    create_sandbox_example,
    list_sandboxes_example,
    get_sandbox_example,
    delete_sandbox_example,
    execute_action_example,
    get_vnc_example,
    pause_sandbox_example,
    resume_sandbox_example,
    update_sandbox_example,
)


@pytest.fixture(scope="module")
def sandbox_tracker():
    """Track all created sandbox IDs for cleanup after tests"""
    tracker = []
    yield tracker
    # Cleanup: Delete all tracked sandboxes after all tests complete
    print(f"\n[CLEANUP] Cleaning up {len(tracker)} tracked sandboxes...")
    api_key = os.getenv("PYROMIND_API_KEY")
    base_url = os.getenv("PYROMIND_BASE_URL", "https://pyromind.ai/api/v1")
    if api_key:
        try:
            cleanup_client = PyroMindAPIClient(api_key=api_key, base_url=base_url)
            for sandbox_id in tracker:
                try:
                    # Try to get sandbox status
                    sandbox = cleanup_client.sandboxes.get_sandbox(sandbox_id)
                    current_status = sandbox.status.value.lower() if hasattr(sandbox.status, 'value') else str(sandbox.status).lower()
                    print(f"[CLEANUP] Sandbox {sandbox_id} status: {current_status}")

                    # If running, pause first
                    if current_status == 'running':
                        print(f"[CLEANUP] Pausing sandbox {sandbox_id}...")
                        cleanup_client.sandboxes.pause(sandbox_id)
                        time.sleep(5)

                    # Delete the sandbox
                    print(f"[CLEANUP] Deleting sandbox {sandbox_id}...")
                    cleanup_client.sandboxes.delete(sandbox_id)
                    print(f"[CLEANUP] Successfully deleted sandbox {sandbox_id}")
                except PyroMindAPIError as e:
                    if "not found" in str(e.message).lower() or e.status_code == 404:
                        print(f"[CLEANUP] Sandbox {sandbox_id} already deleted or not found")
                    else:
                        print(f"[CLEANUP] Error cleaning up sandbox {sandbox_id}: {e.message}")
                except Exception as e:
                    print(f"[CLEANUP] Unexpected error cleaning up sandbox {sandbox_id}: {e}")
        except Exception as e:
            print(f"[CLEANUP] Failed to create cleanup client: {e}")
    else:
        print("[CLEANUP] No API key available for cleanup")


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


def wait_for_sandbox_status(
    client: PyroMindAPIClient,
    sandbox_id: str,
    target_status: str,
    timeout: int = 1800,
    check_interval: int = 3
) -> bool:
    """
    Wait for a sandbox to reach a specific status.
    
    Args:
        client: PyroMindAPIClient instance
        sandbox_id: ID of the sandbox to check
        target_status: Target status to wait for (e.g., 'running', 'stopped')
        timeout: Maximum time to wait in seconds
        check_interval: Time between status checks in seconds
        
    Returns:
        True if the sandbox reached the target status, False if timeout
    """
    waited = 0
    while waited < timeout:
        try:
            sandbox = get_sandbox_example(sandbox_id)
            current_status = sandbox.status.value.lower() if hasattr(sandbox.status, 'value') else str(sandbox.status).lower()
            print(f"[WAIT] Sandbox {sandbox_id} status: {current_status} (target: {target_status}, waited {waited}s)")
            
            if current_status == target_status.lower():
                print(f"[WAIT] Sandbox {sandbox_id} reached target status: {target_status}")
                return True
            # Handle error cases
            elif current_status == 'error':
                print(f"[WAIT] Sandbox {sandbox_id} is in error state, stopping wait")
                return False
        except Exception as e:
            print(f"[WAIT] Error checking sandbox status: {type(e).__name__}: {str(e)}")
        
        time.sleep(check_interval)
        waited += check_interval
    
    print(f"[WAIT] Timeout waiting for sandbox {sandbox_id} to reach status {target_status} after {timeout}s")
    return False


def test_create_sandbox(client, sandbox_tracker):
    """Test creating a sandbox"""
    # Step 1: Create sandbox
    sandbox_id = create_sandbox_example()
    assert sandbox_id is not None
    sandbox_tracker.append(sandbox_id)

    # Step 2: Get sandbox
    sandbox = client.sandboxes.get_sandbox(sandbox_id)
    assert sandbox.id == sandbox_id

    # Wait for sandbox to be running
    if not wait_for_sandbox_status(client, sandbox_id, 'running'):
        pytest.skip(f"Sandbox {sandbox_id} did not reach running state, skipping test")


def test_stop_sandbox(client, sandbox_tracker):
    """Test stopping a sandbox"""
    # List all sandboxes
    sandboxes = list_sandboxes_example()
    # Find a running sandbox
    sandbox_id = None
    for sandbox in sandboxes:
        status = sandbox.status.value.lower() if hasattr(sandbox.status, 'value') else str(sandbox.status).lower()
        if status == 'running':
            # Stop the sandbox
            sandbox_id = sandbox.id
            pause_sandbox_example(sandbox_id=sandbox_id)
            break

    # Verify sandbox status
    if sandbox_id:
        assert wait_for_sandbox_status(client, sandbox_id, 'stopped')


def test_resume_sandbox(client, sandbox_tracker):
    """Test resuming a stopped sandbox"""
    # List all sandboxes
    sandboxes = list_sandboxes_example()
    # Find a stopped sandbox
    sandbox_id = None
    for sandbox in sandboxes:
        status = sandbox.status.value.lower() if hasattr(sandbox.status, 'value') else str(sandbox.status).lower()
        if status == 'stopped':
            # Resume the sandbox
            sandbox_id = sandbox.id
            resume_sandbox_example(sandbox_id=sandbox_id)
            break

    # Verify sandbox status
    if sandbox_id:
        assert wait_for_sandbox_status(client, sandbox_id, 'running')


def test_delete_sandbox(client, sandbox_tracker):
    """Test deleting a sandbox"""
    # List all sandboxes
    sandboxes = list_sandboxes_example()
    # Find a stopped or error sandbox with 'example-' prefix
    sandbox_id = None
    for sandbox in sandboxes:
        status = sandbox.status.value.lower() if hasattr(sandbox.status, 'value') else str(sandbox.status).lower()
        if status in ('stopped', 'error') and sandbox.name.startswith('example-'):
            # Delete the sandbox
            sandbox_id = sandbox.id
            delete_sandbox_example(sandbox_id=sandbox_id)
            break

    if sandbox_id is None:
        test_create_sandbox(client, sandbox_tracker)
        test_stop_sandbox(client, sandbox_tracker)

    # Verify sandbox is deleted (404 means success)
    try:
        sandbox = get_sandbox_example(sandbox_id=sandbox_id)
    except PyroMindAPIError as e:
        # 404 is expected, means sandbox was successfully deleted
        assert e.status_code == 404
        print(f"Sandbox {sandbox_id} successfully deleted, e:{e.message}")
    except Exception as e:
        # Other errors should be raised
        print(f"Error while deleting sandbox {sandbox_id}: {e}")
        raise


def test_edit_sandbox(client, sandbox_tracker):
    """Test editing a sandbox"""
    # List all sandboxes
    sandboxes = list_sandboxes_example()
    # Find a sandbox that's not error or creating
    sandbox_id = None
    for sandbox in sandboxes:
        status = sandbox.status.value.lower() if hasattr(sandbox.status, 'value') else str(sandbox.status).lower()
        if status not in ('error', 'creating'):
            # Edit the sandbox
            sandbox_id = sandbox.id
            update_sandbox_example(sandbox_id=sandbox_id)
            break

    # If we couldn't find a sandbox to edit, create one first
    if sandbox_id is None:
        sandbox_id = create_sandbox_example()
        if sandbox_id:
            # Wait for sandbox to be in a state where it can be updated
            wait_for_sandbox_status(client, sandbox_id, 'running')
            # Now try to update it
            update_sandbox_example(sandbox_id=sandbox_id)

    if sandbox_id:
        sandbox_updated = get_sandbox_example(sandbox_id=sandbox_id)
        assert sandbox_updated is not None
        assert sandbox_updated.name == "example-sandbox-updated"
        resources = sandbox_updated.resources
        assert resources.cpu == "4"
        assert resources.memory == "8Gi"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
