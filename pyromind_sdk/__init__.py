"""
PyroMind Node SDK

A lightweight SDK stub for local development and testing of third-party nodes 
without the full platform codebase (without `app.models.nodes`).

In the real platform runtime environment, nodes should prioritize importing 
base classes from `app.models.nodes`.
"""

__version__ = "0.1.0"

# Export YAML nodes functionality
from .nodes import (
    load_nodes_from_yaml,
    load_all_nodes_from_directory,
    create_node_class_from_yaml,
    convert_node_class_to_yaml,
    yaml_to_node_class,
)

# Export API client functionality
from .client import (
    PyroMindClient,
    PyroMindAPIError,
    SandboxesClient,
    InstanceClient,
    InferenceClient,
    TrainingClient,
    StorageClient,
    PyroMindAPIClient,
)

# Export xyFlow models
from .client.xyflow_models import (
    PositionDTO,
    ViewportDTO,
    XyflowNodeDataDTO,
    XyflowNodeDTO,
    XyflowEdgeDTO,
    XyflowWorkflowDTO,
)

# Export workflow functionality
from .client.workflow import (
    WorkflowLiteConverter,
    LayoutGenerator,
    to_workflow_lite,
    to_workflow_standard,
    XyflowWorkflowBuilder,
    WorkflowFormat,
    detect_format,
    to_xyflow,
    to_lite,
    to_standard,
    convert,
)

__all__ = [
    "__version__",
    # YAML nodes functionality
    "load_nodes_from_yaml",
    "load_all_nodes_from_directory",
    "create_node_class_from_yaml",
    "convert_node_class_to_yaml",
    "yaml_to_node_class",
    # API client functionality
    "PyroMindClient",
    "PyroMindAPIError",
    "SandboxesClient",
    "InstanceClient",
    "InferenceClient",
    "TrainingClient",
    "StorageClient",
    "PyroMindAPIClient",
    # xyFlow models
    "PositionDTO",
    "ViewportDTO",
    "XyflowNodeDataDTO",
    "XyflowNodeDTO",
    "XyflowEdgeDTO",
    "XyflowWorkflowDTO",
    # Workflow functionality
    "WorkflowLiteConverter",
    "LayoutGenerator",
    "to_workflow_lite",
    "to_workflow_standard",
    "XyflowWorkflowBuilder",
    "WorkflowFormat",
    "detect_format",
    "to_xyflow",
    "to_lite",
    "to_standard",
    "convert",
]

