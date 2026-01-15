#!/usr/bin/env python3
"""
Inference Job Management Example

This example demonstrates how to create, manage, and interact with inference jobs.

The API key can be provided via:
1. PYROMIND_API_KEY environment variable (recommended)
2. api_key parameter when initializing the client

If neither is provided, the client will raise a ValueError.
"""

from pyromind_sdk import PyroMindAPIClient, PyroMindAPIError
import time

if __name__ == "__main__":
    client = PyroMindAPIClient()
    instances = client.instance.list()
    print(f"Found {len(instances)} instances")
    for instance in instances:
        if instance.status != 'stopped':
            print(f"Pausing instance {instance.id}")
            client.instance.pause(instance.id)
    # [TODO] fix me, we should not wait for 10 seconds, we should be able to delete the instance immediately after pausing it
    time.sleep(10)
    for instance in instances:
        print(f"Deleting instance {instance.id}")
        client.instance.delete(instance.id)
        