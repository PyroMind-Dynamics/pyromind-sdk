"""
Universal Workflow Format Converter

This module provides a generic, node-agnostic conversion between the standard
workflow format and workflow_lite format. It doesn't require hardcoded logic for
specific node types, making it work with any node definitions.

Standard Workflow Format:
  - Complex structure with UI metadata (pos, size, flags, order, mode)
  - Links as arrays: [link_id, source_node, source_socket, target_node, target_socket, type]
  - Inputs/outputs with verbose metadata
  - Hard to read and edit manually

Workflow Lite Format:
  - Simplified structure focusing on execution logic
  - Named nodes instead of numeric IDs
  - Readable connection definitions
  - Easy for humans and AI to understand

Architecture:
  - WorkflowMapper: Handles node ID and name mapping
  - TypeResolver: Resolves input/output types from node_info
  - LinkBuilder: Builds and validates links
  - WorkflowLiteConverter: Main orchestrator using helper classes
"""

import re
import uuid
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, deque


class WorkflowMapper:
    """
    Handles mapping between node IDs and names.

    Manages bidirectional mapping between numeric node IDs and readable names,
    including handling of duplicate names with counter suffixes.
    """

    def __init__(self):
        self.node_id_to_name: Dict[int, str] = {}
        self.node_name_to_id: Dict[str, int] = {}
        self.name_counters: Dict[str, int] = {}

    def build_from_nodes(self, nodes: List[Dict]) -> None:
        """
        Build mappings from a list of nodes.

        Args:
            nodes: List of node dictionaries from workflow
        """
        self.node_id_to_name = {}
        self.name_counters = {}

        for node in nodes:
            node_id = node.get("id")
            node_type = node.get("type", "")
            base_name = self._generate_node_name(node_type)

            # Handle duplicate names
            if base_name not in self.name_counters:
                self.name_counters[base_name] = 0
                unique_name = base_name
            else:
                self.name_counters[base_name] += 1
                unique_name = f"{base_name}_{self.name_counters[base_name]}"

            self.node_id_to_name[node_id] = unique_name

        # Build reverse mapping
        self.node_name_to_id = {v: k for k, v in self.node_id_to_name.items()}

    def build_from_lite_nodes(self, lite_nodes: Dict[str, Dict]) -> None:
        """
        Build mappings from lite format nodes.

        Args:
            lite_nodes: Dictionary of {node_name: node_data} from lite format

        Note:
            If lite nodes don't have "index" field, assigns sequential IDs starting from 1.
            This allows manual creation of lite workflows without needing to specify indices.
        """
        self.node_name_to_id = {}
        next_id = 1

        for node_name, node_data in lite_nodes.items():
            # Use existing index if available, otherwise assign sequential ID
            # Note: index can be 0, so we check for "index" in node_data and it's not None
            if "index" in node_data and node_data["index"] is not None:
                node_id = node_data["index"]
            else:
                node_id = next_id
                next_id += 1

            self.node_name_to_id[node_name] = node_id

        # Build reverse mapping (handle potential duplicate IDs by using first occurrence)
        self.node_id_to_name = {}
        for node_name, node_id in self.node_name_to_id.items():
            if node_id not in self.node_id_to_name:
                self.node_id_to_name[node_id] = node_name

    def get_name(self, node_id: int, fallback: str = None) -> Optional[str]:
        """Get node name from ID."""
        return self.node_id_to_name.get(node_id, fallback)

    def get_id(self, node_name: str) -> Optional[int]:
        """Get node ID from name."""
        return self.node_name_to_id.get(node_name)

    @staticmethod
    def _generate_node_name(node_type: str) -> str:
        """
        Generate a readable node name from type.

        Converts CamelCase to snake_case and removes 'node' suffix.
        Handles consecutive capitals (LLM -> llm, not l_l_m).

        Args:
            node_type: Node type string (e.g., "TestLLMNode")

        Returns:
            Readable node name (e.g., "test_llm")
        """
        # Insert underscore before capital letters
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', node_type)
        # Handle consecutive capitals
        name = re.sub('([a-z0-9])([A-Z]+)', r'\1_\2', name)
        name = name.lower()

        # Remove 'node' suffix if present
        if name.endswith('_node'):
            name = name[:-5]

        # Fallback for very short names
        if len(name) < 3:
            name = f"node_{node_type.lower()}"

        return name


class TypeResolver:
    """
    Resolves input/output types from node_info.

    Caches type information for efficient repeated lookups.
    """

    def __init__(self, node_info: Optional[Dict[str, Any]] = None):
        """
        Initialize the type resolver.

        Args:
            node_info: Node information dictionary from get_node_info API
        """
        self.node_info = node_info or {}
        self._input_type_cache: Dict[Tuple[str, str], str] = {}
        self._output_type_cache: Dict[Tuple[str, int], str] = {}
        self._param_order_cache: Dict[str, List[str]] = {}

    def set_node_info(self, node_info: Dict[str, Any]) -> None:
        """Update node information."""
        self.node_info = node_info
        self._input_type_cache.clear()
        self._output_type_cache.clear()
        self._param_order_cache.clear()

    def get_input_type(self, node_type: str, param_name: str) -> str:
        """
        Get the type of an input parameter.

        Args:
            node_type: Type of the node
            param_name: Name of the input parameter

        Returns:
            Type string (e.g., "STRING", "INT", "MODEL")
        """
        cache_key = (node_type, param_name)
        if cache_key in self._input_type_cache:
            return self._input_type_cache[cache_key]

        # Look up in node_info
        if node_type in self.node_info:
            input_defs = self.node_info[node_type].get("input", {})

            # Check both required and optional
            for category in ["required", "optional"]:
                if category in input_defs:
                    category_params = input_defs[category]
                    if isinstance(category_params, dict) and param_name in category_params:
                        param_def = category_params[param_name]
                        if isinstance(param_def, list) and len(param_def) > 0:
                            first_elem = param_def[0]
                            if isinstance(first_elem, str):
                                self._input_type_cache[cache_key] = first_elem
                                return first_elem
                            elif isinstance(first_elem, list):
                                # Enum type
                                self._input_type_cache[cache_key] = "STRING"
                                return "STRING"

        # Default fallback
        self._input_type_cache[cache_key] = "AUTO"
        return "AUTO"

    def get_output_type(self, node_type: str, output_idx: int, output_name: str = None) -> str:
        """
        Get the type of an output.

        Args:
            node_type: Type of the node
            output_idx: Index of the output
            output_name: Optional name of the output for more accurate lookup

        Returns:
            Type string
        """
        cache_key = (node_type, output_idx)
        if cache_key in self._output_type_cache:
            return self._output_type_cache[cache_key]

        if node_type in self.node_info:
            node_data = self.node_info[node_type]
            output_types = node_data.get("output", [])
            output_names = node_data.get("output_name", [])

            # Try to match by name first
            if output_name and output_names and output_name in output_names:
                name_idx = output_names.index(output_name)
                if name_idx < len(output_types):
                    self._output_type_cache[cache_key] = output_types[name_idx]
                    return output_types[name_idx]

            # Fall back to index
            if output_idx < len(output_types):
                self._output_type_cache[cache_key] = output_types[output_idx]
                return output_types[output_idx]

        self._output_type_cache[cache_key] = "AUTO"
        return "AUTO"

    def get_parameter_order(self, node_type: str) -> List[str]:
        """
        Get the order of parameters for a node type.

        Returns parameters in required first, then optional order.

        Args:
            node_type: Type of the node

        Returns:
            List of parameter names in order
        """
        if node_type in self._param_order_cache:
            return self._param_order_cache[node_type]

        param_order = []

        if node_type in self.node_info:
            input_defs = self.node_info[node_type].get("input", {})
            for category in ["required", "optional"]:
                if category in input_defs:
                    category_params = input_defs[category]
                    if isinstance(category_params, dict):
                        param_order.extend(category_params.keys())

        self._param_order_cache[node_type] = param_order
        return param_order

    def is_env_type(self, node_type: str, param_name: str) -> bool:
        """
        Check if a parameter is ENV type.

        Args:
            node_type: Type of the node
            param_name: Name of the parameter

        Returns:
            True if parameter is ENV type
        """
        param_type = self.get_input_type(node_type, param_name)
        return param_type == "ENV"

    def get_default_value(self, node_type: str, param_name: str) -> Any:
        """
        Get default value for a parameter from node_info.

        Args:
            node_type: Type of the node
            param_name: Name of the parameter

        Returns:
            Default value or None
        """
        if node_type in self.node_info:
            input_defs = self.node_info[node_type].get("input", {})
            for category in ["required", "optional"]:
                if category in input_defs:
                    category_params = input_defs[category]
                    if isinstance(category_params, dict) and param_name in category_params:
                        param_def = category_params[param_name]
                        if isinstance(param_def, list) and len(param_def) > 1:
                            default_info = param_def[1] if isinstance(param_def[1], dict) else {}
                            return default_info.get("default")
        return None


class LinkBuilder:
    """
    Builds and manages workflow links.

    Handles conversion between connection format and link arrays.
    """

    def __init__(self, type_resolver: TypeResolver):
        """
        Initialize the link builder.

        Args:
            type_resolver: TypeResolver instance for determining link types
        """
        self.type_resolver = type_resolver
        self._next_link_id = 1

    def reset_link_id(self) -> None:
        """Reset link ID counter."""
        self._next_link_id = 1

    def build_socket_mappings(self, nodes: List[Dict]) -> Tuple[Dict[int, Dict[str, Dict]], Dict[int, Dict[str, Dict]]]:
        """
        Build socket name mappings for all nodes.

        Args:
            nodes: List of node dictionaries

        Returns:
            Tuple of (input_mappings, output_mappings)
            Each mapping: {node_id: {idx: name}}
        """
        input_mappings = {}
        output_mappings = {}

        for node in nodes:
            node_id = node.get("id")

            # Map inputs
            input_map = {}
            for idx, inp in enumerate(node.get("inputs", [])):
                if inp.get("name"):
                    input_map[idx] = inp.get("name")
            input_mappings[node_id] = input_map

            # Map outputs
            output_map = {}
            for idx, out in enumerate(node.get("outputs", [])):
                if out.get("name"):
                    output_map[idx] = out.get("name")
            output_mappings[node_id] = output_map

        return input_mappings, output_mappings

    def build_input_connections(
        self,
        links: List[List],
        node_mapper: WorkflowMapper,
        input_mappings: Dict[int, Dict[str, Dict]],
        output_mappings: Dict[int, Dict[str, Dict]]
    ) -> Dict[int, Dict[str, Dict]]:
        """
        Build input connections mapping from links.

        Args:
            links: List of link arrays
            node_mapper: WorkflowMapper instance
            input_mappings: Input socket name mappings
            output_mappings: Output socket name mappings

        Returns:
            Dict mapping {node_id: {input_name: {node_id, output_name}}}
        """
        input_connections = {}

        for link in links:
            if len(link) >= 6:
                link_id, source_id, source_idx, target_id, target_idx, link_type = link[:6]

                # Get socket names
                source_sockets = output_mappings.get(source_id, {})
                target_sockets = input_mappings.get(target_id, {})

                output_name = source_sockets.get(source_idx, f"output_{source_idx}")
                input_name = target_sockets.get(target_idx, f"input_{target_idx}")

                if target_id not in input_connections:
                    input_connections[target_id] = {}

                input_connections[target_id][input_name] = {
                    "node_id": source_id,
                    "output_name": output_name
                }

        return input_connections

    def convert_lite_to_links(
        self,
        lite_nodes: Dict[str, Dict],
        node_mapper: WorkflowMapper
    ) -> List[List]:
        """
        Convert lite format connections to standard links array.

        Args:
            lite_nodes: Lite format nodes dictionary
            node_mapper: WorkflowMapper for ID resolution

        Returns:
            List of link arrays
        """
        self.reset_link_id()
        links = []

        # Build output name to index mapping
        node_outputs = {}
        for node_name, node_data in lite_nodes.items():
            node_id = node_mapper.get_id(node_name)
            if node_id is None:
                continue

            outputs = node_data.get("outputs", [])
            output_map = {name: idx for idx, name in enumerate(outputs)}
            node_outputs[node_id] = output_map

        node_id_to_name = {v: k for k, v in node_mapper.node_name_to_id.items()}

        # Process connections
        for node_name, node_data in lite_nodes.items():
            target_id = node_mapper.get_id(node_name)
            if target_id is None:
                continue

            inputs = node_data.get("inputs", {})

            for input_name, input_value in inputs.items():
                if isinstance(input_value, dict):
                    # Support two connection formats:
                    # 1. {"node_id": 123, "output_name": "model"} - numeric ID (from standard conversion)
                    # 2. {"node": "node_name", "output": "output"} - node name (AI-friendly)

                    source_id = None
                    output_name = None

                    # Format 1: Numeric node_id (from standard conversion)
                    if "node_id" in input_value:
                        source_id = input_value.get("node_id")
                        output_name = input_value.get("output_name")
                    # Format 2: Node name (AI-friendly, for manual creation)
                    elif "node" in input_value:
                        source_node_name = input_value.get("node")
                        output_name = input_value.get("output")
                        # Look up node_id from node_name
                        source_id = node_mapper.get_id(source_node_name)

                    if source_id is None or output_name is None:
                        continue

                    # Get output index
                    output_idx = 0
                    if source_id in node_outputs:
                        output_map = node_outputs[source_id]
                        output_idx = output_map.get(output_name, 0)

                    # Calculate input index
                    # Get param_order from type_resolver for accurate index calculation
                    node_type = node_data.get("type", "")
                    param_order = self.type_resolver.get_parameter_order(node_type) if node_type else None
                    input_idx = self._calculate_input_index(node_data, input_name, node_type, param_order)

                    # Determine link type
                    link_type = self._determine_link_type(
                        source_id, output_name, output_idx,
                        node_id_to_name, lite_nodes
                    )

                    # Create link
                    links.append([0, source_id, output_idx, target_id, input_idx, link_type])

        # Sort and assign link IDs
        links.sort(key=lambda x: (x[3], x[1]))  # Sort by target_id, then source_id
        for i, link in enumerate(links):
            link[0] = i + 1

        return links

    def _calculate_input_index(
        self,
        node_data: Dict,
        target_input_name: str,
        node_type: str = None,
        param_order: List[str] = None
    ) -> int:
        """
        Calculate the input index for a given input name.

        In standard format, inputs array contains inputs in node_info order.
        Only includes: connections and inputs with widgets (including optional inputs).

        Args:
            node_data: Node data from lite format
            target_input_name: Name of the input to find index for
            node_type: Node type (for type checking)
            param_order: Parameter order from node_info (for correct ordering)

        Returns:
            Input index in the standard format inputs array
        """
        lite_inputs = node_data.get("inputs", {})
        if node_type is None:
            node_type = node_data.get("type", "")
        
        # If we have param_order, use it to determine the correct index
        # This matches the order used in _build_standard_inputs
        # IMPORTANT: Only connected inputs (with links) are in inputs_array
        # Unconnected inputs (direct values) are NOT in inputs_array, only in widgets_values
        if param_order and target_input_name in param_order:
            target_param_idx = param_order.index(target_input_name)
            input_idx = 0
            
            # Count inputs that come before this one in param_order
            # Only count those that will actually be in inputs_array
            # Logic matches _build_standard_inputs:
            # - Only connected inputs (have link) are in inputs_array
            # - Unconnected inputs (direct values) are NOT in inputs_array
            for i in range(target_param_idx):
                param_name = param_order[i]
                
                # Check if this parameter should be in inputs_array
                # Only connected inputs are in inputs_array
                should_be_in_inputs = False
                
                if param_name in lite_inputs:
                    input_value = lite_inputs[param_name]
                    # Only if it's a connection (has node_id), it's in inputs_array
                    if isinstance(input_value, dict) and "node_id" in input_value:
                        should_be_in_inputs = True
                
                if should_be_in_inputs:
                    input_idx += 1
            
            return input_idx
        
        # Fallback: old logic (for nodes without node_info)
        # Count only connections
        input_idx = 0
        for inp_name in lite_inputs.keys():
            if inp_name == target_input_name:
                break
            inp_value = lite_inputs[inp_name]
            # Count if it's a connection
            if isinstance(inp_value, dict) and "node_id" in inp_value:
                input_idx += 1

        return input_idx

    def _determine_link_type(
        self,
        source_id: int,
        output_name: str,
        output_idx: int,
        node_id_to_name: Dict[int, str],
        lite_nodes: Dict[str, Dict]
    ) -> str:
        """
        Determine the type of a link based on source node output.

        Args:
            source_id: Source node ID
            output_name: Output name
            output_idx: Output index
            node_id_to_name: Mapping from node ID to name
            lite_nodes: Lite format nodes

        Returns:
            Link type string
        """
        source_node_name = node_id_to_name.get(source_id)
        if source_node_name:
            source_node_data = lite_nodes.get(source_node_name, {})
            source_node_type = source_node_data.get("type")
            if source_node_type:
                return self.type_resolver.get_output_type(source_node_type, output_idx, output_name)

        return "AUTO"


class LayoutGenerator:
    """
    Automatic node layout generator for workflow visualization.

    Generates node positions using topological sorting with a 16:9 aspect ratio layout.
    Nodes are arranged left-to-right based on their dependency relationships.
    """

    # Default layout configuration
    DEFAULT_NODE_WIDTH = 270
    DEFAULT_NODE_HEIGHT = 82
    HORIZONTAL_SPACING = 50   # Minimum space between columns (just enough to avoid overlap)
    VERTICAL_SPACING = 50     # Minimum space between rows (just enough to avoid overlap)
    MARGIN = 50               # Margin around the layout

    def __init__(
        self,
        node_width: int = DEFAULT_NODE_WIDTH,
        node_height: int = DEFAULT_NODE_HEIGHT,
        horizontal_spacing: int = HORIZONTAL_SPACING,
        vertical_spacing: int = VERTICAL_SPACING,
        margin: int = MARGIN
    ):
        """
        Initialize the layout generator.

        Args:
            node_width: Width of each node in pixels
            node_height: Height of each node in pixels
            horizontal_spacing: Horizontal spacing between node columns
            vertical_spacing: Vertical spacing between node rows
            margin: Margin around the entire layout
        """
        self.node_width = node_width
        self.node_height = node_height
        self.horizontal_spacing = horizontal_spacing
        self.vertical_spacing = vertical_spacing
        self.margin = margin

    def generate_layout(
        self,
        lite_nodes: Dict[str, Dict]
    ) -> Dict[str, Tuple[int, int]]:
        """
        Generate node positions using topological sort.

        Args:
            lite_nodes: Dictionary of {node_name: node_data} in lite format

        Returns:
            Dictionary mapping node_name to (x, y) position tuple
        """
        if not lite_nodes:
            return {}

        # Step 1: Build dependency graph
        in_edges = defaultdict(set)  # node -> set of nodes it depends on
        out_edges = defaultdict(set)  # node -> set of nodes that depend on it

        for node_name, node_data in lite_nodes.items():
            inputs = node_data.get("inputs", {})
            for input_value in inputs.values():
                if isinstance(input_value, dict) and "node_id" in input_value:
                    # Find source node name from node_id
                    source_id = input_value["node_id"]
                    source_name = self._find_node_name_by_id(lite_nodes, source_id)
                    if source_name:
                        in_edges[node_name].add(source_name)
                        out_edges[source_name].add(node_name)

        # Step 2: Topological sort to get layer assignment
        layers = self._topological_sort_layers(lite_nodes.keys(), in_edges, out_edges)

        # Step 3: Calculate positions for each layer
        positions = {}
        
        # Special case: if all nodes are in one layer (no dependencies), distribute them horizontally
        if len(layers) == 1 and len(layers[0]) > 1:
            # All nodes are independent - arrange horizontally
            for col_idx, node_name in enumerate(layers[0]):
                x = self.margin + col_idx * (self.node_width + self.horizontal_spacing)
                y = self.margin
                positions[node_name] = (x, y)
        else:
            # Normal case: nodes have dependencies - arrange by layers (columns)
            for layer_idx, layer_nodes in enumerate(layers):
                # Calculate x position for this layer (column)
                x = self.margin + layer_idx * (self.node_width + self.horizontal_spacing)
                
                # Calculate y positions for nodes in this layer
                # If multiple nodes in same layer, arrange them vertically
                start_y = self.margin
                
                for row_idx, node_name in enumerate(layer_nodes):
                    y = start_y + row_idx * (self.node_height + self.vertical_spacing)
                    positions[node_name] = (x, y)

        return positions

    def _topological_sort_layers(
        self,
        node_names: Set[str],
        in_edges: Dict[str, Set[str]],
        out_edges: Dict[str, Set[str]]
    ) -> List[List[str]]:
        """
        Perform topological sort and group nodes into layers.

        Args:
            node_names: Set of all node names
            in_edges: Incoming edge dependencies
            out_edges: Outgoing edge dependencies

        Returns:
            List of layers, where each layer is a list of node names at that level
        """
        # Calculate in-degrees
        in_degree = {node: len(in_edges[node]) for node in node_names}

        # Start with nodes that have no dependencies
        queue = deque([node for node in node_names if in_degree[node] == 0])
        layers = []
        visited = set()

        while queue:
            # Process all nodes at current level
            current_layer = []
            current_layer_size = len(queue)

            for _ in range(current_layer_size):
                node = queue.popleft()
                if node in visited:
                    continue
                visited.add(node)
                current_layer.append(node)

                # Reduce in-degree for dependent nodes
                for dependent in out_edges[node]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0 and dependent not in visited:
                        queue.append(dependent)

            if current_layer:
                layers.append(current_layer)

        # Handle cycles - remaining unvisited nodes
        unvisited = node_names - visited
        if unvisited:
            # Add remaining nodes to the last layer
            layers.append(list(unvisited))

        return layers

    @staticmethod
    def _find_node_name_by_id(lite_nodes: Dict[str, Dict], node_id: int) -> Optional[str]:
        """
        Find node name by its ID in lite format.

        Args:
            lite_nodes: Dictionary of {node_name: node_data}
            node_id: Node ID to search for

        Returns:
            Node name if found, None otherwise
        """
        for node_name, node_data in lite_nodes.items():
            if node_data.get("index") == node_id:
                return node_name
        return None


class WorkflowLiteConverter:
    """
    Universal converter between standard workflow and workflow_lite formats.

    Uses helper classes for better separation of concerns and maintainability.
    """

    def __init__(self, node_info: Optional[Dict[str, Any]] = None, auto_layout: bool = True):
        """
        Initialize the converter.

        Args:
            node_info: Optional node information dictionary from get_node_info API.
                      If provided, parameter names will be accurately mapped.
                      If None, uses generic heuristic-based extraction.
            auto_layout: If True, automatically generate node positions using topological sort.
                        If False, use default positions [0, 0] for all nodes.
        """
        self.type_resolver = TypeResolver(node_info)
        self.link_builder = LinkBuilder(self.type_resolver)
        self.node_mapper = WorkflowMapper()
        self.layout_generator = LayoutGenerator() if auto_layout else None
        self._next_node_id = 1
        self._next_link_id = 1

    def set_node_info(self, node_info: Dict[str, Any]) -> None:
        """
        Update node information for parameter mapping.

        Args:
            node_info: Node information dictionary from get_node_info API
        """
        self.type_resolver.set_node_info(node_info)

    @property
    def _node_info(self) -> Dict[str, Any]:
        """
        Backward compatibility property for accessing node_info.

        Deprecated: Use type_resolver.node_info directly.
        """
        return self.type_resolver.node_info

    def to_lite(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert standard workflow format to workflow_lite format.

        Args:
            workflow: Standard workflow dictionary

        Returns:
            Workflow lite dictionary
        """
        # Build mappings
        self.node_mapper.build_from_nodes(workflow.get("nodes", []))
        input_mappings, output_mappings = self.link_builder.build_socket_mappings(workflow.get("nodes", []))

        # Build input connections
        input_connections = self.link_builder.build_input_connections(
            workflow.get("links", []),
            self.node_mapper,
            input_mappings,
            output_mappings
        )

        # Convert nodes
        lite_nodes = {}
        for node in workflow.get("nodes", []):
            node_id = node.get("id")
            node_name = self.node_mapper.get_name(node_id)
            if node_name:
                lite_nodes[node_name] = self._convert_node_to_lite(
                    node,
                    input_connections.get(node_id, {})
                )

        return {
            "version": "1.0",
            "nodes": lite_nodes
        }

    def to_standard(self, lite: Dict[str, Any], original_workflow: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Convert workflow_lite format to standard workflow format.

        Args:
            lite: Workflow lite dictionary
            original_workflow: Optional original workflow to preserve metadata

        Returns:
            Standard workflow dictionary
        """
        # Build mappings
        self.node_mapper.build_from_lite_nodes(lite.get("nodes", {}))

        # Generate automatic layout if enabled
        node_positions = {}
        if self.layout_generator:
            node_positions = self.layout_generator.generate_layout(lite.get("nodes", {}))

        # Convert nodes
        nodes = []
        max_node_id = 0
        for node_name, node_data in lite.get("nodes", {}).items():
            node_id = self.node_mapper.get_id(node_name)
            if node_id is None:
                node_id = max_node_id + 1
            max_node_id = max(max_node_id, node_id)

            # Get position for this node
            pos = node_positions.get(node_name, [0, 0])
            nodes.append(self._convert_node_to_standard(node_name, node_data, node_id, pos))

        # Convert connections to links
        links = self.link_builder.convert_lite_to_links(lite.get("nodes", {}), self.node_mapper)

        # Update nodes with link references
        # Pass lite nodes to help determine which inputs should have links
        self._update_nodes_with_links(nodes, links, lite.get("nodes", {}))

        # Generate workflow ID (UUID format)
        workflow_id = self._generate_workflow_id(original_workflow, lite)

        # Calculate last_node_id and last_link_id
        # last_node_id should be the maximum node ID, not the node count
        last_node_id = 0
        if nodes:
            last_node_id = max(node.get("id", 0) for node in nodes)
        
        # last_link_id should be the maximum link ID, not the link count
        last_link_id = 0
        if links:
            # Link format: [link_id, source_id, source_idx, target_id, target_idx, link_type]
            link_ids = [link[0] for link in links if len(link) > 0 and isinstance(link[0], (int, float))]
            if link_ids:
                last_link_id = max(link_ids)

        # Create standard workflow
        standard = {
            "id": workflow_id,
            "revision": 0,
            "last_node_id": last_node_id,
            "last_link_id": last_link_id,
            "nodes": nodes,
            "links": links,
            "groups": [],
            "config": {},
            "extra": {
                "ds": {
                    "scale": 1.0,
                    "offset": [0, 0]
                }
            },
            "version": 0.4
        }

        # Preserve original metadata if provided
        if original_workflow:
            if "extra" in original_workflow:
                standard["extra"].update(original_workflow["extra"])

        return standard

    def _convert_node_to_lite(self, node: Dict, input_connections: Dict) -> Dict:
        """
        Convert a single node to lite format.

        Args:
            node: Node dictionary from standard format
            input_connections: Input connections for this node

        Returns:
            Lite format node dictionary
        """
        node_type = node.get("type", "")
        inputs = node.get("inputs", [])
        outputs = node.get("outputs", [])

        # Build inputs dict
        lite_inputs = {}
        for inp in inputs:
            input_name = inp.get("name", "")
            input_type = inp.get("type", "")

            if input_name:
                if input_name in input_connections:
                    lite_inputs[input_name] = input_connections[input_name]
                elif inp.get("widget"):
                    # Widget values handled separately
                    pass
                else:
                    lite_inputs[input_name] = None

        # Extract parameters from widgets_values
        parameters = self._extract_parameters_with_names(node, node_type, inputs, input_connections)

        # Merge parameters for non-connected inputs
        for param_name, param_value in parameters.items():
            if param_name not in lite_inputs:
                lite_inputs[param_name] = param_value

        # Build outputs as list of names
        lite_outputs = [out.get("name", "") for out in outputs if out.get("name")]

        return {
            "type": node_type,
            "inputs": lite_inputs,
            "outputs": lite_outputs,
            "index": node.get("id", 0)
        }

    def _extract_parameters_with_names(
        self,
        node: Dict,
        node_type: str,
        inputs: List[Dict],
        input_connections: Dict
    ) -> Dict[str, Any]:
        """
        Extract parameters from widgets_values and map to actual input names.

        Args:
            node: Node dictionary
            node_type: Type of the node
            inputs: List of input definitions
            input_connections: Mapping of connected inputs

        Returns:
            Dictionary mapping parameter names to values
        """
        widgets_values = node.get("widgets_values", [])
        if not widgets_values:
            return {}

        # Use node_info if available
        if node_type in self.type_resolver.node_info:
            return self._extract_using_node_info(
                node_type,
                widgets_values,
                input_connections
            )

        # Fallback: map widget values to input names
        parameter_inputs = [
            inp.get("name") for inp in inputs
            if inp.get("widget") and inp.get("name") and inp.get("name") not in input_connections
        ]

        parameters = {}
        for i, value in enumerate(widgets_values):
            if i < len(parameter_inputs):
                parameters[parameter_inputs[i]] = value
            else:
                # Use generic param_0, param_1, etc. for values without named inputs
                parameters[f"param_{i}"] = value

        # Special case: if no parameter inputs were found but widgets_values exist,
        # preserve all widget values with generic names
        if not parameter_inputs and widgets_values:
            for i, value in enumerate(widgets_values):
                parameters[f"param_{i}"] = value

        return parameters

    def _extract_using_node_info(
        self,
        node_type: str,
        widgets_values: List[Any],
        input_connections: Dict
    ) -> Dict[str, Any]:
        """
        Extract parameters using node_info for accurate mapping.

        Args:
            node_type: Type of the node
            widgets_values: Widget values list
            input_connections: Connected inputs mapping

        Returns:
            Dictionary mapping parameter names to values
        """
        parameters = {}

        # Get node definition
        if node_type not in self.type_resolver.node_info:
            return {}

        node_def = self.type_resolver.node_info[node_type]
        input_defs = node_def.get("input", {})
        required_params = input_defs.get("required", {})
        optional_params = input_defs.get("optional", {})

        # Helper function to check if a type is widget-able
        def is_widgetable_type(param_type: str) -> bool:
            """Check if parameter type is widget-able (primitive type)."""
            widgetable_types = {"STRING", "INT", "FLOAT", "BOOLEAN", "COMBO", "ENV"}
            return param_type in widgetable_types

        # Helper function to get parameter type
        def get_param_type(param_def: Any) -> str:
            """Get parameter type from node_info definition."""
            if isinstance(param_def, list) and len(param_def) > 0:
                first_elem = param_def[0]
                if isinstance(first_elem, str):
                    return first_elem
                elif isinstance(first_elem, list):
                    return "COMBO"
            return "STRING"

        # widgets_values is in to_standard order:
        # 1. required + widget-able (STRING, INT, etc.)
        # 2. required + non-widget (MODEL, VAE, etc.)
        # 3. optional + widget-able (only those with connections)
        # 4. optional + non-widget (only those with connections)
        # Note: optional params without connections are NOT in widgets_values

        # Collect parameters in to_standard order
        required_widgetable = []
        required_nonwidget = []
        optional_widgetable_in_widgets = []  # optional widget-able that are in widgets_values
        optional_nonwidget_in_widgets = []  # optional non-widget that are in widgets_values

        # Process required parameters
        for param_name, param_def in required_params.items():
            param_type = get_param_type(param_def)
            if is_widgetable_type(param_type):
                required_widgetable.append((param_name, param_type))
            else:
                required_nonwidget.append((param_name, param_type))

        # Process optional parameters (only those with connections are in widgets_values)
        for param_name, param_def in optional_params.items():
            if param_name not in input_connections:
                continue  # Not in widgets_values
            param_type = get_param_type(param_def)
            if is_widgetable_type(param_type):
                optional_widgetable_in_widgets.append((param_name, param_type))
            else:
                optional_nonwidget_in_widgets.append((param_name, param_type))

        # Map widgets_values to parameters in to_standard order
        widget_idx = 0

        # 1. required + widget-able
        for param_name, param_type in required_widgetable:
            if widget_idx >= len(widgets_values):
                break
            if param_name not in input_connections:
                # Non-connected: extract actual value
                parameters[param_name] = widgets_values[widget_idx]
            # Connected: skip (will be added via input_connections)
            widget_idx += 1

        # 2. required + non-widget
        for param_name, param_type in required_nonwidget:
            if widget_idx >= len(widgets_values):
                break
            if param_name not in input_connections:
                # Non-connected: extract actual value
                parameters[param_name] = widgets_values[widget_idx]
            # Connected: skip (will be added via input_connections)
            widget_idx += 1

        # 3. optional + widget-able (with connections)
        for param_name, param_type in optional_widgetable_in_widgets:
            if widget_idx >= len(widgets_values):
                break
            # These all have connections, so skip (will be added via input_connections)
            widget_idx += 1

        # 4. optional + non-widget (with connections)
        for param_name, param_type in optional_nonwidget_in_widgets:
            if widget_idx >= len(widgets_values):
                break
            # These all have connections, so skip (will be added via input_connections)
            widget_idx += 1

        return parameters

    def _convert_node_to_standard(
        self,
        node_name: str,
        lite_node: Dict,
        node_id: int,
        pos: Tuple[int, int] = (0, 0)
    ) -> Dict:
        """
        Convert a lite node to standard format.

        Args:
            node_name: Node name
            lite_node: Lite format node data
            node_id: Node ID
            pos: Node position as (x, y) tuple

        Returns:
            Standard format node dictionary
        """
        node_type = lite_node.get("type", "PrimitiveNode")
        inputs = lite_node.get("inputs", {})
        outputs = lite_node.get("outputs", [])

        # Build inputs array and widgets_values
        inputs_array, widgets_values = self._build_standard_inputs(node_type, inputs, outputs)

        # Build outputs array
        outputs_array = self._build_standard_outputs(node_type, outputs)

        # Convert pos tuple to list if needed
        pos_list = list(pos) if isinstance(pos, tuple) else pos

        return {
            "id": node_id,
            "type": node_type,
            "pos": pos_list,
            "size": [270, 82],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": inputs_array,
            "outputs": outputs_array,
            "properties": {},
            "widgets_values": widgets_values
        }

    def _build_standard_inputs(
        self,
        node_type: str,
        lite_inputs: Dict,
        lite_outputs: List[str]
    ) -> Tuple[List[Dict], List[Any]]:
        """
        Build standard format inputs array and widgets_values.

        Args:
            node_type: Node type
            lite_inputs: Lite format inputs dict
            lite_outputs: Lite format outputs list

        Returns:
            Tuple of (inputs_array, widgets_values)
        """
        inputs_array = []
        widgets_values = []
        param_order = self.type_resolver.get_parameter_order(node_type)

        # Track connected inputs
        connected_input_names = set()
        for input_name, input_value in lite_inputs.items():
            if isinstance(input_value, dict) and "node_id" in input_value:
                connected_input_names.add(input_name)

        # Build widgets_values
        # Rules:
        # 1. Include all required parameters (use default value if not in lite format)
        # 2. Include optional parameters that exist in lite format and have links (use default value)
        # 3. Order: First required, then optional. Within each category, widget-able types first, then non-widget types
        #    Widget-able types: STRING, INT, FLOAT, BOOLEAN, COMBO, etc.
        #    Non-widget types: MODEL, VAE, CLIP, CONDITIONING, LATENT, IMAGE, etc.
        if param_order:
            # Get required and optional parameter sets
            required_params = {}
            optional_params = {}
            if self.type_resolver.node_info and node_type in self.type_resolver.node_info:
                node_def = self.type_resolver.node_info[node_type]
                input_defs = node_def.get("input", {})
                if "required" in input_defs:
                    required_params = input_defs["required"]
                if "optional" in input_defs:
                    optional_params = input_defs["optional"]
            
            # Helper function to check if a type is widget-able
            def is_widgetable_type(param_type: str) -> bool:
                """Check if parameter type is widget-able (primitive type)."""
                widgetable_types = {"STRING", "INT", "FLOAT", "BOOLEAN", "COMBO"}
                return param_type in widgetable_types
            
            # Helper function to get parameter type
            def get_param_type(param_name: str, param_def: Any) -> str:
                """Get parameter type from node_info definition."""
                if isinstance(param_def, list) and len(param_def) > 0:
                    first_elem = param_def[0]
                    if isinstance(first_elem, str):
                        return first_elem
                    elif isinstance(first_elem, list):
                        # COMBO type
                        return "COMBO"
                return "STRING"  # Default
            
            # Collect parameters that should be in widgets_values
            # Maintain original order within required/optional, but group by widget-able vs non-widget
            required_widgetable = []  # List of (param_name, param_type)
            required_nonwidget = []    # List of (param_name, param_type)
            optional_widgetable = []   # List of (param_name, param_type)
            optional_nonwidget = []    # List of (param_name, param_type)
            
            # Process required parameters (maintain original order)
            for param_name, param_def in required_params.items():
                param_type = get_param_type(param_name, param_def)
                if is_widgetable_type(param_type):
                    required_widgetable.append((param_name, param_type))
                else:
                    required_nonwidget.append((param_name, param_type))
            
            # Process optional parameters that exist in lite format and have links (maintain original order)
            for param_name, param_def in optional_params.items():
                if param_name in lite_inputs:
                    input_value = lite_inputs[param_name]
                    # Only include if it's a connection (has link)
                    if isinstance(input_value, dict) and "node_id" in input_value:
                        param_type = get_param_type(param_name, param_def)
                        if is_widgetable_type(param_type):
                            optional_widgetable.append((param_name, param_type))
                        else:
                            optional_nonwidget.append((param_name, param_type))
            
            # Combine in correct order: required (widget-able, then non-widget), then optional (widget-able, then non-widget)
            params_to_include = []
            params_to_include.extend([(name, typ, True, True) for name, typ in required_widgetable])
            params_to_include.extend([(name, typ, True, False) for name, typ in required_nonwidget])
            params_to_include.extend([(name, typ, False, True) for name, typ in optional_widgetable])
            params_to_include.extend([(name, typ, False, False) for name, typ in optional_nonwidget])
            
            # Build widgets_values in sorted order
            for param_name, param_type, is_required, is_widgetable in params_to_include:
                if param_name in lite_inputs:
                    input_value = lite_inputs[param_name]
                    if isinstance(input_value, dict) and "node_id" in input_value:
                        # Connected input - use default value
                        widget_value = self.type_resolver.get_default_value(node_type, param_name)
                        widgets_values.append(widget_value if widget_value is not None else "")
                    else:
                        # Parameter value - use value from lite format
                        widgets_values.append(input_value)
                else:
                    # Parameter not in lite format - use default value
                    widget_value = self.type_resolver.get_default_value(node_type, param_name)
                    widgets_values.append(widget_value if widget_value is not None else "")
        else:
            # Fallback: preserve all input values in order (for nodes without node_info)
            # Sort by param_N names to maintain order
            sorted_params = sorted(
                [k for k in lite_inputs.keys() if k.startswith("param_")],
                key=lambda x: int(x.split("_")[1]) if x.split("_")[1].isdigit() else 0
            )
            for param_name in sorted_params:
                widgets_values.append(lite_inputs[param_name])

            # Also include non-param values (non-connection inputs)
            for input_name, input_value in lite_inputs.items():
                if not input_name.startswith("param_") and not isinstance(input_value, dict):
                    if input_name not in sorted_params:
                        widgets_values.append(input_value)

        # Build inputs array
        # Rules:
        # 1. All optional inputs that exist in lite format must be in inputs array (as connections or widgets)
        # 2. All connected inputs must be in inputs array
        # 3. All inputs with values (widgets) must be in inputs array
        # 4. All optional inputs from node_info (with widgets) must be in inputs array
        # 5. No special handling for param_type - follow node_info order
        
        # Get required and optional parameter sets
        required_params = set()
        optional_params = set()
        if self.type_resolver.node_info and node_type in self.type_resolver.node_info:
            node_def = self.type_resolver.node_info[node_type]
            input_defs = node_def.get("input", {})
            if "required" in input_defs:
                required_params = set(input_defs["required"].keys())
            if "optional" in input_defs:
                optional_params = set(input_defs["optional"].keys())
        
        inputs_to_add = {}  # name -> input_dict
        
        # Step 1: Add only connected inputs to inputs array
        # In PyroMind standard format:
        # - Connected inputs (have link) -> appear in inputs array
        # - Unconnected inputs (direct values) -> ONLY in widgets_values, NOT in inputs array
        for input_name, input_value in lite_inputs.items():
            if isinstance(input_value, dict) and "node_id" in input_value:
                # Connection - must be in inputs array
                input_type = self.type_resolver.get_input_type(node_type, input_name)
                input_dict = {
                    "name": input_name,
                    "type": input_type,
                    "link": None  # Will be filled later
                }
                # Add widget info for connected inputs
                input_dict["widget"] = {"name": input_name}
                inputs_to_add[input_name] = input_dict
            # else: Unconnected inputs are NOT added to inputs array
            # Their values are already stored in widgets_values

        # Step 2: Build inputs_array in node_info order
        # Only include connected inputs in inputs_array
        # Follow node_info order, but only for inputs that are actually in inputs_array
        if param_order:
            # Add all inputs in node_info parameter order
            # Only include those that are in inputs_to_add (i.e., should be in inputs_array)
            for param_name in param_order:
                if param_name in inputs_to_add:
                    inputs_array.append(inputs_to_add[param_name])
        else:
            # Fallback: add all inputs in the order they were found
            for input_dict in inputs_to_add.values():
                inputs_array.append(input_dict)

        return inputs_array, widgets_values

    def _build_standard_outputs(self, node_type: str, lite_outputs: List[str]) -> List[Dict]:
        """
        Build standard format outputs array.

        Args:
            node_type: Node type
            lite_outputs: Lite format outputs list

        Returns:
            Standard format outputs array
        """
        outputs_array = []

        # Get expected output names from node_info if available
        expected_output_names = None
        if node_type in self.type_resolver.node_info:
            node_def = self.type_resolver.node_info[node_type]
            output_names = node_def.get("output_name", [])
            if output_names and len(output_names) >= len(lite_outputs):
                expected_output_names = output_names

        for idx, output_name in enumerate(lite_outputs):
            # Use expected output name from node_info if available
            actual_name = output_name
            if expected_output_names and idx < len(expected_output_names):
                actual_name = expected_output_names[idx]

            output_type = self.type_resolver.get_output_type(node_type, idx, actual_name)
            outputs_array.append({
                "name": actual_name,
                "type": output_type,
                "links": []
            })

        return outputs_array

    def _update_nodes_with_links(self, nodes: List[Dict], links: List[List], lite_nodes: Dict[str, Dict] = None) -> None:
        """
        Update nodes with link references.

        Args:
            nodes: List of node dictionaries (modified in place)
            links: List of link arrays
            lite_nodes: Lite format nodes to check which inputs are connections
        """
        # Build mappings
        target_input_links = {}  # target_id -> {input_idx: link_id}
        output_links_map = {}  # source_id -> {output_idx: [link_ids]}

        for link in links:
            if len(link) >= 6:
                link_id, source_id, source_idx, target_id, target_idx, link_type = link[:6]

                if target_id not in target_input_links:
                    target_input_links[target_id] = {}
                target_input_links[target_id][target_idx] = link_id

                if source_id not in output_links_map:
                    output_links_map[source_id] = {}
                if source_idx not in output_links_map[source_id]:
                    output_links_map[source_id][source_idx] = []
                output_links_map[source_id][source_idx].append(link_id)

        # Update nodes
        for node in nodes:
            node_id = node["id"]
            node_name = self.node_mapper.get_name(node_id)

            # Check which inputs are connections in lite format
            connected_input_names = set()
            if lite_nodes and node_name:
                lite_node = lite_nodes.get(node_name, {})
                lite_inputs = lite_node.get("inputs", {})
                for input_name, input_value in lite_inputs.items():
                    if isinstance(input_value, dict) and "node_id" in input_value:
                        connected_input_names.add(input_name)

            # Update input links
            # Only set link for inputs that are actually connections in lite format
            if node_id in target_input_links:
                input_links = target_input_links[node_id]
                for i, inp in enumerate(node["inputs"]):
                    if i in input_links:
                        input_name = inp.get("name")
                        # Only set link if this input is a connection in lite format
                        if input_name in connected_input_names:
                            inp["link"] = input_links[i]
                        # Otherwise, don't set the link (it's not a connection)

            # Update output links
            if node_id in output_links_map:
                output_links = output_links_map[node_id]
                for i, out in enumerate(node["outputs"]):
                    if i in output_links:
                        out["links"] = output_links[i]
            else:
                # No links from this node
                for out in node["outputs"]:
                    out["links"] = []

    def _generate_workflow_id(self, original_workflow: Optional[Dict], lite: Dict) -> str:
        """
        Generate workflow ID in UUID format.

        Args:
            original_workflow: Original workflow if available
            lite: Lite format workflow

        Returns:
            UUID string like "189cc5d9-cb63-4b03-9a92-9a5b43ae17cc"
        """
        # Try to preserve original ID if it's already a UUID
        if original_workflow:
            original_id = original_workflow.get("id", "")
            if self._is_valid_uuid(original_id):
                return original_id

        # Try to get ID from lite format
        lite_id = lite.get("id", "")
        if self._is_valid_uuid(lite_id):
            return lite_id

        # Generate new UUID
        return str(uuid.uuid4())

    @staticmethod
    def _is_valid_uuid(id_string: str) -> bool:
        """
        Check if a string is a valid UUID.

        Args:
            id_string: String to check

        Returns:
            True if string is a valid UUID
        """
        try:
            uuid.UUID(id_string)
            return True
        except (ValueError, AttributeError):
            return False


# Convenience functions
def to_workflow_lite(
    workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convert standard workflow to workflow_lite format.

    Convenience function that creates a converter and performs conversion.

    Args:
        workflow: Standard workflow dictionary
        node_info: Optional node information dictionary from get_node_info API

    Returns:
        Workflow lite dictionary
    """
    converter = WorkflowLiteConverter(node_info=node_info)
    return converter.to_lite(workflow)


def to_workflow_standard(
    lite: Dict[str, Any],
    original_workflow: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Convert workflow_lite to standard workflow format.

    Convenience function that creates a converter and performs conversion.

    Args:
        lite: Workflow lite dictionary
        original_workflow: Optional original workflow to preserve metadata

    Returns:
        Standard workflow dictionary
    """
    converter = WorkflowLiteConverter()
    return converter.to_standard(lite, original_workflow)
