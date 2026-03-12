"""
XyflowWorkflowBuilder - Fluent API for building xyFlow workflows

Provides a convenient way to construct workflows step by step with
automatic ID generation, layout, and validation.

V2 Builder (Recommended):
    ```python
    from pyromind_sdk.client.xyflow_models import (
        XyflowWorkflowBuilderV2,
        NodeDefinitionDTO,
    )
    
    # Create node definition
    node_def = NodeDefinitionDTO(
        name="LoadModel",
        display_name="Load Model",
        input={"required": {"model_path": ["STRING", {"default": ""}]}},
        output=["MODEL"],
        output_name=["model"]
    )
    
    # Build workflow
    builder = XyflowWorkflowBuilderV2("my-training-workflow")
    builder.add_node("load_model", node_def, {"model_path": "/models/llama"})
    builder.add_node("train", train_def, {"epochs": 100})
    builder.connect("load_model", "model", "train", "model")
    workflow = builder.build()
    ```

Legacy Builder (Deprecated):
    ```python
    builder = XyflowWorkflowBuilder("my-training-workflow")
    builder.add_node("load_model", "LoadModel", {"model_path": "/models/llama"})
    builder.connect("load_model", "model", "train", "model")
    workflow = builder.build()
    ```
"""
import uuid
import warnings
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, deque

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


# Layout configuration
DEFAULT_NODE_WIDTH = 150
DEFAULT_NODE_HEIGHT = 86
HORIZONTAL_SPACING = 300
VERTICAL_SPACING = 50
MARGIN = 50


# ============================================================================
# V2 Builder (Recommended)
# ============================================================================

class LayoutGeneratorV2:
    """
    Automatic node layout generator using topological sort (V2).
    
    Arranges nodes left-to-right based on dependency relationships.
    """
    
    def __init__(
        self,
        node_width: int = DEFAULT_NODE_WIDTH,
        node_height: int = DEFAULT_NODE_HEIGHT,
        horizontal_spacing: int = HORIZONTAL_SPACING,
        vertical_spacing: int = VERTICAL_SPACING,
        margin: int = MARGIN
    ):
        self.node_width = node_width
        self.node_height = node_height
        self.horizontal_spacing = horizontal_spacing
        self.vertical_spacing = vertical_spacing
        self.margin = margin
    
    def generate_layout(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, Tuple[float, float]]:
        """
        Generate node positions using topological sort.
        
        Args:
            nodes: List of node dictionaries with 'id' field
            edges: List of edge dictionaries with 'source' and 'target' fields
            
        Returns:
            Dictionary mapping node_id to (x, y) position tuple
        """
        if not nodes:
            return {}
        
        # Build dependency graph
        in_edges: Dict[str, Set[str]] = defaultdict(set)
        out_edges: Dict[str, Set[str]] = defaultdict(set)
        node_ids = {n.get('id') or n.get('name') for n in nodes}
        
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            if source and target and source in node_ids and target in node_ids:
                in_edges[target].add(source)
                out_edges[source].add(target)
        
        # Topological sort to get layer assignment
        layers = self._topological_sort_layers(node_ids, in_edges, out_edges)
        
        # Calculate positions
        positions = {}
        
        for layer_idx, layer_nodes in enumerate(layers):
            x = self.margin + layer_idx * (self.node_width + self.horizontal_spacing)
            start_y = self.margin
            
            for row_idx, node_id in enumerate(layer_nodes):
                y = start_y + row_idx * (self.node_height + self.vertical_spacing)
                positions[node_id] = (float(x), float(y))
        
        return positions
    
    def _topological_sort_layers(
        self,
        node_ids: Set[str],
        in_edges: Dict[str, Set[str]],
        out_edges: Dict[str, Set[str]]
    ) -> List[List[str]]:
        """Perform topological sort and group nodes into layers."""
        in_degree = {node: len(in_edges[node]) for node in node_ids}
        queue = deque([node for node in node_ids if in_degree[node] == 0])
        layers = []
        visited = set()
        
        while queue:
            current_layer = []
            current_layer_size = len(queue)
            
            for _ in range(current_layer_size):
                node = queue.popleft()
                if node in visited:
                    continue
                visited.add(node)
                current_layer.append(node)
                
                for dependent in out_edges[node]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0 and dependent not in visited:
                        queue.append(dependent)
            
            if current_layer:
                layers.append(current_layer)
        
        # Handle cycles - add remaining nodes
        unvisited = node_ids - visited
        if unvisited:
            layers.append(list(unvisited))
        
        return layers


class XyflowWorkflowBuilderV2:
    """
    Fluent builder for xyFlow workflows (V2 - Recommended).
    
    Provides convenient methods for:
    - Adding nodes with complete node definitions
    - Connecting nodes by name
    - Automatic layout generation
    - Validation before building
    
    Design Pattern: Builder
    
    The builder accumulates nodes and edges, then produces
    an immutable XyflowWorkflowDTOV2 on build().
    """
    
    def __init__(
        self, 
        name: Optional[str] = None, 
        auto_layout: bool = True,
        workflow_id: Optional[str] = None
    ):
        """
        Initialize builder.
        
        Args:
            name: Optional workflow name
            auto_layout: Whether to auto-generate node positions
            workflow_id: Optional workflow ID (UUID)
        """
        self._id = workflow_id or str(uuid.uuid4())
        self._name = name or "Unsaved Workflow"
        self._auto_layout = auto_layout
        self._nodes: Dict[str, Dict[str, Any]] = {}  # name -> node_data
        self._edges: List[Dict[str, Any]] = []
        self._node_id_counter = 0
        self._layout_generator = LayoutGeneratorV2() if auto_layout else None
    
    # ==================== Node Methods ====================
    
    def add_node(
        self,
        name: str,
        node_definition: NodeDefinitionDTO,
        config: Optional[Dict[str, Any]] = None,
        position: Optional[Tuple[float, float]] = None,
        label: Optional[str] = None,
        is_read_only: bool = True,
        properties: Optional[Dict[str, Any]] = None
    ) -> "XyflowWorkflowBuilderV2":
        """
        Add a node to the workflow with full node definition.
        
        Args:
            name: Unique name for the node (used for connections)
            node_definition: Complete node definition (NodeDefinitionDTO)
            config: Node configuration parameters
            position: Optional (x, y) position, auto-generated if None
            label: Optional display label (defaults to node_definition.display_name)
            is_read_only: Whether the node is read-only (default: True)
            properties: Optional node properties (e.g., {"dystatus": "Succeeded"})
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If node name already exists
        """
        if name in self._nodes:
            raise ValueError(f"Node '{name}' already exists")
        
        # Generate unique node ID with timestamp to match frontend format
        import time
        timestamp = int(time.time() * 1000)
        node_id = f"{node_definition.name}-{timestamp}"
        
        self._nodes[name] = {
            "id": node_id,
            "name": name,
            "node_definition": node_definition,
            "config": config or {},
            "position": position,
            "label": label or node_definition.display_name,
            "is_read_only": is_read_only,
            "properties": properties or {}
        }
        
        return self
    
    def add_node_simple(
        self,
        name: str,
        node_type: str,
        config: Optional[Dict[str, Any]] = None,
        position: Optional[Tuple[float, float]] = None,
        label: Optional[str] = None,
        node_definition_dict: Optional[Dict[str, Any]] = None
    ) -> "XyflowWorkflowBuilderV2":
        """
        Add a node with simplified parameters (convenience method).
        
        Args:
            name: Unique name for the node
            node_type: Type of the node (class_type)
            config: Node configuration parameters
            position: Optional (x, y) position
            label: Optional display label
            node_definition_dict: Optional node definition as dict
            
        Returns:
            Self for chaining
        """
        node_def = None
        if node_definition_dict:
            node_def = NodeDefinitionDTO.model_validate(node_definition_dict)
        else:
            # Create minimal node definition
            node_def = NodeDefinitionDTO(
                name=node_type,
                display_name=label or node_type,
                description="",
                input={}
            )
        
        return self.add_node(
            name=name,
            node_definition=node_def,
            config=config,
            position=position,
            label=label
        )
    
    def update_node(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> "XyflowWorkflowBuilderV2":
        """
        Update an existing node's configuration.
        
        Args:
            name: Node name to update
            config: New config to merge with existing
            label: New display label
            properties: New properties to merge
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If node doesn't exist
        """
        if name not in self._nodes:
            raise ValueError(f"Node '{name}' not found")
        
        if config:
            self._nodes[name]["config"].update(config)
        if label:
            self._nodes[name]["label"] = label
        if properties:
            self._nodes[name]["properties"].update(properties)
        
        return self
    
    def remove_node(self, name: str) -> "XyflowWorkflowBuilderV2":
        """
        Remove a node and its connected edges.
        
        Args:
            name: Node name to remove
            
        Returns:
            Self for chaining
        """
        if name in self._nodes:
            node_id = self._nodes[name]["id"]
            del self._nodes[name]
            # Remove connected edges
            self._edges = [
                e for e in self._edges 
                if e.get("source") != node_id and e.get("target") != node_id
            ]
        
        return self
    
    # ==================== Edge Methods ====================
    
    def add_edge(
        self,
        source: str,
        source_handle: Optional[str],
        target: str,
        target_handle: Optional[str],
        edge_type: str = "default",
        animated: bool = True,
        style: Optional[Dict[str, Any]] = None
    ) -> "XyflowWorkflowBuilderV2":
        """
        Add an edge between two nodes.
        
        Args:
            source: Source node name
            source_handle: Source output handle name
            target: Target node name
            target_handle: Target input handle name
            edge_type: Edge type (default, animated, etc.)
            animated: Whether the edge is animated (default: True)
            style: Optional edge style (e.g., {"stroke": "#6366f1", "strokeWidth": 2})
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If source or target node doesn't exist
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' not found")
        
        source_id = self._nodes[source]["id"]
        target_id = self._nodes[target]["id"]
        
        # Generate edge ID matching frontend format
        edge_id = f"xy-edge__{source_id}{source_handle or ''}-{target_id}{target_handle or ''}"
        
        self._edges.append({
            "id": edge_id,
            "source": source_id,
            "sourceHandle": source_handle,
            "target": target_id,
            "targetHandle": target_handle,
            "type": edge_type,
            "animated": animated,
            "style": style or {"stroke": "#6366f1", "strokeWidth": 2}
        })
        
        return self
    
    def connect(
        self,
        source: str,
        source_output: str,
        target: str,
        target_input: str,
        animated: bool = True
    ) -> "XyflowWorkflowBuilderV2":
        """
        Connect two nodes (convenience method).
        
        Args:
            source: Source node name
            source_output: Source output handle
            target: Target node name
            target_input: Target input handle
            animated: Whether the edge is animated
            
        Returns:
            Self for chaining
        """
        return self.add_edge(
            source, source_output, target, target_input,
            animated=animated
        )
    
    # ==================== Build Methods ====================
    
    def build(self, validate: bool = True) -> XyflowWorkflowDTOV2:
        """
        Build the final workflow.
        
        Args:
            validate: Whether to validate the workflow before returning
            
        Returns:
            XyflowWorkflowDTOV2 instance
            
        Raises:
            ValueError: If validation fails and validate=True
        """
        # Generate positions if auto_layout is enabled
        positions = {}
        if self._auto_layout and self._layout_generator:
            positions = self._layout_generator.generate_layout(
                [{"id": n["id"], "name": name} for name, n in self._nodes.items()],
                self._edges
            )
        
        # Build node DTOs
        node_dtos = []
        for name, node_data in self._nodes.items():
            node_id = node_data["id"]
            
            # Use provided position or generated position
            pos = node_data.get("position")
            if pos is None:
                pos = positions.get(node_id, (0.0, 0.0))
            
            # Calculate measured dimensions based on inputs
            node_def = node_data["node_definition"]
            input_count = len(node_def.get_all_params())
            # Estimate height based on number of inputs
            estimated_height = max(86, 28 + input_count * 28)
            
            node_dto = XyflowNodeDTOV2(
                id=node_id,
                type="default",
                position=PositionDTOV2(x=pos[0], y=pos[1]),
                data=XyflowNodeDataDTOV2(
                    label=node_data.get("label", name),
                    nodeType=node_def.name,
                    config=node_data["config"],
                    nodeDefinition=node_def,
                    isReadOnly=node_data.get("is_read_only", True)
                ),
                measured=MeasuredDTO(width=150, height=estimated_height),
                selected=False,
                dragging=False,
                properties=node_data.get("properties", {})
            )
            node_dtos.append(node_dto)
        
        # Build edge DTOs
        edge_dtos = []
        for edge_data in self._edges:
            style_dto = None
            if edge_data.get("style"):
                style_dto = EdgeStyleDTO.model_validate(edge_data["style"])
            
            edge_dto = XyflowEdgeDTOV2(
                id=edge_data["id"],
                source=edge_data["source"],
                target=edge_data["target"],
                sourceHandle=edge_data.get("sourceHandle"),
                targetHandle=edge_data.get("targetHandle"),
                type=edge_data.get("type", "default"),
                animated=edge_data.get("animated", False),
                style=style_dto
            )
            edge_dtos.append(edge_dto)
        
        # Create workflow
        workflow = XyflowWorkflowDTOV2(
            id=self._id,
            name=self._name,
            nodes=node_dtos,
            edges=edge_dtos,
            viewport=ViewportDTOV2()
        )
        
        # Validate if requested
        if validate:
            errors = workflow.validate_all()
            if errors:
                raise ValueError(f"Workflow validation failed: {errors}")
        
        return workflow
    
    # ==================== Import Methods ====================
    
    @classmethod
    def from_dict(cls, workflow_dict: Dict[str, Any]) -> "XyflowWorkflowBuilderV2":
        """
        Create builder from xyFlow V2 dictionary.
        
        Args:
            workflow_dict: xyFlow V2 format workflow dictionary
            
        Returns:
            XyflowWorkflowBuilderV2 instance
        """
        builder = cls(
            name=workflow_dict.get("name"),
            workflow_id=workflow_dict.get("id")
        )
        
        # Build name -> id mapping
        name_to_id = {}
        id_to_name = {}
        
        nodes = workflow_dict.get("nodes", [])
        for node_dict in nodes:
            node_id = str(node_dict.get("id", ""))
            data = node_dict.get("data", {})
            name = data.get("label", node_id)
            
            name_to_id[name] = node_id
            id_to_name[node_id] = name
            
            pos = node_dict.get("position", {})
            
            # Parse node definition
            node_def_dict = data.get("nodeDefinition", {})
            node_def = None
            if node_def_dict:
                node_def = NodeDefinitionDTO.model_validate(node_def_dict)
            else:
                # Create minimal definition
                node_def = NodeDefinitionDTO(
                    name=data.get("nodeType", ""),
                    display_name=data.get("label", ""),
                    description="",
                    input={}
                )
            
            builder.add_node(
                name=name,
                node_definition=node_def,
                config=data.get("config", {}),
                position=(pos.get("x", 0), pos.get("y", 0)) if pos else None,
                label=data.get("label"),
                is_read_only=data.get("isReadOnly", False),
                properties=node_dict.get("properties", {})
            )
        
        # Add edges
        edges = workflow_dict.get("edges", [])
        for edge_dict in edges:
            source_id = str(edge_dict.get("source", ""))
            target_id = str(edge_dict.get("target", ""))
            
            source_name = id_to_name.get(source_id)
            target_name = id_to_name.get(target_id)
            
            if source_name and target_name:
                builder.add_edge(
                    source=source_name,
                    source_handle=edge_dict.get("sourceHandle"),
                    target=target_name,
                    target_handle=edge_dict.get("targetHandle"),
                    edge_type=edge_dict.get("type", "default"),
                    animated=edge_dict.get("animated", False),
                    style=edge_dict.get("style")
                )
        
        return builder
    
    # ==================== Utility Methods ====================
    
    def get_node_names(self) -> List[str]:
        """Get list of all node names."""
        return list(self._nodes.keys())
    
    def get_node_id(self, name: str) -> Optional[str]:
        """Get node ID by name."""
        return self._nodes.get(name, {}).get("id")
    
    def get_node_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get node configuration by name."""
        return self._nodes.get(name, {}).get("config")
    
    def node_count(self) -> int:
        """Get total number of nodes."""
        return len(self._nodes)
    
    def edge_count(self) -> int:
        """Get total number of edges."""
        return len(self._edges)
    
    def clear(self) -> "XyflowWorkflowBuilderV2":
        """Clear all nodes and edges."""
        self._nodes.clear()
        self._edges.clear()
        self._node_id_counter = 0
        return self
    
    def copy(self) -> "XyflowWorkflowBuilderV2":
        """Create a copy of this builder."""
        new_builder = XyflowWorkflowBuilderV2(
            name=self._name,
            auto_layout=self._auto_layout,
            workflow_id=self._id
        )
        new_builder._nodes = {k: dict(v) for k, v in self._nodes.items()}
        new_builder._edges = [dict(e) for e in self._edges]
        new_builder._node_id_counter = self._node_id_counter
        return new_builder


# ============================================================================
# Legacy Builder (Deprecated)
# ============================================================================

class LayoutGenerator:
    """
    Automatic node layout generator using topological sort.
    
    .. deprecated:: 0.2.0
        Use LayoutGeneratorV2 instead.
    
    Arranges nodes left-to-right based on dependency relationships.
    """
    
    def __init__(
        self,
        node_width: int = DEFAULT_NODE_WIDTH,
        node_height: int = DEFAULT_NODE_HEIGHT,
        horizontal_spacing: int = HORIZONTAL_SPACING,
        vertical_spacing: int = VERTICAL_SPACING,
        margin: int = MARGIN
    ):
        self.node_width = node_width
        self.node_height = node_height
        self.horizontal_spacing = horizontal_spacing
        self.vertical_spacing = vertical_spacing
        self.margin = margin
    
    def generate_layout(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, Tuple[int, int]]:
        """
        Generate node positions using topological sort.
        
        Args:
            nodes: List of node dictionaries with 'id' field
            edges: List of edge dictionaries with 'source' and 'target' fields
            
        Returns:
            Dictionary mapping node_id to (x, y) position tuple
        """
        if not nodes:
            return {}
        
        # Build dependency graph
        in_edges: Dict[str, Set[str]] = defaultdict(set)
        out_edges: Dict[str, Set[str]] = defaultdict(set)
        node_ids = {n.get('id') or n.get('name') for n in nodes}
        
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            if source and target and source in node_ids and target in node_ids:
                in_edges[target].add(source)
                out_edges[source].add(target)
        
        # Topological sort to get layer assignment
        layers = self._topological_sort_layers(node_ids, in_edges, out_edges)
        
        # Calculate positions
        positions = {}
        
        for layer_idx, layer_nodes in enumerate(layers):
            x = self.margin + layer_idx * (self.node_width + self.horizontal_spacing)
            start_y = self.margin
            
            for row_idx, node_id in enumerate(layer_nodes):
                y = start_y + row_idx * (self.node_height + self.vertical_spacing)
                positions[node_id] = (int(x), int(y))
        
        return positions
    
    def _topological_sort_layers(
        self,
        node_ids: Set[str],
        in_edges: Dict[str, Set[str]],
        out_edges: Dict[str, Set[str]]
    ) -> List[List[str]]:
        """Perform topological sort and group nodes into layers."""
        in_degree = {node: len(in_edges[node]) for node in node_ids}
        queue = deque([node for node in node_ids if in_degree[node] == 0])
        layers = []
        visited = set()
        
        while queue:
            current_layer = []
            current_layer_size = len(queue)
            
            for _ in range(current_layer_size):
                node = queue.popleft()
                if node in visited:
                    continue
                visited.add(node)
                current_layer.append(node)
                
                for dependent in out_edges[node]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0 and dependent not in visited:
                        queue.append(dependent)
            
            if current_layer:
                layers.append(current_layer)
        
        # Handle cycles - add remaining nodes
        unvisited = node_ids - visited
        if unvisited:
            layers.append(list(unvisited))
        
        return layers


class XyflowWorkflowBuilder:
    """
    Fluent builder for xyFlow workflows (Legacy - Deprecated).
    
    .. deprecated:: 0.2.0
        Use XyflowWorkflowBuilderV2 instead for full nodeDefinition support.
    
    Provides convenient methods for:
    - Adding nodes with auto-generated IDs
    - Connecting nodes by name
    - Automatic layout generation
    - Validation before building
    
    Design Pattern: Builder
    
    The builder accumulates nodes and edges, then produces
    an immutable XyflowWorkflowDTO on build().
    """
    
    def __init__(self, name: Optional[str] = None, auto_layout: bool = True):
        """
        Initialize builder.
        
        Args:
            name: Optional workflow name
            auto_layout: Whether to auto-generate node positions
        """
        warnings.warn(
            "XyflowWorkflowBuilder is deprecated. Use XyflowWorkflowBuilderV2 instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._name = name
        self._auto_layout = auto_layout
        self._nodes: Dict[str, Dict[str, Any]] = {}  # name -> node_data
        self._edges: List[Dict[str, Any]] = []
        self._node_id_counter = 0
        self._layout_generator = LayoutGenerator() if auto_layout else None
    
    # ==================== Node Methods ====================
    
    def add_node(
        self,
        name: str,
        node_type: str,
        config: Optional[Dict[str, Any]] = None,
        position: Optional[Tuple[float, float]] = None,
        label: Optional[str] = None,
        node_definition: Optional[Dict[str, Any]] = None
    ) -> "XyflowWorkflowBuilder":
        """
        Add a node to the workflow.
        
        Args:
            name: Unique name for the node (used for connections)
            node_type: Type of the node (class_type)
            config: Node configuration parameters
            position: Optional (x, y) position, auto-generated if None
            label: Optional display label
            node_definition: Optional node definition from node_info
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If node name already exists
        """
        if name in self._nodes:
            raise ValueError(f"Node '{name}' already exists")
        
        self._node_id_counter += 1
        node_id = str(self._node_id_counter)
        
        self._nodes[name] = {
            "id": node_id,
            "name": name,
            "node_type": node_type,
            "config": config or {},
            "position": position,
            "label": label or name,
            "node_definition": node_definition
        }
        
        return self
    
    def update_node(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        label: Optional[str] = None
    ) -> "XyflowWorkflowBuilder":
        """
        Update an existing node's configuration.
        
        Args:
            name: Node name to update
            config: New config to merge with existing
            label: New display label
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If node doesn't exist
        """
        if name not in self._nodes:
            raise ValueError(f"Node '{name}' not found")
        
        if config:
            self._nodes[name]["config"].update(config)
        if label:
            self._nodes[name]["label"] = label
        
        return self
    
    def remove_node(self, name: str) -> "XyflowWorkflowBuilder":
        """
        Remove a node and its connected edges.
        
        Args:
            name: Node name to remove
            
        Returns:
            Self for chaining
        """
        if name in self._nodes:
            node_id = self._nodes[name]["id"]
            del self._nodes[name]
            # Remove connected edges
            self._edges = [
                e for e in self._edges 
                if e.get("source") != node_id and e.get("target") != node_id
            ]
        
        return self
    
    # ==================== Edge Methods ====================
    
    def add_edge(
        self,
        source: str,
        source_handle: Optional[str],
        target: str,
        target_handle: Optional[str],
        edge_type: str = "default"
    ) -> "XyflowWorkflowBuilder":
        """
        Add an edge between two nodes.
        
        Args:
            source: Source node name
            source_handle: Source output handle name
            target: Target node name
            target_handle: Target input handle name
            edge_type: Edge type (default, animated, etc.)
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If source or target node doesn't exist
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' not found")
        
        source_id = self._nodes[source]["id"]
        target_id = self._nodes[target]["id"]
        
        edge_id = f"edge-{source_id}-{target_id}-{len(self._edges)}"
        
        self._edges.append({
            "id": edge_id,
            "source": source_id,
            "sourceHandle": source_handle,
            "target": target_id,
            "targetHandle": target_handle,
            "type": edge_type
        })
        
        return self
    
    def connect(
        self,
        source: str,
        source_output: str,
        target: str,
        target_input: str
    ) -> "XyflowWorkflowBuilder":
        """
        Connect two nodes (convenience method).
        
        Args:
            source: Source node name
            source_output: Source output handle
            target: Target node name
            target_input: Target input handle
            
        Returns:
            Self for chaining
        """
        return self.add_edge(source, source_output, target, target_input)
    
    # ==================== Build Methods ====================
    
    def build(self, validate: bool = True) -> XyflowWorkflowDTO:
        """
        Build the final workflow.
        
        Args:
            validate: Whether to validate the workflow before returning
            
        Returns:
            XyflowWorkflowDTO instance
            
        Raises:
            ValueError: If validation fails and validate=True
        """
        # Generate positions if auto_layout is enabled
        positions = {}
        if self._auto_layout and self._layout_generator:
            positions = self._layout_generator.generate_layout(
                [{"id": n["id"], "name": name} for name, n in self._nodes.items()],
                self._edges
            )
        
        # Build node DTOs
        node_dtos = []
        for name, node_data in self._nodes.items():
            node_id = node_data["id"]
            
            # Use provided position or generated position
            pos = node_data.get("position")
            if pos is None:
                pos = positions.get(node_id, (0, 0))
            
            node_dto = XyflowNodeDTO(
                id=node_id,
                type="default",
                position=PositionDTO(x=pos[0], y=pos[1]),
                data=XyflowNodeDataDTO(
                    label=node_data.get("label", name),
                    nodeType=node_data["node_type"],
                    config=node_data["config"],
                    nodeDefinition=node_data.get("node_definition")
                )
            )
            node_dtos.append(node_dto)
        
        # Build edge DTOs
        edge_dtos = []
        for edge_data in self._edges:
            edge_dto = XyflowEdgeDTO(
                id=edge_data["id"],
                source=edge_data["source"],
                target=edge_data["target"],
                sourceHandle=edge_data.get("sourceHandle"),
                targetHandle=edge_data.get("targetHandle"),
                type=edge_data.get("type", "default")
            )
            edge_dtos.append(edge_dto)
        
        # Create workflow
        workflow = XyflowWorkflowDTO(
            name=self._name,
            nodes=node_dtos,
            edges=edge_dtos,
            viewport=ViewportDTO()
        )
        
        # Validate if requested
        if validate:
            errors = workflow.validate_all()
            if errors:
                raise ValueError(f"Workflow validation failed: {errors}")
        
        return workflow
    
    # ==================== Import Methods ====================
    
    @classmethod
    def from_lite(
        cls,
        lite_workflow: Dict[str, Any],
        node_info: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None
    ) -> "XyflowWorkflowBuilder":
        """
        Create builder from lite format workflow.
        
        Args:
            lite_workflow: Lite format workflow dictionary
            node_info: Optional node definitions for enrichment
            name: Optional workflow name
            
        Returns:
            XyflowWorkflowBuilder instance
        """
        builder = cls(name=name or lite_workflow.get("name"))
        
        nodes = lite_workflow.get("nodes", {})
        
        # Add nodes
        for node_name, node_data in nodes.items():
            node_type = node_data.get("type", "")
            config = {}
            
            # Separate config from connections
            inputs = node_data.get("inputs", {})
            for inp_name, inp_value in inputs.items():
                if not isinstance(inp_value, dict):
                    config[inp_name] = inp_value
            
            # Get node definition if available
            node_def = None
            if node_info and node_type in node_info:
                node_def = node_info[node_type]
            
            builder.add_node(
                name=node_name,
                node_type=node_type,
                config=config,
                label=node_data.get("label", node_name),
                node_definition=node_def
            )
        
        # Add edges
        for node_name, node_data in nodes.items():
            inputs = node_data.get("inputs", {})
            for inp_name, inp_value in inputs.items():
                if isinstance(inp_value, dict):
                    # It's a connection
                    source_id = inp_value.get("node_id")
                    output_name = inp_value.get("output_name")
                    
                    # Find source node name from ID
                    source_name = None
                    for n_name, n_data in nodes.items():
                        if n_data.get("index") == source_id:
                            source_name = n_name
                            break
                    
                    if source_name and output_name:
                        builder.connect(source_name, output_name, node_name, inp_name)
        
        return builder
    
    @classmethod
    def from_dict(
        cls,
        workflow_dict: Dict[str, Any]
    ) -> "XyflowWorkflowBuilder":
        """
        Create builder from xyFlow dictionary.
        
        Args:
            workflow_dict: xyFlow format workflow dictionary
            
        Returns:
            XyflowWorkflowBuilder instance
        """
        builder = cls(name=workflow_dict.get("name"))
        
        # Build name -> id mapping
        name_to_id = {}
        id_to_name = {}
        
        nodes = workflow_dict.get("nodes", [])
        for node_dict in nodes:
            node_id = str(node_dict.get("id", ""))
            data = node_dict.get("data", {})
            name = data.get("label", node_id)
            
            name_to_id[name] = node_id
            id_to_name[node_id] = name
            
            pos = node_dict.get("position", {})
            
            builder.add_node(
                name=name,
                node_type=data.get("nodeType", ""),
                config=data.get("config", {}),
                position=(pos.get("x", 0), pos.get("y", 0)) if pos else None,
                label=data.get("label"),
                node_definition=data.get("nodeDefinition")
            )
        
        # Add edges
        edges = workflow_dict.get("edges", [])
        for edge_dict in edges:
            source_id = str(edge_dict.get("source", ""))
            target_id = str(edge_dict.get("target", ""))
            
            source_name = id_to_name.get(source_id)
            target_name = id_to_name.get(target_id)
            
            if source_name and target_name:
                builder.add_edge(
                    source=source_name,
                    source_handle=edge_dict.get("sourceHandle"),
                    target=target_name,
                    target_handle=edge_dict.get("targetHandle"),
                    edge_type=edge_dict.get("type", "default")
                )
        
        return builder
    
    # ==================== Utility Methods ====================
    
    def get_node_names(self) -> List[str]:
        """Get list of all node names."""
        return list(self._nodes.keys())
    
    def get_node_id(self, name: str) -> Optional[str]:
        """Get node ID by name."""
        return self._nodes.get(name, {}).get("id")
    
    def get_node_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get node configuration by name."""
        return self._nodes.get(name, {}).get("config")
    
    def node_count(self) -> int:
        """Get total number of nodes."""
        return len(self._nodes)
    
    def edge_count(self) -> int:
        """Get total number of edges."""
        return len(self._edges)
    
    def clear(self) -> "XyflowWorkflowBuilder":
        """Clear all nodes and edges."""
        self._nodes.clear()
        self._edges.clear()
        self._node_id_counter = 0
        return self
    
    def copy(self) -> "XyflowWorkflowBuilder":
        """Create a copy of this builder."""
        new_builder = XyflowWorkflowBuilder(
            name=self._name,
            auto_layout=self._auto_layout
        )
        new_builder._nodes = {k: dict(v) for k, v in self._nodes.items()}
        new_builder._edges = [dict(e) for e in self._edges]
        new_builder._node_id_counter = self._node_id_counter
        return new_builder


class LayoutGenerator:
    """
    Automatic node layout generator using topological sort.
    
    Arranges nodes left-to-right based on dependency relationships.
    """
    
    def __init__(
        self,
        node_width: int = DEFAULT_NODE_WIDTH,
        node_height: int = DEFAULT_NODE_HEIGHT,
        horizontal_spacing: int = HORIZONTAL_SPACING,
        vertical_spacing: int = VERTICAL_SPACING,
        margin: int = MARGIN
    ):
        self.node_width = node_width
        self.node_height = node_height
        self.horizontal_spacing = horizontal_spacing
        self.vertical_spacing = vertical_spacing
        self.margin = margin
    
    def generate_layout(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, Tuple[int, int]]:
        """
        Generate node positions using topological sort.
        
        Args:
            nodes: List of node dictionaries with 'id' field
            edges: List of edge dictionaries with 'source' and 'target' fields
            
        Returns:
            Dictionary mapping node_id to (x, y) position tuple
        """
        if not nodes:
            return {}
        
        # Build dependency graph
        in_edges: Dict[str, Set[str]] = defaultdict(set)
        out_edges: Dict[str, Set[str]] = defaultdict(set)
        node_ids = {n.get('id') or n.get('name') for n in nodes}
        
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            if source and target and source in node_ids and target in node_ids:
                in_edges[target].add(source)
                out_edges[source].add(target)
        
        # Topological sort to get layer assignment
        layers = self._topological_sort_layers(node_ids, in_edges, out_edges)
        
        # Calculate positions
        positions = {}
        
        for layer_idx, layer_nodes in enumerate(layers):
            x = self.margin + layer_idx * (self.node_width + self.horizontal_spacing)
            start_y = self.margin
            
            for row_idx, node_id in enumerate(layer_nodes):
                y = start_y + row_idx * (self.node_height + self.vertical_spacing)
                positions[node_id] = (int(x), int(y))
        
        return positions
    
    def _topological_sort_layers(
        self,
        node_ids: Set[str],
        in_edges: Dict[str, Set[str]],
        out_edges: Dict[str, Set[str]]
    ) -> List[List[str]]:
        """Perform topological sort and group nodes into layers."""
        in_degree = {node: len(in_edges[node]) for node in node_ids}
        queue = deque([node for node in node_ids if in_degree[node] == 0])
        layers = []
        visited = set()
        
        while queue:
            current_layer = []
            current_layer_size = len(queue)
            
            for _ in range(current_layer_size):
                node = queue.popleft()
                if node in visited:
                    continue
                visited.add(node)
                current_layer.append(node)
                
                for dependent in out_edges[node]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0 and dependent not in visited:
                        queue.append(dependent)
            
            if current_layer:
                layers.append(current_layer)
        
        # Handle cycles - add remaining nodes
        unvisited = node_ids - visited
        if unvisited:
            layers.append(list(unvisited))
        
        return layers


class XyflowWorkflowBuilder:
    """
    Fluent builder for xyFlow workflows.
    
    Provides convenient methods for:
    - Adding nodes with auto-generated IDs
    - Connecting nodes by name
    - Automatic layout generation
    - Validation before building
    
    Design Pattern: Builder
    
    The builder accumulates nodes and edges, then produces
    an immutable XyflowWorkflowDTO on build().
    """
    
    def __init__(self, name: Optional[str] = None, auto_layout: bool = True):
        """
        Initialize builder.
        
        Args:
            name: Optional workflow name
            auto_layout: Whether to auto-generate node positions
        """
        self._name = name
        self._auto_layout = auto_layout
        self._nodes: Dict[str, Dict[str, Any]] = {}  # name -> node_data
        self._edges: List[Dict[str, Any]] = []
        self._node_id_counter = 0
        self._layout_generator = LayoutGenerator() if auto_layout else None
    
    # ==================== Node Methods ====================
    
    def add_node(
        self,
        name: str,
        node_type: str,
        config: Optional[Dict[str, Any]] = None,
        position: Optional[Tuple[float, float]] = None,
        label: Optional[str] = None,
        node_definition: Optional[Dict[str, Any]] = None
    ) -> "XyflowWorkflowBuilder":
        """
        Add a node to the workflow.
        
        Args:
            name: Unique name for the node (used for connections)
            node_type: Type of the node (class_type)
            config: Node configuration parameters
            position: Optional (x, y) position, auto-generated if None
            label: Optional display label
            node_definition: Optional node definition from node_info
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If node name already exists
        """
        if name in self._nodes:
            raise ValueError(f"Node '{name}' already exists")
        
        self._node_id_counter += 1
        node_id = str(self._node_id_counter)
        
        self._nodes[name] = {
            "id": node_id,
            "name": name,
            "node_type": node_type,
            "config": config or {},
            "position": position,
            "label": label or name,
            "node_definition": node_definition
        }
        
        return self
    
    def update_node(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        label: Optional[str] = None
    ) -> "XyflowWorkflowBuilder":
        """
        Update an existing node's configuration.
        
        Args:
            name: Node name to update
            config: New config to merge with existing
            label: New display label
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If node doesn't exist
        """
        if name not in self._nodes:
            raise ValueError(f"Node '{name}' not found")
        
        if config:
            self._nodes[name]["config"].update(config)
        if label:
            self._nodes[name]["label"] = label
        
        return self
    
    def remove_node(self, name: str) -> "XyflowWorkflowBuilder":
        """
        Remove a node and its connected edges.
        
        Args:
            name: Node name to remove
            
        Returns:
            Self for chaining
        """
        if name in self._nodes:
            node_id = self._nodes[name]["id"]
            del self._nodes[name]
            # Remove connected edges
            self._edges = [
                e for e in self._edges 
                if e.get("source") != node_id and e.get("target") != node_id
            ]
        
        return self
    
    # ==================== Edge Methods ====================
    
    def add_edge(
        self,
        source: str,
        source_handle: Optional[str],
        target: str,
        target_handle: Optional[str],
        edge_type: str = "default"
    ) -> "XyflowWorkflowBuilder":
        """
        Add an edge between two nodes.
        
        Args:
            source: Source node name
            source_handle: Source output handle name
            target: Target node name
            target_handle: Target input handle name
            edge_type: Edge type (default, animated, etc.)
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If source or target node doesn't exist
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' not found")
        
        source_id = self._nodes[source]["id"]
        target_id = self._nodes[target]["id"]
        
        edge_id = f"edge-{source_id}-{target_id}-{len(self._edges)}"
        
        self._edges.append({
            "id": edge_id,
            "source": source_id,
            "sourceHandle": source_handle,
            "target": target_id,
            "targetHandle": target_handle,
            "type": edge_type
        })
        
        return self
    
    def connect(
        self,
        source: str,
        source_output: str,
        target: str,
        target_input: str
    ) -> "XyflowWorkflowBuilder":
        """
        Connect two nodes (convenience method).
        
        Args:
            source: Source node name
            source_output: Source output handle
            target: Target node name
            target_input: Target input handle
            
        Returns:
            Self for chaining
        """
        return self.add_edge(source, source_output, target, target_input)
    
    # ==================== Build Methods ====================
    
    def build(self, validate: bool = True) -> XyflowWorkflowDTO:
        """
        Build the final workflow.
        
        Args:
            validate: Whether to validate the workflow before returning
            
        Returns:
            XyflowWorkflowDTO instance
            
        Raises:
            ValueError: If validation fails and validate=True
        """
        # Generate positions if auto_layout is enabled
        positions = {}
        if self._auto_layout and self._layout_generator:
            positions = self._layout_generator.generate_layout(
                [{"id": n["id"], "name": name} for name, n in self._nodes.items()],
                self._edges
            )
        
        # Build node DTOs
        node_dtos = []
        for name, node_data in self._nodes.items():
            node_id = node_data["id"]
            
            # Use provided position or generated position
            pos = node_data.get("position")
            if pos is None:
                pos = positions.get(node_id, (0, 0))
            
            node_dto = XyflowNodeDTO(
                id=node_id,
                type="default",
                position=PositionDTO(x=pos[0], y=pos[1]),
                data=XyflowNodeDataDTO(
                    label=node_data.get("label", name),
                    nodeType=node_data["node_type"],
                    config=node_data["config"],
                    nodeDefinition=node_data.get("node_definition")
                )
            )
            node_dtos.append(node_dto)
        
        # Build edge DTOs
        edge_dtos = []
        for edge_data in self._edges:
            edge_dto = XyflowEdgeDTO(
                id=edge_data["id"],
                source=edge_data["source"],
                target=edge_data["target"],
                sourceHandle=edge_data.get("sourceHandle"),
                targetHandle=edge_data.get("targetHandle"),
                type=edge_data.get("type", "default")
            )
            edge_dtos.append(edge_dto)
        
        # Create workflow
        workflow = XyflowWorkflowDTO(
            name=self._name,
            nodes=node_dtos,
            edges=edge_dtos,
            viewport=ViewportDTO()
        )
        
        # Validate if requested
        if validate:
            errors = workflow.validate_all()
            if errors:
                raise ValueError(f"Workflow validation failed: {errors}")
        
        return workflow
    
    # ==================== Import Methods ====================
    
    @classmethod
    def from_lite(
        cls,
        lite_workflow: Dict[str, Any],
        node_info: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None
    ) -> "XyflowWorkflowBuilder":
        """
        Create builder from lite format workflow.
        
        Args:
            lite_workflow: Lite format workflow dictionary
            node_info: Optional node definitions for enrichment
            name: Optional workflow name
            
        Returns:
            XyflowWorkflowBuilder instance
        """
        builder = cls(name=name or lite_workflow.get("name"))
        
        nodes = lite_workflow.get("nodes", {})
        
        # Add nodes
        for node_name, node_data in nodes.items():
            node_type = node_data.get("type", "")
            config = {}
            
            # Separate config from connections
            inputs = node_data.get("inputs", {})
            for inp_name, inp_value in inputs.items():
                if not isinstance(inp_value, dict):
                    config[inp_name] = inp_value
            
            # Get node definition if available
            node_def = None
            if node_info and node_type in node_info:
                node_def = node_info[node_type]
            
            builder.add_node(
                name=node_name,
                node_type=node_type,
                config=config,
                label=node_data.get("label", node_name),
                node_definition=node_def
            )
        
        # Add edges
        for node_name, node_data in nodes.items():
            inputs = node_data.get("inputs", {})
            for inp_name, inp_value in inputs.items():
                if isinstance(inp_value, dict):
                    # It's a connection
                    source_id = inp_value.get("node_id")
                    output_name = inp_value.get("output_name")
                    
                    # Find source node name from ID
                    source_name = None
                    for n_name, n_data in nodes.items():
                        if n_data.get("index") == source_id:
                            source_name = n_name
                            break
                    
                    if source_name and output_name:
                        builder.connect(source_name, output_name, node_name, inp_name)
        
        return builder
    
    @classmethod
    def from_dict(
        cls,
        workflow_dict: Dict[str, Any]
    ) -> "XyflowWorkflowBuilder":
        """
        Create builder from xyFlow dictionary.
        
        Args:
            workflow_dict: xyFlow format workflow dictionary
            
        Returns:
            XyflowWorkflowBuilder instance
        """
        builder = cls(name=workflow_dict.get("name"))
        
        # Build name -> id mapping
        name_to_id = {}
        id_to_name = {}
        
        nodes = workflow_dict.get("nodes", [])
        for node_dict in nodes:
            node_id = str(node_dict.get("id", ""))
            data = node_dict.get("data", {})
            name = data.get("label", node_id)
            
            name_to_id[name] = node_id
            id_to_name[node_id] = name
            
            pos = node_dict.get("position", {})
            
            builder.add_node(
                name=name,
                node_type=data.get("nodeType", ""),
                config=data.get("config", {}),
                position=(pos.get("x", 0), pos.get("y", 0)) if pos else None,
                label=data.get("label"),
                node_definition=data.get("nodeDefinition")
            )
        
        # Add edges
        edges = workflow_dict.get("edges", [])
        for edge_dict in edges:
            source_id = str(edge_dict.get("source", ""))
            target_id = str(edge_dict.get("target", ""))
            
            source_name = id_to_name.get(source_id)
            target_name = id_to_name.get(target_id)
            
            if source_name and target_name:
                builder.add_edge(
                    source=source_name,
                    source_handle=edge_dict.get("sourceHandle"),
                    target=target_name,
                    target_handle=edge_dict.get("targetHandle"),
                    edge_type=edge_dict.get("type", "default")
                )
        
        return builder
    
    # ==================== Utility Methods ====================
    
    def get_node_names(self) -> List[str]:
        """Get list of all node names."""
        return list(self._nodes.keys())
    
    def get_node_id(self, name: str) -> Optional[str]:
        """Get node ID by name."""
        return self._nodes.get(name, {}).get("id")
    
    def get_node_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get node configuration by name."""
        return self._nodes.get(name, {}).get("config")
    
    def node_count(self) -> int:
        """Get total number of nodes."""
        return len(self._nodes)
    
    def edge_count(self) -> int:
        """Get total number of edges."""
        return len(self._edges)
    
    def clear(self) -> "XyflowWorkflowBuilder":
        """Clear all nodes and edges."""
        self._nodes.clear()
        self._edges.clear()
        self._node_id_counter = 0
        return self
    
    def copy(self) -> "XyflowWorkflowBuilder":
        """Create a copy of this builder."""
        new_builder = XyflowWorkflowBuilder(
            name=self._name,
            auto_layout=self._auto_layout
        )
        new_builder._nodes = {k: dict(v) for k, v in self._nodes.items()}
        new_builder._edges = [dict(e) for e in self._edges]
        new_builder._node_id_counter = self._node_id_counter
        return new_builder
