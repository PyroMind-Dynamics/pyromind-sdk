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


def create_training_job_example():
    """Example: Create a new training task"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print("Creating a new training task...")
        job = client.training.create(
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
        print(f"  ID: {job.task_id}")
        print(f"  Name: {job.name}")
        print(f"  Status: {job.status}")
        if job.logs_url:
            print(f"  Logs URL: {job.logs_url}")
        return job.task_id
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to create training task: {e.message}")
        return None
    finally:
        client.close()


def list_training_jobs_example():
    """Example: List all training tasks"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print("Listing all training tasks...")
        jobs = client.training.list()
        print(f"Found {len(jobs)} training task(s):")
        
        for job in jobs:
            print(f"\n  Task: {job.name}")
            print(f"    ID: {job.task_id}")
            print(f"    Status: {job.status}")
            if job.logs_url:
                print(f"    Logs URL: {job.logs_url}")
        
        return jobs
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to list training tasks: {e.message}")
        return []
    finally:
        client.close()


def get_training_job_example(job_id: str):
    """Example: Get a specific training task"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Getting training task {job_id}...")
        job = client.training.get_job(job_id)
        print(f"✓ Training task details:")
        print(f"  Name: {job.name}")
        print(f"  Status: {job.status}")
        if job.logs_url:
            print(f"  Logs URL: {job.logs_url}")
        if job.started_at:
            print(f"  Started At: {job.started_at}")
        if job.completed_at:
            print(f"  Completed At: {job.completed_at}")
        return job
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to get training task: {e.message}")
        return None
    finally:
        client.close()


def stop_training_job_example(job_id: str):
    """Example: Stop a training task"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Stopping training task {job_id}...")
        job = client.training.stop(job_id)
        print(f"✓ Training task stopped!")
        print(f"  Status: {job.status}")
        return job
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to stop training task: {e.message}")
        return None
    finally:
        client.close()


def delete_training_job_example(job_id: str):
    """Example: Delete a training task"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Deleting training task {job_id}...")
        client.training.delete(job_id)
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
    jobs = list_training_jobs_example()
    
    # If we have tasks, demonstrate operations
    if jobs:
        job_id = jobs[0].task_id
        print(f"\nUsing training task: {job_id}")
        
        # Get task details
        get_training_job_example(job_id)
        
        # Stop task (commented out to avoid disrupting running tasks)
        # stop_training_job_example(job_id)
    else:
        print("\nNo existing training tasks found. Creating a new one...")
        job_id = create_training_job_example()
        
        if job_id:
            # Wait a bit for task to be ready
            import time
            print("\nWaiting for training task to be ready...")
            time.sleep(2)
            
            # Get task details
            get_training_job_example(job_id)


if __name__ == "__main__":
    jobs = list_training_jobs_example()
    print(jobs)
    # main()
