# PyroMind API Client SDK

Python client SDK for interacting with the PyroMind API v1.

## Installation

```bash
pip install pyromind-sdk
```

## Quick Start

### Setting up API Key

The API key can be provided in two ways:

1. **Environment variable (recommended):**
```bash
export PYROMIND_API_KEY="your-api-key"
```

2. **As a parameter:**
```python
client = PyroMindAPIClient(api_key="your-api-key")
```

**Note:** If neither is provided, the client will raise a `ValueError`.

### Basic Usage

```python
from pyromind_sdk import PyroMindAPIClient
from pyromind_sdk.client.models import (
    JupyterRequest,
    ResourceConfig,
    SandboxCreateRequest,
    SandboxConfiguration,
    SandboxType,
    InferenceJobCreateRequest,
    TrainingJobCreateRequest,
    TrainingFramework,
)

# Initialize the client (reads from PYROMIND_API_KEY environment variable)
client = PyroMindAPIClient()

# Or explicitly provide the API key
# client = PyroMindAPIClient(api_key="your-api-key")

# Or use context manager
with PyroMindAPIClient(api_key="your-api-key") as client:
    # Your code here
    pass
```

## Sandboxes

### List all sandboxes

```python
sandboxes = client.sandboxes.list()
for sandbox in sandboxes:
    print(f"Sandbox: {sandbox.name} - Status: {sandbox.status}")
```

### Create a sandbox

```python
from pyromind_sdk.client.models import (
    SandboxCreateRequest,
    SandboxConfiguration,
    SandboxType,
    ResourceConfig,
    ScreenResolution,
)

sandbox = client.sandboxes.create(
    SandboxCreateRequest(
        name="my-sandbox",
        type=SandboxType.LINUX,
        configuration=SandboxConfiguration(
            image="ubuntu:22.04",
            resources=ResourceConfig(cpu="2", memory="4Gi", gpu=1),
            screen_resolution=ScreenResolution(width=1920, height=1080)
        )
    )
)
print(f"Created sandbox: {sandbox.id}")
```

### Get a sandbox

```python
sandbox = client.sandboxes.get_sandbox(sandbox_id="sandbox-id")
print(f"Sandbox status: {sandbox.status}")
```

### Execute an action in a sandbox

```python
from pyromind_sdk.client.models import ActionRequest, ActionParameters

action = client.sandboxes.execute_action(
    sandbox_id="sandbox-id",
    request=ActionRequest(
        action="run_command",
        parameters=ActionParameters(
            command="echo 'Hello, World!'",
            working_directory="/home/user"
        )
    )
)
print(f"Action status: {action.result.status}")
```

### Delete a sandbox

```python
client.sandboxes.delete(sandbox_id="sandbox-id")
```

## Instance (Jupyter)

### List all Jupyter instances

```python
instances = client.instance.list()
for instance in instances:
    print(f"Instance: {instance.name} - Status: {instance.status}")
```

### Create a Jupyter instance

```python
instance = client.instance.create(
    JupyterRequest(
        name="my-jupyter",
        image="jupyter/scipy-notebook:latest",
        resources=ResourceConfig(cpu="2", memory="4Gi", gpu=1),
        auto_pause=True,
        auto_pause_timeout=3600
    )
)
print(f"Created instance: {instance.id}")
print(f"Jupyter URL: {instance.url}")
```

### Get a Jupyter instance

```python
instance = client.instance.get_instance(jupyter_id="jupyter-id")
print(f"Instance status: {instance.status}")
```

### Update a Jupyter instance

```python
updated = client.instance.update(
    jupyter_id="jupyter-id",
    request=JupyterRequest(
        name="updated-jupyter",
        image="jupyter/tensorflow-notebook:latest",
        resources=ResourceConfig(cpu="4", memory="8Gi")
    )
)
```

### Pause/Resume a Jupyter instance

```python
# Pause
client.instance.pause(jupyter_id="jupyter-id")

# Resume
client.instance.resume(jupyter_id="jupyter-id")
```

### Delete a Jupyter instance

```python
client.instance.delete(jupyter_id="jupyter-id")
```

## Inference

### List all inference jobs

```python
jobs = client.inference.list()
for job in jobs:
    print(f"Job: {job.name} - Status: {job.status}")
```

### Create an inference job

```python
job = client.inference.create(
    InferenceJobCreateRequest(
        name="my-inference",
        model_path="/models/my-model",
        image="pytorch/pytorch:latest",
        resources=ResourceConfig(cpu="4", memory="8Gi", gpu=1),
        endpoint_url="https://api.example.com/inference"
    )
)
print(f"Created inference job: {job.id}")
```

### Get an inference job

```python
job = client.inference.get_job(job_id="job-id")
print(f"Job status: {job.status}")
print(f"Endpoint URL: {job.endpoint_url}")
```

### Delete an inference job

```python
client.inference.delete(job_id="job-id")
```

## Training

### List all training jobs

```python
jobs = client.training.list()
for job in jobs:
    print(f"Job: {job.name} - Status: {job.status}")
```

### Create a training job

```python
job = client.training.create(
    TrainingJobCreateRequest(
        name="my-training",
        framework=TrainingFramework.PYTORCH,
        script_path="/scripts/train.py",
        image="pytorch/pytorch:latest",
        resources=ResourceConfig(cpu="8", memory="16Gi", gpu=2),
        hyperparameters={"learning_rate": 0.001, "batch_size": 32},
        data_path="/data/training",
        output_path="/output/models"
    )
)
print(f"Created training job: {job.id}")
```

### Get a training job

```python
job = client.training.get_job(job_id="job-id")
print(f"Job status: {job.status}")
print(f"Logs URL: {job.logs_url}")
```

### Pause/Resume a training job

```python
# Pause
client.training.pause(job_id="job-id")

# Resume
client.training.resume(job_id="job-id")
```

### Delete a training job

```python
client.training.delete(job_id="job-id")
```

## Error Handling

```python
from pyromind_sdk import PyroMindAPIError

try:
    sandbox = client.sandboxes.get_sandbox(sandbox_id="invalid-id")
except PyroMindAPIError as e:
    print(f"API Error: {e.message}")
    print(f"Status Code: {e.status_code}")
    print(f"Response: {e.response}")
```

## Advanced Usage

### Using individual clients

You can also use individual resource clients directly:

```python
from pyromind_sdk import SandboxesClient

sandboxes_client = SandboxesClient(api_key="your-api-key")
sandboxes = sandboxes_client.list()
```

### Custom base URL and timeout

```python
client = PyroMindAPIClient(
    api_key="your-api-key",
    base_url="https://custom-api.example.com/api/v1",
    timeout=60,
    max_retries=5
)
```

## API Reference

For detailed API documentation, see [PyroMind API v1 Docs](https://pyromind.ai/api/v1/docs).
