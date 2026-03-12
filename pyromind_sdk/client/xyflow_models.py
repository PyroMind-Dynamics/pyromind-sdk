"""
xyFlow (React Flow) Workflow Data Models

This module provides Pydantic models for xyFlow format workflows,
compatible with k8s_middleware backend.

Design:
- Aligns with k8s_middleware/app/models/workflow/xyflow_models.py
- Provides type-safe workflow construction
- Includes validation methods for security and correctness

V2 Models (Recommended):
- NodeDefinitionDTO: Complete node definition with input/output specifications
- XyflowNodeDataDTOV2: Enhanced node data with isReadOnly support
- XyflowNodeDTOV2: Complete node model with measured, properties
- XyflowEdgeDTOV2: Edge with animated and style support
- XyflowWorkflowDTOV2: Full workflow with timestamp

Legacy Models (Deprecated):
- XyflowNodeDataDTO, XyflowNodeDTO, XyflowEdgeDTO, XyflowWorkflowDTO
"""
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
import re
import uuid
import warnings


# Security configuration
SENSITIVE_FIELD_PATTERNS = frozenset([
    "password", "passwd", "pwd",
    "secret", "token", "api_key", "apikey",
    "credential", "private_key", "privatekey",
    "access_key", "secret_key",
])


# ============================================================================
# V2 Models (Recommended)
# ============================================================================

class InputParamSpecDTO(BaseModel):
    """
    Input parameter specification.
    
    Represents a single input parameter with its type and configuration.
    Format: [type_or_enum_list, config_dict]
    """
    # The first element can be a type string or a list of enum values
    type_or_enum: Union[str, List[str]] = Field(..., description="Type string or enum values list")
    config: Dict[str, Any] = Field(default_factory=dict, description="Parameter configuration")
    
    model_config = {"extra": "allow"}


class InputDefinitionDTO(BaseModel):
    """Input definition with required and optional parameters."""
    required: Dict[str, List[Any]] = Field(default_factory=dict, description="Required parameters")
    optional: Dict[str, List[Any]] = Field(default_factory=dict, description="Optional parameters")
    
    model_config = {"extra": "allow"}


class NodeDefinitionDTO(BaseModel):
    """
    Complete node definition.
    
    Contains all metadata about a node type including:
    - Input/output specifications
    - Display information
    - Execution metadata
    """
    input: InputDefinitionDTO = Field(default_factory=InputDefinitionDTO, description="Input parameters")
    output: List[str] = Field(default_factory=list, description="Output types")
    output_is_list: List[bool] = Field(default_factory=list, description="Whether each output is a list")
    output_name: List[str] = Field(default_factory=list, description="Output parameter names")
    name: str = Field(..., description="Node type name (e.g., 'CloneAndCacheModel')")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field("", description="Node description")
    python_module: str = Field("", description="Python module path")
    category: str = Field("", description="Node category for UI grouping")
    output_node: bool = Field(False, description="Whether this is an output node")
    experimental: bool = Field(False, description="Whether this node is experimental")
    deprecated: bool = Field(False, description="Whether this node is deprecated")
    
    model_config = {"extra": "allow"}
    
    @field_validator('input', mode='before')
    @classmethod
    def parse_input(cls, v: Any) -> InputDefinitionDTO:
        """Parse input from dict to InputDefinitionDTO."""
        if isinstance(v, InputDefinitionDTO):
            return v
        if isinstance(v, dict):
            return InputDefinitionDTO.model_validate(v)
        return InputDefinitionDTO()
    
    def get_required_params(self) -> List[str]:
        """Get list of required parameter names."""
        return list(self.input.required.keys())
    
    def get_optional_params(self) -> List[str]:
        """Get list of optional parameter names."""
        return list(self.input.optional.keys())
    
    def get_all_params(self) -> List[str]:
        """Get all parameter names in order (required first, then optional)."""
        return self.get_required_params() + self.get_optional_params()
    
    def get_param_type(self, param_name: str) -> Optional[str]:
        """Get the type of a parameter."""
        if param_name in self.input.required:
            param_def = self.input.required[param_name]
            if isinstance(param_def, list) and len(param_def) > 0:
                first = param_def[0]
                if isinstance(first, str):
                    return first
                elif isinstance(first, list):
                    return "COMBO"
        if param_name in self.input.optional:
            param_def = self.input.optional[param_name]
            if isinstance(param_def, list) and len(param_def) > 0:
                first = param_def[0]
                if isinstance(first, str):
                    return first
                elif isinstance(first, list):
                    return "COMBO"
        return None
    
    def get_param_default(self, param_name: str) -> Any:
        """Get the default value of a parameter."""
        for params in [self.input.required, self.input.optional]:
            if param_name in params:
                param_def = params[param_name]
                if isinstance(param_def, list) and len(param_def) > 1:
                    config = param_def[1]
                    if isinstance(config, dict):
                        return config.get("default")
        return None


class PositionDTOV2(BaseModel):
    """Node position model."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}


class ViewportDTOV2(BaseModel):
    """Viewport configuration model."""
    x: float = Field(0, description="Viewport X offset")
    y: float = Field(0, description="Viewport Y offset")
    zoom: float = Field(1, description="Zoom level")
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "zoom": self.zoom}


class MeasuredDTO(BaseModel):
    """Node dimensions."""
    width: float = Field(..., description="Node width")
    height: float = Field(..., description="Node height")
    
    model_config = {"extra": "allow"}


class EdgeStyleDTO(BaseModel):
    """Edge styling configuration."""
    stroke: str = Field("#6366f1", description="Stroke color")
    strokeWidth: int = Field(2, description="Stroke width")
    
    model_config = {"extra": "allow"}


class XyflowNodeDataDTOV2(BaseModel):
    """
    Enhanced node data model (V2).
    
    Contains the actual node configuration and metadata.
    """
    label: str = Field(..., description="Node display label")
    nodeType: str = Field(..., description="Node type (class_type)")
    nodeDefinition: Optional[NodeDefinitionDTO] = Field(
        None, 
        description="Complete node definition"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Node configuration parameters"
    )
    isReadOnly: bool = Field(False, description="Whether node is read-only")
    
    model_config = {"extra": "allow"}
    
    @field_validator('nodeDefinition', mode='before')
    @classmethod
    def parse_node_definition(cls, v: Any) -> Optional[NodeDefinitionDTO]:
        """Parse node definition from dict to NodeDefinitionDTO."""
        if v is None or isinstance(v, NodeDefinitionDTO):
            return v
        if isinstance(v, dict):
            return NodeDefinitionDTO.model_validate(v)
        return None
    
    @field_validator('config', mode='before')
    @classmethod
    def validate_config_security(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate config for sensitive fields."""
        if v is None:
            return {}
        
        for key in v.keys():
            key_lower = key.lower()
            for pattern in SENSITIVE_FIELD_PATTERNS:
                if pattern in key_lower:
                    warnings.warn(
                        f"Potentially sensitive field '{key}' in config. "
                        "Consider using environment variables or secrets.",
                        UserWarning
                    )
        return v


class XyflowNodeDTOV2(BaseModel):
    """
    Enhanced xyFlow node model (V2).
    
    Represents a single node in the workflow graph with all metadata.
    """
    id: str = Field(..., description="Unique node identifier")
    type: str = Field("default", description="Node visual type")
    position: PositionDTOV2 = Field(..., description="Node position")
    data: XyflowNodeDataDTOV2 = Field(..., description="Node data")
    measured: Optional[MeasuredDTO] = Field(None, description="Node dimensions")
    selected: bool = Field(False, description="Is node selected")
    dragging: bool = Field(False, description="Is node being dragged")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")
    
    model_config = {"extra": "allow"}
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v: Any) -> str:
        """Ensure id is string."""
        return str(v)
    
    @field_validator('position', mode='before')
    @classmethod
    def parse_position(cls, v: Any) -> PositionDTOV2:
        """Parse position from dict to PositionDTOV2."""
        if isinstance(v, PositionDTOV2):
            return v
        if isinstance(v, dict):
            return PositionDTOV2.model_validate(v)
        return PositionDTOV2(x=0, y=0)
    
    @field_validator('data', mode='before')
    @classmethod
    def parse_data(cls, v: Any) -> XyflowNodeDataDTOV2:
        """Parse data from dict to XyflowNodeDataDTOV2."""
        if isinstance(v, XyflowNodeDataDTOV2):
            return v
        if isinstance(v, dict):
            return XyflowNodeDataDTOV2.model_validate(v)
        raise ValueError("Invalid node data")
    
    @field_validator('measured', mode='before')
    @classmethod
    def parse_measured(cls, v: Any) -> Optional[MeasuredDTO]:
        """Parse measured from dict to MeasuredDTO."""
        if v is None or isinstance(v, MeasuredDTO):
            return v
        if isinstance(v, dict):
            return MeasuredDTO.model_validate(v)
        return None


class XyflowEdgeDTOV2(BaseModel):
    """
    Enhanced xyFlow edge model (V2).
    
    Represents a connection between two nodes with styling support.
    """
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    sourceHandle: Optional[str] = Field(None, description="Source node output handle")
    targetHandle: Optional[str] = Field(None, description="Target node input handle")
    type: str = Field("default", description="Edge visual type")
    animated: bool = Field(False, description="Is edge animated")
    style: Optional[EdgeStyleDTO] = Field(None, description="Edge styling")
    
    model_config = {"extra": "allow"}
    
    @field_validator('id', 'source', 'target', mode='before')
    @classmethod
    def validate_node_ref(cls, v: Any) -> str:
        """Ensure node references are strings."""
        return str(v)
    
    @field_validator('style', mode='before')
    @classmethod
    def parse_style(cls, v: Any) -> Optional[EdgeStyleDTO]:
        """Parse style from dict to EdgeStyleDTO."""
        if v is None or isinstance(v, EdgeStyleDTO):
            return v
        if isinstance(v, dict):
            return EdgeStyleDTO.model_validate(v)
        return None


class XyflowWorkflowDTOV2(BaseModel):
    """
    Complete xyFlow workflow model (V2).
    
    Represents a complete workflow with nodes, edges, and all metadata.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Workflow ID (UUID)")
    name: str = Field("Unsaved Workflow", description="Workflow name")
    nodes: List[XyflowNodeDTOV2] = Field(default_factory=list, description="List of nodes")
    edges: List[XyflowEdgeDTOV2] = Field(default_factory=list, description="List of edges")
    viewport: ViewportDTOV2 = Field(default_factory=ViewportDTOV2, description="Viewport configuration")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        description="Workflow timestamp (ISO format)"
    )
    
    model_config = {"extra": "allow"}
    
    @field_validator('id', mode='before')
    @classmethod
    def generate_id_if_missing(cls, v: Optional[str]) -> str:
        """Generate UUID if id is missing."""
        if v is None:
            return str(uuid.uuid4())
        return str(v)
    
    @field_validator('nodes', mode='before')
    @classmethod
    def validate_nodes(cls, v: Any) -> List:
        """Validate nodes is a list."""
        if not isinstance(v, list):
            raise ValueError('nodes must be a list')
        return v
    
    @field_validator('edges', mode='before')
    @classmethod
    def validate_edges(cls, v: Any) -> List:
        """Validate edges is a list."""
        if not isinstance(v, list):
            raise ValueError('edges must be a list')
        return v
    
    @field_validator('viewport', mode='before')
    @classmethod
    def parse_viewport(cls, v: Any) -> ViewportDTOV2:
        """Parse viewport from dict to ViewportDTOV2."""
        if isinstance(v, ViewportDTOV2):
            return v
        if isinstance(v, dict):
            return ViewportDTOV2.model_validate(v)
        return ViewportDTOV2()
    
    # ==================== Instance Methods ====================
    
    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return self.model_dump(exclude_none=exclude_none)
    
    def validate_connections(self) -> List[str]:
        """Validate edge connections."""
        errors = []
        node_ids = {node.id for node in self.nodes}
        
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge {edge.id}: source node '{edge.source}' does not exist")
            if edge.target not in node_ids:
                errors.append(f"Edge {edge.id}: target node '{edge.target}' does not exist")
            if edge.source == edge.target:
                errors.append(f"Edge {edge.id}: self-loop detected")
        
        return errors
    
    def validate_dag(self) -> List[str]:
        """Validate workflow is a DAG (no cycles)."""
        errors = []
        adj: Dict[str, List[str]] = {node.id: [] for node in self.nodes}
        
        for edge in self.edges:
            if edge.source in adj:
                adj[edge.source].append(edge.target)
        
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node.id: WHITE for node in self.nodes}
        
        def dfs(node_id: str, path: List[str]) -> bool:
            color[node_id] = GRAY
            for neighbor in adj.get(node_id, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    cycle_path = path + [neighbor]
                    errors.append(f"Cycle detected: {' -> '.join(cycle_path)}")
                    return True
                if color[neighbor] == WHITE:
                    if dfs(neighbor, path + [neighbor]):
                        return True
            color[node_id] = BLACK
            return False
        
        for node_id in color:
            if color[node_id] == WHITE:
                dfs(node_id, [node_id])
        
        return errors
    
    def validate_all(self) -> List[str]:
        """Run all validations."""
        errors = []
        errors.extend(self.validate_connections())
        errors.extend(self.validate_dag())
        return errors
    
    # ==================== Query Methods ====================
    
    def get_node_by_id(self, node_id: str) -> Optional[XyflowNodeDTOV2]:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_edges_by_source(self, node_id: str) -> List[XyflowEdgeDTOV2]:
        """Get all edges starting from a node."""
        return [edge for edge in self.edges if edge.source == node_id]
    
    def get_edges_by_target(self, node_id: str) -> List[XyflowEdgeDTOV2]:
        """Get all edges ending at a node."""
        return [edge for edge in self.edges if edge.target == node_id]
    
    def get_incoming_edges(self, node_id: str) -> List[XyflowEdgeDTOV2]:
        """Alias for get_edges_by_target."""
        return self.get_edges_by_target(node_id)
    
    def get_outgoing_edges(self, node_id: str) -> List[XyflowEdgeDTOV2]:
        """Alias for get_edges_by_source."""
        return self.get_edges_by_source(node_id)
    
    # ==================== Modification Methods ====================
    
    def add_node(self, node: XyflowNodeDTOV2) -> "XyflowWorkflowDTOV2":
        """Add a node to the workflow."""
        self.nodes.append(node)
        return self
    
    def add_edge(self, edge: XyflowEdgeDTOV2) -> "XyflowWorkflowDTOV2":
        """Add an edge to the workflow."""
        self.edges.append(edge)
        return self
    
    def remove_node(self, node_id: str) -> "XyflowWorkflowDTOV2":
        """Remove a node and its connected edges."""
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]
        return self
    
    # ==================== Class Methods ====================
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "XyflowWorkflowDTOV2":
        """Create instance from dictionary."""
        return cls.model_validate(data)
    
    @classmethod
    def create_empty(cls, name: str = "Unsaved Workflow") -> "XyflowWorkflowDTOV2":
        """Create an empty workflow."""
        return cls(name=name, nodes=[], edges=[], viewport=ViewportDTOV2())


# ============================================================================
# Legacy Models (Deprecated - kept for backward compatibility)
# ============================================================================

class PositionDTO(BaseModel):
    """Node position model (Legacy)."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}


class ViewportDTO(BaseModel):
    """Viewport configuration model (Legacy)."""
    x: float = Field(0, description="Viewport X offset")
    y: float = Field(0, description="Viewport Y offset")
    zoom: float = Field(1, description="Zoom level")
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "zoom": self.zoom}


class PositionDTO(BaseModel):
    """Node position model"""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {"x": self.x, "y": self.y}


class ViewportDTO(BaseModel):
    """Viewport configuration model"""
    x: float = Field(0, description="Viewport X offset")
    y: float = Field(0, description="Viewport Y offset")
    zoom: float = Field(1, description="Zoom level")
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {"x": self.x, "y": self.y, "zoom": self.zoom}


class XyflowNodeDataDTO(BaseModel):
    """
    Node data model (Legacy - Deprecated).
    
    .. deprecated:: 0.2.0
        Use XyflowNodeDataDTOV2 instead for full nodeDefinition support.
    
    Contains the actual node configuration and metadata.
    """
    label: Optional[str] = Field(None, description="Node display label")
    nodeType: Optional[str] = Field(None, description="Node type (class_type)")
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Node configuration parameters"
    )
    nodeDefinition: Optional[Dict[str, Any]] = Field(
        None, 
        description="Node definition from node_info"
    )
    
    model_config = {"extra": "allow"}
    
    def __init__(self, **data):
        warnings.warn(
            "XyflowNodeDataDTO is deprecated. Use XyflowNodeDataDTOV2 instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(**data)
    
    @field_validator('config', mode='before')
    @classmethod
    def validate_config_security(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate config for sensitive fields."""
        if v is None:
            return {}
        
        for key in v.keys():
            key_lower = key.lower()
            for pattern in SENSITIVE_FIELD_PATTERNS:
                if pattern in key_lower:
                    warnings.warn(
                        f"Potentially sensitive field '{key}' in config. "
                        "Consider using environment variables or secrets.",
                        UserWarning
                    )
        return v
    
    def to_v2(self) -> XyflowNodeDataDTOV2:
        """Convert to V2 model."""
        node_def = None
        if self.nodeDefinition:
            if isinstance(self.nodeDefinition, NodeDefinitionDTO):
                node_def = self.nodeDefinition
            else:
                node_def = NodeDefinitionDTO.model_validate(self.nodeDefinition)
        
        return XyflowNodeDataDTOV2(
            label=self.label or "",
            nodeType=self.nodeType or "",
            nodeDefinition=node_def,
            config=self.config or {},
            isReadOnly=False
        )


class XyflowNodeDTO(BaseModel):
    """
    xyFlow node model (Legacy - Deprecated).
    
    .. deprecated:: 0.2.0
        Use XyflowNodeDTOV2 instead for full measured and properties support.
    
    Represents a single node in the workflow graph.
    """
    id: str = Field(..., description="Unique node identifier")
    type: str = Field("default", description="Node type (default, input, output, etc.)")
    position: PositionDTO = Field(..., description="Node position")
    data: XyflowNodeDataDTO = Field(..., description="Node data")
    measured: Optional[Dict[str, float]] = Field(
        None, 
        description="Node dimensions (width, height)"
    )
    selected: Optional[bool] = Field(False, description="Is node selected")
    dragging: Optional[bool] = Field(False, description="Is node being dragged")
    
    model_config = {"extra": "allow"}
    
    def __init__(self, **data):
        warnings.warn(
            "XyflowNodeDTO is deprecated. Use XyflowNodeDTOV2 instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(**data)
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v: Any) -> str:
        """Ensure id is string."""
        return str(v)
    
    def to_v2(self) -> XyflowNodeDTOV2:
        """Convert to V2 model."""
        measured_dto = None
        if self.measured:
            measured_dto = MeasuredDTO.model_validate(self.measured)
        
        return XyflowNodeDTOV2(
            id=self.id,
            type=self.type,
            position=PositionDTOV2(x=self.position.x, y=self.position.y),
            data=self.data.to_v2(),
            measured=measured_dto,
            selected=self.selected or False,
            dragging=self.dragging or False,
            properties={}
        )


class XyflowEdgeDTO(BaseModel):
    """
    xyFlow edge model (Legacy - Deprecated).
    
    .. deprecated:: 0.2.0
        Use XyflowEdgeDTOV2 instead for full style support.
    
    Represents a connection between two nodes.
    """
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    sourceHandle: Optional[str] = Field(
        None, 
        description="Source node output handle"
    )
    targetHandle: Optional[str] = Field(
        None, 
        description="Target node input handle"
    )
    type: Optional[str] = Field("default", description="Edge type")
    animated: Optional[bool] = Field(False, description="Is edge animated")
    style: Optional[Dict[str, Any]] = Field(None, description="Edge style")
    
    model_config = {"extra": "allow"}
    
    def __init__(self, **data):
        warnings.warn(
            "XyflowEdgeDTO is deprecated. Use XyflowEdgeDTOV2 instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(**data)
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v: Any) -> str:
        """Ensure id is string."""
        return str(v)
    
    @field_validator('source', 'target', mode='before')
    @classmethod
    def validate_node_ref(cls, v: Any) -> str:
        """Ensure node references are strings."""
        return str(v)
    
    def to_v2(self) -> XyflowEdgeDTOV2:
        """Convert to V2 model."""
        style_dto = None
        if self.style:
            style_dto = EdgeStyleDTO.model_validate(self.style)
        
        return XyflowEdgeDTOV2(
            id=self.id,
            source=self.source,
            target=self.target,
            sourceHandle=self.sourceHandle,
            targetHandle=self.targetHandle,
            type=self.type or "default",
            animated=self.animated or False,
            style=style_dto
        )


class XyflowWorkflowDTO(BaseModel):
    """
    Complete xyFlow workflow model (Legacy - Deprecated).
    
    .. deprecated:: 0.2.0
        Use XyflowWorkflowDTOV2 instead for full timestamp support.
    
    Represents a complete workflow with nodes, edges, and metadata.
    """
    id: Optional[str] = Field(None, description="Workflow ID")
    name: Optional[str] = Field(None, description="Workflow name")
    nodes: List[XyflowNodeDTO] = Field(
        default_factory=list, 
        description="List of nodes"
    )
    edges: List[XyflowEdgeDTO] = Field(
        default_factory=list, 
        description="List of edges"
    )
    viewport: Optional[ViewportDTO] = Field(None, description="Viewport configuration")
    
    model_config = {"extra": "allow"}
    
    def __init__(self, **data):
        warnings.warn(
            "XyflowWorkflowDTO is deprecated. Use XyflowWorkflowDTOV2 instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(**data)
    
    @field_validator('id', mode='before')
    @classmethod
    def generate_id_if_missing(cls, v: Optional[str]) -> str:
        """Generate UUID if id is missing."""
        if v is None:
            return str(uuid.uuid4())
        return str(v)
    
    @field_validator('nodes', mode='before')
    @classmethod
    def validate_nodes(cls, v: Any) -> List:
        """Validate nodes is a list."""
        if not isinstance(v, list):
            raise ValueError('nodes must be a list')
        return v
    
    @field_validator('edges', mode='before')
    @classmethod
    def validate_edges(cls, v: Any) -> List:
        """Validate edges is a list."""
        if not isinstance(v, list):
            raise ValueError('edges must be a list')
        return v
    
    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return self.model_dump(exclude_none=exclude_none)
    
    def validate_connections(self) -> List[str]:
        """Validate edge connections."""
        errors = []
        node_ids = {node.id for node in self.nodes}
        
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge {edge.id}: source node '{edge.source}' does not exist")
            if edge.target not in node_ids:
                errors.append(f"Edge {edge.id}: target node '{edge.target}' does not exist")
            if edge.source == edge.target:
                errors.append(f"Edge {edge.id}: self-loop detected")
        
        return errors
    
    def validate_dag(self) -> List[str]:
        """Validate workflow is a DAG (no cycles)."""
        errors = []
        adj: Dict[str, List[str]] = {node.id: [] for node in self.nodes}
        
        for edge in self.edges:
            if edge.source in adj:
                adj[edge.source].append(edge.target)
        
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node.id: WHITE for node in self.nodes}
        
        def dfs(node_id: str, path: List[str]) -> bool:
            color[node_id] = GRAY
            for neighbor in adj.get(node_id, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    cycle_path = path + [neighbor]
                    errors.append(f"Cycle detected: {' -> '.join(cycle_path)}")
                    return True
                if color[neighbor] == WHITE:
                    if dfs(neighbor, path + [neighbor]):
                        return True
            color[node_id] = BLACK
            return False
        
        for node_id in color:
            if color[node_id] == WHITE:
                dfs(node_id, [node_id])
        
        return errors
    
    def validate_all(self) -> List[str]:
        """Run all validations."""
        errors = []
        errors.extend(self.validate_connections())
        errors.extend(self.validate_dag())
        return errors
    
    def get_node_by_id(self, node_id: str) -> Optional[XyflowNodeDTO]:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_edges_by_source(self, node_id: str) -> List[XyflowEdgeDTO]:
        """Get all edges starting from a node."""
        return [edge for edge in self.edges if edge.source == node_id]
    
    def get_edges_by_target(self, node_id: str) -> List[XyflowEdgeDTO]:
        """Get all edges ending at a node."""
        return [edge for edge in self.edges if edge.target == node_id]
    
    def get_incoming_edges(self, node_id: str) -> List[XyflowEdgeDTO]:
        """Alias for get_edges_by_target."""
        return self.get_edges_by_target(node_id)
    
    def get_outgoing_edges(self, node_id: str) -> List[XyflowEdgeDTO]:
        """Alias for get_edges_by_source."""
        return self.get_edges_by_source(node_id)
    
    def add_node(self, node: XyflowNodeDTO) -> "XyflowWorkflowDTO":
        """Add a node to the workflow."""
        self.nodes.append(node)
        return self
    
    def add_edge(self, edge: XyflowEdgeDTO) -> "XyflowWorkflowDTO":
        """Add an edge to the workflow."""
        self.edges.append(edge)
        return self
    
    def remove_node(self, node_id: str) -> "XyflowWorkflowDTO":
        """Remove a node and its connected edges."""
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]
        return self
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "XyflowWorkflowDTO":
        """Create instance from dictionary."""
        return cls.model_validate(data)
    
    @classmethod
    def create_empty(cls, name: Optional[str] = None) -> "XyflowWorkflowDTO":
        """Create an empty workflow."""
        return cls(
            name=name,
            nodes=[],
            edges=[],
            viewport=ViewportDTO()
        )
    
    def to_v2(self) -> XyflowWorkflowDTOV2:
        """Convert to V2 model."""
        return XyflowWorkflowDTOV2(
            id=self.id or str(uuid.uuid4()),
            name=self.name or "Unsaved Workflow",
            nodes=[node.to_v2() for node in self.nodes],
            edges=[edge.to_v2() for edge in self.edges],
            viewport=ViewportDTOV2(
                x=self.viewport.x if self.viewport else 0,
                y=self.viewport.y if self.viewport else 0,
                zoom=self.viewport.zoom if self.viewport else 1
            )
        )
