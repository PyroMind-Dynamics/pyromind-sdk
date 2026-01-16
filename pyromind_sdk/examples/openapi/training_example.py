#!/usr/bin/env python3
"""
Training Job Management Example

This example demonstrates how to create, manage, and interact with training jobs.

The API key can be provided via:
1. PYROMIND_API_KEY environment variable (recommended)
2. api_key parameter when initializing the client

If neither is provided, the client will raise a ValueError.
"""

from pyromind_sdk import PyroMindAPIClient, PyroMindAPIError
from pyromind_sdk.client.models import (
    TrainingJobCreateRequest,
    TrainingFramework,
    ResourceConfig,
)


def create_training_job_example():
    """Example: Create a new training job"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print("Creating a new training job...")
        job = client.training.create(
            TrainingJobCreateRequest(
                name="example-training",
                framework=TrainingFramework.PYTORCH,
                script_path="/scripts/train.py",
                image="pytorch/pytorch:latest",
                resources=ResourceConfig(
                    cpu="8",
                    memory="16Gi",
                    gpu=2,
                    gpu_type="nvidia-tesla-v100"
                ),
                environment_variables={
                    "CUDA_VISIBLE_DEVICES": "0,1",
                    "PYTHONUNBUFFERED": "1"
                },
                hyperparameters={
                    "learning_rate": 0.001,
                    "batch_size": 32,
                    "epochs": 100,
                    "optimizer": "adam"
                },
                data_path="/data/training",
                output_path="/output/models"
            )
        )
        print(f"✓ Training job created successfully!")
        print(f"  ID: {job.id}")
        print(f"  Name: {job.name}")
        print(f"  Status: {job.status}")
        print(f"  Framework: {job.framework}")
        print(f"  Script Path: {job.script_path}")
        if job.logs_url:
            print(f"  Logs URL: {job.logs_url}")
        return job.id
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to create training job: {e.message}")
        return None
    finally:
        client.close()


def list_training_jobs_example():
    """Example: List all training jobs"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print("Listing all training jobs...")
        jobs = client.training.list()
        print(f"Found {len(jobs)} training job(s):")
        
        for job in jobs:
            print(f"\n  Job: {job.name}")
            print(f"    ID: {job.id}")
            print(f"    Status: {job.status}")
            print(f"    Framework: {job.framework}")
            print(f"    Script Path: {job.script_path}")
            if job.logs_url:
                print(f"    Logs URL: {job.logs_url}")
        
        return jobs
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to list training jobs: {e.message}")
        return []
    finally:
        client.close()


def get_training_job_example(job_id: str):
    """Example: Get a specific training job"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Getting training job {job_id}...")
        job = client.training.get_job(job_id)
        print(f"✓ Training job details:")
        print(f"  Name: {job.name}")
        print(f"  Status: {job.status}")
        print(f"  Framework: {job.framework}")
        print(f"  Script Path: {job.script_path}")
        if job.resources:
            print(f"  Resources:")
            print(f"    CPU: {job.resources.cpu}")
            print(f"    Memory: {job.resources.memory}")
            print(f"    GPU: {job.resources.gpu}")
        if job.hyperparameters:
            print(f"  Hyperparameters: {job.hyperparameters}")
        if job.logs_url:
            print(f"  Logs URL: {job.logs_url}")
        if job.started_at:
            print(f"  Started At: {job.started_at}")
        if job.completed_at:
            print(f"  Completed At: {job.completed_at}")
        return job
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to get training job: {e.message}")
        return None
    finally:
        client.close()


def stop_training_job_example(job_id: str):
    """Example: Stop a training job"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Stopping training job {job_id}...")
        job = client.training.stop(job_id)
        print(f"✓ Training job stopped!")
        print(f"  Status: {job.status}")
        return job
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to stop training job: {e.message}")
        return None
    finally:
        client.close()


def delete_training_job_example(job_id: str):
    """Example: Delete a training job"""
    # API key is read from PYROMIND_API_KEY environment variable
    client = PyroMindAPIClient()
    
    try:
        print(f"Deleting training job {job_id}...")
        client.training.delete(job_id)
        print(f"✓ Training job deleted successfully!")
        
    except PyroMindAPIError as e:
        print(f"✗ Failed to delete training job: {e.message}")
    finally:
        client.close()


def main():
    """Main example function"""
    print("=" * 60)
    print("Training Job Management Examples")
    print("=" * 60)
    
    # List existing jobs
    jobs = list_training_jobs_example()
    
    # If we have jobs, demonstrate operations
    if jobs:
        job_id = jobs[0].id
        print(f"\nUsing training job: {job_id}")
        
        # Get job details
        get_training_job_example(job_id)
        
        # Pause and resume (commented out to avoid disrupting running jobs)
        # stop_training_job_example(job_id)
    else:
        print("\nNo existing training jobs found. Creating a new one...")
        job_id = create_training_job_example()
        
        if job_id:
            # Wait a bit for job to be ready
            import time
            print("\nWaiting for training job to be ready...")
            time.sleep(2)
            
            # Get job details
            get_training_job_example(job_id)


if __name__ == "__main__":
    main()
