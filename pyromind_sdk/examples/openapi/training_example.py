#!/usr/bin/env python3
"""
Training Task Management Example

This example demonstrates how to create, manage, and interact with training tasks.

The API key can be provided via:
1. PYROMIND_API_KEY environment variable (recommended)
2. api_key parameter when initializing the client

If neither is provided, the client will raise a ValueError.
"""

from pyromind_sdk import PyroMindAPIClient, PyroMindAPIError
from pyromind_sdk.client.models import (
    TrainingTaskCreateRequest,
    TrainingFramework,
    ResourceConfig,
)


def create_training_task_example():
    """Example: Create a new training task"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print("Creating a new training task...")
        task = client.training.create(
            TrainingTaskCreateRequest(
                name="example-training",
                framework=TrainingFramework.verl,
                environment_config={
                    "env_type": "gym",
                    "env_name": "CartPole-v1"
                },
                model_configuration={
                    "model_type": "ppo",
                    "hidden_size": 256
                },
                training_config={
                    "learning_rate": 0.001,
                    "batch_size": 32,
                    "epochs": 100,
                    "optimizer": "adam"
                },
                resources=ResourceConfig(
                    cpu="8",
                    memory="16Gi",
                    gpu=2
                ),
                checkpoint_interval=300,
                data_source={
                    "type": "local",
                    "path": "/data/training"
                },
                output_config={
                    "type": "local",
                    "path": "/output/models"
                }
            )
        )
        print(f"✓ Training task created successfully!")
        print(f"  ID: {task.task_id}")
        print(f"  Name: {task.name}")
        print(f"  Status: {task.status}")
        if task.logs_url:
            print(f"  Logs URL: {task.logs_url}")
        return task.task_id
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to create training task: {e.message}")
        return None
    finally:
        client.close()


def list_training_tasks_example():
    """Example: List all training tasks"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print("Listing all training tasks...")
        tasks = client.training.list()
        print(f"Found {len(tasks)} training task(s):")
        
        for task in tasks:
            print(f"\n  Task: {task.name}")
            print(f"    ID: {task.task_id}")
            print(f"    Status: {task.status}")
            if task.logs_url:
                print(f"    Logs URL: {task.logs_url}")
        
        return tasks
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to list training tasks: {e.message}")
        return []
    finally:
        client.close()


def get_training_task_example(task_id: str):
    """Example: Get a specific training task"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Getting training task {task_id}...")
        task = client.training.get_task(task_id)
        print(f"✓ Training task details:")
        print(f"  Name: {task.name}")
        print(f"  Status: {task.status}")
        if task.logs_url:
            print(f"  Logs URL: {task.logs_url}")
        if task.started_at:
            print(f"  Started At: {task.started_at}")
        if task.completed_at:
            print(f"  Completed At: {task.completed_at}")
        return task
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to get training task: {e.message}")
        return None
    finally:
        client.close()


def stop_training_task_example(task_id: str):
    """Example: Stop a training task"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Stopping training task {task_id}...")
        task = client.training.stop(task_id)
        print(f"✓ Training task stopped!")
        print(f"  Status: {task.status}")
        return task
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to stop training task: {e.message}")
        return None
    finally:
        client.close()


def delete_training_task_example(task_id: str):
    """Example: Delete a training task"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Deleting training task {task_id}...")
        client.training.delete(task_id)
        print(f"✓ Training task deleted successfully!")
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to delete training task: {e.message}")
    finally:
        client.close()


def main():
    """Main example function"""
    print("=" * 60)
    print("Training Task Management Examples")
    print("=" * 60)
    
    # List existing tasks
    tasks = list_training_tasks_example()
    
    # If we have tasks, demonstrate operations
    if tasks:
        task_id = tasks[0].task_id
        print(f"\nUsing training task: {task_id}")
        
        # Get task details
        get_training_task_example(task_id)
        
        # Stop task (commented out to avoid disrupting running tasks)
        # stop_training_task_example(task_id)
    else:
        print("\nNo existing training tasks found. Creating a new one...")
        task_id = create_training_task_example()
        
        if task_id:
            # Wait a bit for task to be ready
            import time
            print("\nWaiting for training task to be ready...")
            time.sleep(2)
            
            # Get task details
            get_training_task_example(task_id)


if __name__ == "__main__":
    tasks = list_training_tasks_example()
    print(get_training_task_example(tasks[0].task_id))
    # main()
