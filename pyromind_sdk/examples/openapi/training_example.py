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
)


def create_training_task_example():
    """Example: Create a new training task"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print("Creating a new training task...")
        # Load workflow from JSON file (recommended)
        import json
        from pathlib import Path
        workflow_path = Path(__file__).parent / "workflows" / "llm_test.json"
        if workflow_path.exists():
            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)
        task = client.training.create(
            TrainingTaskCreateRequest(
                name="example-training",
                workflow=workflow
            )
        )
        print(f"✓ Training task created successfully!")
        print(f"  ID: {task.task_id}")
        print(f"  Name: {task.name}")
        print(f"  Status: {task.status}")
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
        if task.started_at:
            if isinstance(task.started_at, str):
                print(f"  Started At: {task.started_at}")
            else:
                print(f"  Started At: {task.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if task.completed_at:
            if isinstance(task.completed_at, str):
                print(f"  Completed At: {task.completed_at}")
            else:
                print(f"  Completed At: {task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if task.created_at:
            if isinstance(task.created_at, str):
                print(f"  Created At: {task.created_at}")
            else:
                print(f"  Created At: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Display nodes information
        if task.nodes:
            print(f"\n  Nodes ({len(task.nodes)}):")
            for i, node in enumerate(task.nodes, 1):
                print(f"    Node {i}:")
                print(f"      ID: {node.node_id}")
                print(f"      Name: {node.node_name}")
                if node.start_at:
                    if isinstance(node.start_at, str):
                        print(f"      Started At: {node.start_at}")
                    else:
                        print(f"      Started At: {node.start_at.strftime('%Y-%m-%d %H:%M:%S')}")
                if node.end_at:
                    if isinstance(node.end_at, str):
                        print(f"      Ended At: {node.end_at}")
                    else:
                        print(f"      Ended At: {node.end_at.strftime('%Y-%m-%d %H:%M:%S')}")
                if node.duration:
                    # Format timedelta as readable string
                    if isinstance(node.duration, str):
                        print(f"      Duration: {node.duration}")
                    else:
                        total_seconds = int(node.duration.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        if hours > 0:
                            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        else:
                            duration_str = f"{minutes:02d}:{seconds:02d}"
                        print(f"      Duration: {duration_str}")
                # Display resource information from resources field
                if node.resources:
                    if node.resources.cpu:
                        print(f"      CPU: {node.resources.cpu}")
                    if node.resources.memory:
                        print(f"      Memory: {node.resources.memory}")
                    if node.resources.gpu:
                        gpu_info = node.resources.gpu
                        if node.resources.gpu_card:
                            gpu_info = f"{node.resources.gpu_card}*{node.resources.gpu}"
                        print(f"      GPU: {gpu_info}")
                if node.amount is not None:
                    print(f"      Cost: ${node.amount:.3f}")
                if node.url:
                    print(f"      WandB URL: {node.url}")
        else:
            print(f"\n  Nodes: None or empty")
        
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
    create_training_task_example()
    # main()
