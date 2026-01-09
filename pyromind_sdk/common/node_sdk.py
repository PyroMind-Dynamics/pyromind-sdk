"""Lightweight SDK stub for local development

This SDK is only used for local development and testing of third-party nodes
without the full platform codebase (without `app.models.nodes`).
In the real platform runtime environment, nodes should prioritize importing
base classes from `app.models.nodes`.
"""

from abc import ABC
from enum import Enum
from typing import Dict, Any, Tuple, Optional, List


class NodeType(Enum):
    """Node type enumeration (simplified version)"""

    PASSTHROUGH = "passthrough"
    POD_EXECUTION = "pod_execution"


class PodExecutionNode(ABC):
    """Simplified PodExecutionNode, only retains type information (merged with BaseNode functionality)"""

    CATEGORY: str = ""
    RETURN_TYPES: Tuple[str, ...] = ()
    RETURN_NAMES: Tuple[str, ...] = ()
    DISPLAY_NAME: Optional[str] = None
    DESCRIPTION: Optional[str] = None
    OUTPUT_NODE: bool = False
    NODE_TYPE: NodeType = NodeType.POD_EXECUTION
    COMMAND_TEMPLATE: List[str] = []
    ARGS_TEMPLATE: List[str] = []
    
    # CPU and memory resource configuration (subclasses can override this attribute)
    # CPU configuration: int format, e.g., 1 means 1 CPU core
    CPU_LIMIT: Optional[int] = None
    # Memory configuration: int format, e.g., 1 means 1GiB memory
    MEMORY_LIMIT: Optional[int] = None

    @classmethod
    def RESOURCE_TYPES(cls):
        return {}

    @classmethod
    def BASE_INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define the base input types for the node (excluding resource types)"""
        return {"required": {}, "optional": {}}

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Automatically merge RESOURCE_TYPES into the input type definition"""
        base_inputs = cls.BASE_INPUT_TYPES()
        if cls.RESOURCE_TYPES():
            base_inputs["required"] = {**base_inputs.get("required", {}), **cls.RESOURCE_TYPES()}
        return base_inputs

    @classmethod
    def CUSTOMER_INPUTS(cls) -> set:
        """
        Define which inputs are for customer use
        
        Subclasses can override this method to specify which input fields are
        user-defined (customer). These inputs are typically not used in
        ARGS_TEMPLATE or COMMAND_TEMPLATE, but are provided for user custom logic.
        
        Returns:
            set: A set containing customer input names
        """
        return set()


class PortPodExecutionNode(PodExecutionNode):
    """Simplified PortPodExecutionNode, provides port resource type"""

    @classmethod
    def RESOURCE_TYPES(cls):
        return {"port": ("INT", {"default": 3000, "min": 1, "max": 8000})}


class DaemonPodExecutionNode(PodExecutionNode):
    """Simplified DaemonPodExecutionNode"""

    pass


class GpuPodExecutionNode(PodExecutionNode):
    """Simplified GpuPodExecutionNode, provides gpu_count and gpu_product resource types"""

    GPU_MIN_COUNT = 1
    GPU_MAX_COUNT = 8

    @classmethod
    def RESOURCE_TYPES(cls):
        # Provide default GPU product options (consistent with the platform)
        # In the real environment, these values would be imported from app.core.base.GPU_PRODUCT_OPTIONS
        default_gpu_options = ["NVIDIA-H100-NVL", "NVIDIA-L40S"]
        resources = super().RESOURCE_TYPES()
        resources.update({
            "gpu_count": ("INT", {"default": cls.GPU_MIN_COUNT, "min": cls.GPU_MIN_COUNT, "max": cls.GPU_MAX_COUNT}),
            "gpu_product": (default_gpu_options, {"default": default_gpu_options[0]}),
        })
        return resources


class JupyterLabPodExecutionNode(PodExecutionNode):
    """Simplified JupyterLabPodExecutionNode, Pod execution node using JupyterLab image"""

    DESCRIPTION = "Execute a command in a Kubernetes Pod with JupyterLab environment"


class EndpointNode(PodExecutionNode):
    """Simplified EndpointNode, all nodes that return endpoints should inherit from this class"""

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("endpoint",)


# Prioritize using the real SDK provided by the platform; if import fails, use the simplified implementation in this file
try:
    from app.models.nodes.base_node import (
        PodExecutionNode as _PodExecutionNode,
        DaemonPodExecutionNode as _DaemonPodExecutionNode,
        GpuPodExecutionNode as _GpuPodExecutionNode,
        PortPodExecutionNode as _PortPodExecutionNode,
        JupyterLabPodExecutionNode as _JupyterLabPodExecutionNode,
        EndpointNode as _EndpointNode,
        NodeType as _NodeType,
    )

    PodExecutionNode = _PodExecutionNode
    DaemonPodExecutionNode = _DaemonPodExecutionNode
    GpuPodExecutionNode = _GpuPodExecutionNode
    PortPodExecutionNode = _PortPodExecutionNode
    JupyterLabPodExecutionNode = _JupyterLabPodExecutionNode
    EndpointNode = _EndpointNode
    NodeType = _NodeType
except ImportError:
    # In local standalone debugging environment (without app.models.nodes), continue using the simplified classes defined above
    pass

