#!/usr/bin/env python3
"""
Jupyter Instance Management Example

This example demonstrates how to create, manage, and interact with Jupyter instances.

The API key can be provided via:
1. PYROMIND_API_KEY environment variable (recommended)
2. api_key parameter when initializing the client

If neither is provided, the client will raise a ValueError.
"""

from pyromind_sdk import PyroMindAPIClient, PyroMindAPIError
from pyromind_sdk.client.models import (
    JupyterRequest,
    ResourceConfig,
)


def create_jupyter_example():
    """Example: Create a new Jupyter instance"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print("Creating a new Jupyter instance...")
        instance = client.instance.create(
            JupyterRequest(
                name="example-jupyter",
                image="jupyter/scipy-notebook:latest",
                resources=ResourceConfig(
                    cpu="2",
                    memory="4Gi",
                    gpu=0
                ),
                environment_variables={
                    "JUPYTER_ENABLE_LAB": "yes",
                    "GRANT_SUDO": "yes"
                },
                auto_pause=True,
                auto_pause_timeout=3600  # Auto-pause after 1 hour of inactivity
            )
        )
        print(f"✓ Jupyter instance created successfully!")
        print(f"  ID: {instance.id}")
        print(f"  Name: {instance.name}")
        print(f"  Status: {instance.status}")
        if instance.url:
            print(f"  URL: {instance.url}")
        return instance.id
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to create Jupyter instance: {e.message}")
        return None
    finally:
        client.close()


def list_jupyter_example():
    """Example: List all Jupyter instances"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print("Listing all Jupyter instances...")
        instances = client.instance.list()
        print(f"Found {len(instances)} Jupyter instance(s):")
        
        for instance in instances:
            print(f"\n  Instance: {instance.name}")
            print(f"    ID: {instance.id}")
            print(f"    Status: {instance.status}")
            print(f"    Image: {instance.image}")
            if instance.url:
                print(f"    URL: {instance.url}")
        
        return instances
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to list Jupyter instances: {e.message}")
        return []
    finally:
        client.close()


def get_jupyter_example(jupyter_id: str):
    """Example: Get a specific Jupyter instance"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Getting Jupyter instance {jupyter_id}...")
        instance = client.instance.get_instance(jupyter_id)
        print(f"✓ Jupyter instance details:")
        print(f"  Name: {instance.name}")
        print(f"  Status: {instance.status}")
        print(f"  Image: {instance.image}")
        if instance.resources:
            print(f"  Resources:")
            print(f"    CPU: {instance.resources.cpu}")
            print(f"    Memory: {instance.resources.memory}")
            print(f"    GPU: {instance.resources.gpu}")
        if instance.url:
            print(f"  URL: {instance.url}")
        return instance
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to get Jupyter instance: {e.message}")
        return None
    finally:
        client.close()


def update_jupyter_example(jupyter_id: str):
    """Example: Update a Jupyter instance"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Updating Jupyter instance {jupyter_id}...")
        updated = client.instance.update(
            jupyter_id=jupyter_id,
            request=JupyterRequest(
                name="updated-jupyter",
                image="jupyter/tensorflow-notebook:latest",
                resources=ResourceConfig(
                    cpu="4",
                    memory="8Gi",
                    gpu=0
                )
            )
        )
        print(f"✓ Jupyter instance updated successfully!")
        print(f"  New Name: {updated.name}")
        print(f"  New Image: {updated.image}")
        return updated
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to update Jupyter instance: {e.message}")
        return None
    finally:
        client.close()


def pause_jupyter_example(jupyter_id: str):
    """Example: Pause a Jupyter instance"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Pausing Jupyter instance {jupyter_id}...")
        instance = client.instance.pause(jupyter_id)
        print(f"✓ Jupyter instance paused!")
        print(f"  Status: {instance.status}")
        return instance
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to pause Jupyter instance: {e.message}")
        return None
    finally:
        client.close()


def resume_jupyter_example(jupyter_id: str):
    """Example: Resume a paused Jupyter instance"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Resuming Jupyter instance {jupyter_id}...")
        instance = client.instance.resume(jupyter_id)
        print(f"✓ Jupyter instance resumed!")
        print(f"  Status: {instance.status}")
        return instance
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to resume Jupyter instance: {e.message}")
        return None
    finally:
        client.close()


def delete_jupyter_example(jupyter_id: str):
    """Example: Delete a Jupyter instance"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Deleting Jupyter instance {jupyter_id}...")
        client.instance.delete(jupyter_id)
        print(f"✓ Jupyter instance deleted successfully!")
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to delete Jupyter instance: {e.message}")
    finally:
        client.close()


def main():
    """Main example function"""
    print("=" * 60)
    print("Jupyter Instance Management Examples")
    print("=" * 60)
    
    # List existing instances
    instances = list_jupyter_example()
    
    # If we have instances, demonstrate operations
    if instances:
        jupyter_id = instances[0].id
        print(f"\nUsing Jupyter instance: {jupyter_id}")
        
        # Get instance details
        get_jupyter_example(jupyter_id)
        
        # Pause and resume (commented out to avoid disrupting running instances)
        # pause_jupyter_example(jupyter_id)
        # resume_jupyter_example(jupyter_id)
    else:
        print("\nNo existing Jupyter instances found. Creating a new one...")
        jupyter_id = create_jupyter_example()
        
        if jupyter_id:
            # Wait a bit for instance to be ready
            import time
            print("\nWaiting for Jupyter instance to be ready...")
            time.sleep(2)
            
            # Get instance details
            get_jupyter_example(jupyter_id)


if __name__ == "__main__":
    main()
