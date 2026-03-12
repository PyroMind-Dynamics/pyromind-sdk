"""
Workflow Tools

This module provides tools for working with workflows:
- Converter: Convert between standard and lite workflow formats
- Validator: Validate workflows in both formats with comprehensive checks
- Builder: Build workflows using fluent API (V2 recommended)
- Format Converter: Convert between xyFlow V2, xyFlow, lite, and standard formats

V2 Models (Recommended):
    ```python
    from pyromind_sdk.client.workflow import (
        XyflowWorkflowBuilderV2,
        to_xyflow_v2,
        convert_v2,
    )
    from pyromind_sdk.client.xyflow_models import (
        XyflowWorkflowDTOV2,
        XyflowNodeDTOV2,
        XyflowEdgeDTOV2,
        NodeDefinitionDTO,
    )
    ```
"""

from .converter import (
    WorkflowLiteConverter,
    WorkflowMapper,
    TypeResolver,
    LinkBuilder,
    LayoutGenerator,
    to_workflow_lite,
    to_workflow_standard
)

from .validator import (
    ValidationError,
    SchemaValidationError,
    LinkValidationError,
    TypeValidationError,
    validate_workflow,
    validate_lite_format,
    validate_standard_format,
    validate_workflow_lite,
    validate_workflow_standard,
    validate_workflow_legacy,
)

# V2 Builder (Recommended)
from .builder import (
    XyflowWorkflowBuilderV2,
    LayoutGeneratorV2,
)

# Legacy Builder (Deprecated)
from .builder import (
    XyflowWorkflowBuilder,
    LayoutGenerator as NodeLayoutGenerator,
)

# Format Converter with V2 support
from .format_converter import (
    WorkflowFormat,
    detect_format,
    to_xyflow_v2,
    to_xyflow,
    to_lite,
    to_standard,
    convert,
    convert_v2,
)

# V2 Models (Recommended)
from ..xyflow_models import (
    XyflowWorkflowDTOV2,
    XyflowNodeDTOV2,
    XyflowEdgeDTOV2,
    XyflowNodeDataDTOV2,
    NodeDefinitionDTO,
    PositionDTOV2,
    ViewportDTOV2,
    MeasuredDTO,
    EdgeStyleDTO,
    InputDefinitionDTO,
)

# Legacy Models (Deprecated)
from ..xyflow_models import (
    XyflowWorkflowDTO,
    XyflowNodeDTO,
    XyflowEdgeDTO,
    XyflowNodeDataDTO,
    PositionDTO,
    ViewportDTO,
)

__all__ = [
    # Converter
    "WorkflowLiteConverter",
    "WorkflowMapper",
    "TypeResolver",
    "LinkBuilder",
    "LayoutGenerator",
    "to_workflow_lite",
    "to_workflow_standard",
    # Validator
    "ValidationError",
    "SchemaValidationError",
    "LinkValidationError",
    "TypeValidationError",
    "validate_workflow",
    "validate_lite_format",
    "validate_standard_format",
    "validate_workflow_lite",
    "validate_workflow_standard",
    "validate_workflow_legacy",
    # V2 Builder (Recommended)
    "XyflowWorkflowBuilderV2",
    "LayoutGeneratorV2",
    # Legacy Builder (Deprecated)
    "XyflowWorkflowBuilder",
    "NodeLayoutGenerator",
    # Format Converter
    "WorkflowFormat",
    "detect_format",
    "to_xyflow_v2",
    "to_xyflow",
    "to_lite",
    "to_standard",
    "convert",
    "convert_v2",
    # V2 Models (Recommended)
    "XyflowWorkflowDTOV2",
    "XyflowNodeDTOV2",
    "XyflowEdgeDTOV2",
    "XyflowNodeDataDTOV2",
    "NodeDefinitionDTO",
    "PositionDTOV2",
    "ViewportDTOV2",
    "MeasuredDTO",
    "EdgeStyleDTO",
    "InputDefinitionDTO",
    # Legacy Models (Deprecated)
    "XyflowWorkflowDTO",
    "XyflowNodeDTO",
    "XyflowEdgeDTO",
    "XyflowNodeDataDTO",
    "PositionDTO",
    "ViewportDTO",
]
