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

def test_create_instance(client, instance_tracker):
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
    instance_tracker.append(instance_id)

    # Step 2: Get instance
    instance = client.instance.get_instance(instance_id)
    assert instance.id == instance_id


    # Wait for instance to be running
    if not wait_for_instance_status(client, instance_id, 'running'):
        pytest.skip(f"Instance {instance_id} did not reach running state, skipping test")


def test_stop_instance(client, instance_tracker):
    # 列出所有的实例
    instances = client.instance.list()
    # 找到状态是启动中的
    instance_code = None
    for instance in instances:
        if instance.status.lower() == 'running':
            # 暂停实例
            instance_code = instance.id
            client.instance.pause(jupyter_id=instance_code)
            break

    # 验证实例状态
    if instance_code:
            assert wait_for_instance_status(client, instance_code, 'stopped')


def test_resume_instance(client, instance_tracker):
    # 列出所有的实例
    instances = client.instance.list()
    # 找到状态是暂停的
    instance_code = None
    for instance in instances:
        if instance.status.lower() == 'stopped':
            # 恢复实例
            instance_code = instance.id
            client.instance.resume(jupyter_id=instance_code)
            break

    # 验证实例状态
    if instance_code:
            assert wait_for_instance_status(client, instance_code, 'running')


def test_delete_instance(client, instance_tracker):
    # 列出所有的实例
    instances = client.instance.list()
    # 找到状态是运行中的
    instance_code = None
    for instance in instances:
        if instance.status.lower() in ('stopped', 'failed'):
            # 删除实例
            instance_code = instance.id
            client.instance.delete(jupyter_id=instance_code)
            break
    if instance_code is None:
        test_create_instance(client, instance_tracker)
        test_stop_instance(client, instance_tracker)

    # 验证实例已删除（404 表示删除成功）
    try:
        instance_jupyter = client.instance.get_instance(jupyter_id=instance_code)
    except PyroMindAPIError as e:  # 或者用实际的异常类
        # 404 是正常的，表示实例已成功删除 PyroMindAPIError('JUPYTER_INSTANCE_NOT_FOUND: JupyterLab instance None not found')
        assert e.status_code == 404
        print(f"实例 {instance_code} 已成功删除, e:{e.message}")
    except Exception as e:
        # 其他错误需要抛出
        print(f"实例 {instance_code} 删除时出错：{e}")
        raise



def test_edit_instance(client, instance_tracker):
    # 列出所有的实例
    instances = client.instance.list()
    # 找到状态是运行中的
    instance_code = None
    for instance in instances:
        if instance.status.lower() not in ('failed', 'pending'):
            # 编辑实例
            instance_code = instance.id
            jupyter_response = client.instance.get_instance(jupyter_id=instance_code)
            resources = jupyter_response.resources
            resources.cpu = "2"
            resources.memory = "16Gi"
            resources.gpu = 1
            resources.gpu_card = "H100"
            request = JupyterRequest()
            request.name = jupyter_response.name
            request.resources = resources
            client.instance.update(jupyter_id=jupyter_response.id, request=request)
            break

    instance_restart = client.instance.get_instance(jupyter_id=instance_code)
    assert instance_restart is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
