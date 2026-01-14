"""
Data models for PyroMind API Client SDK

This module defines Pydantic models for request and response data structures.
"""

from typing import Optional, List, Dict, Any, Literal, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# Common Models
class APIResponse(BaseModel):
    """Base API response model"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    code: Optional[int] = None
    version: Optional[str] = None


class ResourceConfig(BaseModel):
    """Resource configuration model"""
    cpu: Optional[str] = None
    memory: Optional[str] = None
    gpu: Optional[int] = None
    gpu_type: Optional[str] = None

    @field_validator('cpu', mode='before')
    @classmethod
    def validate_cpu(cls, v: Optional[Union[int, str]]) -> Optional[str]:
        """Validate and convert cpu field, accept integer or string, convert to string"""
        if v is None:
            return None
        # If integer, convert to string
        if isinstance(v, int):
            return str(v)
        # If string, return as is
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        # Other types raise error
        raise ValueError(f"cpu must be an integer or string, got {type(v).__name__}")

    @field_validator('memory', mode='before')
    @classmethod
    def validate_memory(cls, v: Optional[Union[int, str]]) -> Optional[str]:
        """Validate and convert memory field, accept integer or string, convert to string with 'Gi' unit"""
        if v is None:
            return None
        # If integer, add 'Gi' unit
        if isinstance(v, int):
            return f"{v}Gi"
        # If string, return as is
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        # Other types raise error
        raise ValueError(f"memory must be an integer or string, got {type(v).__name__}")

    @field_validator('gpu', mode='before')
    @classmethod
    def validate_gpu(cls, v: Optional[Union[int, str]]) -> Optional[int]:
        """Validate and convert gpu field, accept integer or string, keep as integer"""
        if v is None:
            return None
        # If string, convert to integer
        if isinstance(v, str):
            try:
                return int(v.strip())
            except ValueError:
                raise ValueError(f"gpu must be a valid integer, got '{v}'")
        # If integer, return as is
        if isinstance(v, int):
            return v
        # Other types raise error
        raise ValueError(f"gpu must be an integer or string, got {type(v).__name__}")


# Sandbox Models
class SandboxType(str, Enum):
    """Sandbox type enumeration"""
    LINUX = "linux"
    WINDOWS = "windows"


class SandboxStatus(str, Enum):
    """Sandbox status enumeration"""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class ScreenResolution(BaseModel):
    """Screen resolution model"""
    width: int
    height: int


class SandboxConfiguration(BaseModel):
    """Sandbox configuration model"""
    image: str
    resources: Optional[ResourceConfig] = None
    screen_resolution: Optional[ScreenResolution] = None
    environment_variables: Optional[Dict[str, str]] = None


class SandboxCreateRequest(BaseModel):
    """Request model for creating a sandbox"""
    name: str
    type: SandboxType
    configuration: SandboxConfiguration


class SandboxUsage(BaseModel):
    """Sandbox usage statistics"""
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    gpu_usage: Optional[float] = None


class SandboxResponse(BaseModel):
    """Sandbox response model"""
    id: str
    name: str
    type: SandboxType
    status: SandboxStatus
    configuration: SandboxConfiguration
    usage: Optional[SandboxUsage] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SandboxListAPIResponse(BaseModel):
    """List sandboxes API response"""
    sandboxes: List[SandboxResponse]


class SandboxAPIResponse(BaseModel):
    """Single sandbox API response"""
    sandbox: SandboxResponse


# Action Models
class ActionStatus(str, Enum):
    """Action status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionParameters(BaseModel):
    """Action parameters model"""
    command: Optional[str] = None
    working_directory: Optional[str] = None
    environment_variables: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None


class ActionRequest(BaseModel):
    """Action request model"""
    action: str
    parameters: Optional[ActionParameters] = None


class ActionResult(BaseModel):
    """Action result model"""
    action_id: str
    status: ActionStatus
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ActionResponse(BaseModel):
    """Action response model"""
    result: ActionResult


class ActionAPIResponse(BaseModel):
    """Action API response"""
    action: ActionResponse


class BatchActionRequest(BaseModel):
    """Batch action request model"""
    actions: List[ActionRequest]


class BatchActionAPIResponse(BaseModel):
    """Batch action API response"""
    actions: List[ActionResponse]


# VNC Models
class VNCConnectionInfo(BaseModel):
    """VNC connection information"""
    host: str
    port: int
    password: Optional[str] = None
    websocket_url: Optional[str] = None


class VNCResponse(BaseModel):
    """VNC response model"""
    connection: VNCConnectionInfo


class VncAPIResponse(BaseModel):
    """VNC API response"""
    vnc: VNCResponse


# Instance (Jupyter) Models
class JupyterRequest(BaseModel):
    """Request model for creating/updating a Jupyter instance"""
    name: Optional[str] = None
    resources: Optional[ResourceConfig] = None
    configuration: Optional[Dict[str, Any]] = None
    public_key: Optional[Union[str, List[str]]] = None
    timeout: Optional[int] = None


class JupyterResponse(BaseModel):
    """Jupyter instance response model"""
    id: str
    name: str
    status: str
    password: Optional[str] = None
    resources: Optional[ResourceConfig] = None
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class JupyterListAPIResponse(BaseModel):
    """List Jupyter instances API response"""
    instances: List[JupyterResponse]


class JupyterAPIResponse(BaseModel):
    """Single Jupyter instance API response"""
    instance: JupyterResponse


# Inference Models
class InferenceJobCreateRequest(BaseModel):
    """Request model for creating an inference job"""
    model_path: str
    inference_framework: str
    timeout: Optional[int] = None
    resources: Optional[ResourceConfig] = None
    environment_variables: Optional[Dict[str, str]] = None


class InferenceJobResponse(BaseModel):
    """Inference job response model"""
    id: str
    name: str
    model_path: str
    image: str
    status: str
    resources: Optional[ResourceConfig] = None
    endpoint_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class InferenceJobListAPIResponse(BaseModel):
    """List inference jobs API response"""
    inference_jobs: List[InferenceJobResponse] = Field(default_factory=list)
    page: Optional[int] = None
    page_size: Optional[int] = None
    total: Optional[int] = None
    has_more: Optional[bool] = None


class InferenceJobAPIResponse(BaseModel):
    """Single inference job API response"""
    job: InferenceJobResponse


class InferenceJobCreateAPIResponse(BaseModel):
    """Create inference job API response"""
    job_id: str


# Training Models
class TrainingFramework(str, Enum):
    """Training framework enumeration"""
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    JAX = "jax"
    HUGGINGFACE = "huggingface"


class TrainingJobStatus(str, Enum):
    """Training job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingJobCreateRequest(BaseModel):
    """Request model for creating a training job"""
    name: str
    framework: TrainingFramework
    script_path: str
    image: str
    resources: Optional[ResourceConfig] = None
    environment_variables: Optional[Dict[str, str]] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    data_path: Optional[str] = None
    output_path: Optional[str] = None


class TrainingJobResponse(BaseModel):
    """Training job response model"""
    id: str
    name: str
    framework: TrainingFramework
    script_path: str
    image: str
    status: TrainingJobStatus
    resources: Optional[ResourceConfig] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    data_path: Optional[str] = None
    output_path: Optional[str] = None
    logs_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TrainingJobListAPIResponse(BaseModel):
    """List training jobs API response"""
    jobs: List[TrainingJobResponse]


class TrainingJobAPIResponse(BaseModel):
    """Single training job API response"""
    job: TrainingJobResponse
