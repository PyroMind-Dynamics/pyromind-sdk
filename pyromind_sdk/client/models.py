"""
Data models for PyroMind API Client SDK

This module defines Pydantic models for request and response data structures.
"""

from typing import Optional, List, Dict, Any, Literal, Union
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


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
    verl = "verl"
    slime = "slime"


class TrainingTaskCreateRequest(BaseModel):
    """Request model for creating a training task"""
    name: str
    framework: TrainingFramework
    environment_config: Dict[str, str]  # Configuration for the RL environment
    model_configuration: Dict[str, str]  # Configuration for the model
    training_config: Dict[str, str]  # Configuration for the training process
    resources: Optional[ResourceConfig] = None
    checkpoint_interval: Optional[int] = 300  # in seconds
    data_source: Optional[Dict[str, str]] = None  # Where to get training data from
    output_config: Optional[Dict[str, str]] = None  # Where to store results/models


class TrainingTaskNodeInfo(BaseModel):
    """Training task node information"""
    node_id: int
    task_id: int
    node_name: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    duration: Optional[timedelta] = None  # Duration as timedelta object
    cpu_num: Optional[float] = None  # CPU number in cores (e.g., 4.0 from "4c")
    cpu_memory: Optional[float] = None  # Memory in GiB (e.g., 80.0 from "80.0Gi")
    gpu_type: Optional[str] = None  # GPU device type (e.g., "H100", "A100")
    gpu_num: Optional[int] = 0  # GPU number, default to 0 if not specified or "-"
    amount: Optional[float] = None  # Cost amount in float
    url: Optional[str] = None
    wand_flag: Optional[str] = None
    
    @model_validator(mode='before')
    @classmethod
    def parse_gpu_fields(cls, data):
        """Parse GPU fields from gpu_num string format like 'H100*4'"""
        if isinstance(data, dict) and 'gpu_num' in data:
            gpu_value = data.get('gpu_num')
            if isinstance(gpu_value, str) and gpu_value.strip() not in ["-", ""]:
                # Parse format like "H100*4"
                if "*" in gpu_value:
                    parts = gpu_value.split("*")
                    if len(parts) == 2:
                        data['gpu_type'] = parts[0].strip()
                        try:
                            data['gpu_num'] = int(parts[1].strip())
                        except (ValueError, IndexError):
                            data['gpu_num'] = 0
                    else:
                        data['gpu_num'] = 0
                else:
                    # If it's just a number string, try to parse it
                    try:
                        data['gpu_num'] = int(gpu_value.strip())
                    except (ValueError, TypeError):
                        data['gpu_num'] = 0
            elif gpu_value in [None, "-", ""]:
                data['gpu_num'] = 0
        return data
    
    @field_validator('cpu_num', mode='before')
    @classmethod
    def parse_cpu_num(cls, v):
        """Parse CPU number from string like '4c' to float"""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            v = v.strip()
            if v == "" or v == "-":
                return None
            # Remove 'c' suffix if present (e.g., "4c" -> "4")
            if v.endswith('c'):
                v = v[:-1].strip()
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        return None
    
    @field_validator('cpu_memory', mode='before')
    @classmethod
    def parse_cpu_memory(cls, v):
        """Parse CPU memory from string like '80.0Gi' to float (in GiB)"""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            v = v.strip()
            if v == "" or v == "-":
                return None
            # Remove common suffixes: Gi, GB, Mi, MB, etc.
            import re
            # Match number followed by optional unit
            match = re.match(r'^([\d.]+)', v)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, TypeError):
                    return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        return None
    
    @field_validator('amount', mode='before')
    @classmethod
    def parse_amount(cls, v):
        """Parse amount from string or number to float"""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            v = v.strip()
            if v == "" or v == "-":
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        return None
    
    @field_validator('duration', mode='before')
    @classmethod
    def parse_duration(cls, v):
        """Parse duration from string to timedelta
        
        Handles formats like:
        - "00:22:16" -> timedelta(hours=0, minutes=22, seconds=16)
        - "1day 02:30:45" -> timedelta(days=1, hours=2, minutes=30, seconds=45)
        - "2days 05:10:20" -> timedelta(days=2, hours=5, minutes=10, seconds=20)
        """
        if v is None:
            return None
        if isinstance(v, timedelta):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v == "" or v == "-":
                return None
            try:
                # Parse format like "1day 02:30:45" or "2days 05:10:20"
                if "day" in v.lower():
                    # Format: "Nd HH:MM:SS" or "Ndays HH:MM:SS"
                    parts = v.split()
                    days = 0
                    time_str = ""
                    
                    for part in parts:
                        part_lower = part.lower()
                        if "day" in part_lower:
                            # Extract number from "1day" or "2days"
                            import re
                            match = re.search(r'(\d+)', part)
                            if match:
                                days = int(match.group(1))
                        elif ":" in part:
                            time_str = part
                    
                    if time_str:
                        # Parse HH:MM:SS
                        time_parts = time_str.split(":")
                        if len(time_parts) == 3:
                            hours = int(time_parts[0])
                            minutes = int(time_parts[1])
                            seconds = int(time_parts[2])
                            return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
                    elif days > 0:
                        return timedelta(days=days)
                
                # Parse format like "HH:MM:SS" or "MM:SS"
                elif ":" in v:
                    time_parts = v.split(":")
                    if len(time_parts) == 3:
                        # HH:MM:SS
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        seconds = int(time_parts[2])
                        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
                    elif len(time_parts) == 2:
                        # MM:SS
                        minutes = int(time_parts[0])
                        seconds = int(time_parts[1])
                        return timedelta(minutes=minutes, seconds=seconds)
                
                # Try to parse as seconds (integer string)
                try:
                    seconds = float(v)
                    return timedelta(seconds=seconds)
                except ValueError:
                    return None
            except (ValueError, TypeError, IndexError):
                return None
        return None
    
    @field_validator('start_at', 'end_at', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime from string if needed"""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                # Try ISO format first (most common)
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                try:
                    # Try common datetime formats
                    from datetime import datetime as dt
                    # Try various formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                        try:
                            return dt.strptime(v, fmt)
                        except ValueError:
                            continue
                    return None
                except (ValueError, TypeError):
                    return None
        return None
    


class TrainingTaskResponse(BaseModel):
    """Training task response model"""
    task_id: str
    name: str
    status: str  # Using task status from backend
    metrics: Optional[Dict[str, Any]] = None  # Training metrics
    nodes: Optional[List[TrainingTaskNodeInfo]] = None  # List of nodes in this task
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @field_validator('created_at', 'started_at', 'completed_at', 'expires_at', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime from string if needed"""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                # Try ISO format first (most common)
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                try:
                    # Try common datetime formats
                    from datetime import datetime as dt
                    # Try various formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                        try:
                            return dt.strptime(v, fmt)
                        except ValueError:
                            continue
                    return None
                except (ValueError, TypeError):
                    return None
        return None


class TrainingTaskListAPIResponse(BaseModel):
    """List training jobs API response"""
    tasks: List[TrainingTaskResponse]


class TrainingTaskAPIResponse(BaseModel):
    """Single training job API response"""
    job: TrainingTaskResponse
