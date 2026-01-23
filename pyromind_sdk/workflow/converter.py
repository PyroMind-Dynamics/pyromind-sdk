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
"""

import re
from typing import Dict, List, Any, Optional


class WorkflowLiteConverter:
    """
    Universal converter between standard workflow and workflow_lite formats.

    This converter uses node_info (from get_node_info API) to accurately
    map parameters, making conversions more precise and readable.

    The converter is node-agnostic and works with any node type.
    """

    def __init__(self, node_info: Optional[Dict[str, Any]] = None):
        """
        Initialize the converter.

        Args:
            node_info: Optional node information dictionary from get_node_info API.
                      If provided, parameter names will be accurately mapped.
                      If None, uses generic heuristic-based extraction.
        """
        self._next_node_id = 1
        self._next_link_id = 1
        self._node_info = node_info or {}

    def set_node_info(self, node_info: Dict[str, Any]) -> None:
        """
        Update node information for parameter mapping.

        Args:
            node_info: Node information dictionary from get_node_info API
        """
        self._node_info = node_info

    def to_lite(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert standard workflow format to workflow_lite format.

        Args:
            workflow: Standard workflow dictionary

        Returns:
            Workflow lite dictionary
        """
        # Build node ID to name mapping (handle duplicates)
        node_id_to_name = {}
        name_counters = {}
        for node in workflow.get("nodes", []):
            node_id = node.get("id")
            node_type = node.get("type", "")
            # Generate a readable name from node type
            base_name = self._generate_node_name(node_type, node_id)

            # Handle duplicate names by adding counter suffix
            if base_name not in name_counters:
                name_counters[base_name] = 0
                unique_name = base_name
            else:
                name_counters[base_name] += 1
                unique_name = f"{base_name}_{name_counters[base_name]}"

            node_id_to_name[node_id] = unique_name

        # Build link lookup for socket name resolution
        socket_names = self._build_socket_name_mapping(workflow.get("nodes", []))

        # Build input connections mapping: {node_id: {input_name: (source_node, source_output)}}
        input_connections = self._build_input_connections(
            workflow.get("links", []),
            node_id_to_name,
            socket_names
        )

        # Convert nodes
        lite_nodes = {}
        for node in workflow.get("nodes", []):
            node_id = node.get("id")
            node_name = node_id_to_name[node_id]
            lite_nodes[node_name] = self._convert_node_to_lite(
                node,
                input_connections.get(node_id, {}),
                node_id_to_name
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
        self._next_link_id = 1

        # Build node name to ID mapping
        # Use the index from lite format as the node_id to maintain consistency
        node_name_to_id = {}
        nodes = []
        max_node_id = 0
        for node_name, node_data in lite.get("nodes", {}).items():
            # Use index from lite format if available, otherwise generate new ID
            original_index = node_data.get("index")
            if original_index is not None:
                node_id = original_index
            else:
                # If no index, we need to generate one
                # But this shouldn't happen if to_lite preserved the index
                node_id = max_node_id + 1
            node_name_to_id[node_name] = node_id
            max_node_id = max(max_node_id, node_id)
            nodes.append(self._convert_node_to_standard(node_name, node_data, node_id))
        
        # Update last_node_id for the workflow
        self._next_node_id = max_node_id + 1

        # Convert connections from inputs to links
        links = self._convert_input_connections_to_links(
            lite.get("nodes", {}),
            node_name_to_id
        )

        # Update outputs links based on converted links
        # Build a mapping: target_node_id -> {input_idx: link_id}
        target_input_links = {}  # target_id -> {input_idx: link_id}
        for link in links:
            link_id, source_id, source_idx, target_id, target_idx, link_type = link[:6]
            if target_id not in target_input_links:
                target_input_links[target_id] = {}
            target_input_links[target_id][target_idx] = link_id

        # Build output links mapping: source_node_id -> {output_idx: [link_ids]}
        output_links_map = {}  # source_id -> {output_idx: [link_ids]}
        for link in links:
            link_id, source_id, source_idx, target_id, target_idx, link_type = link[:6]
            if source_id not in output_links_map:
                output_links_map[source_id] = {}
            if source_idx not in output_links_map[source_id]:
                output_links_map[source_id][source_idx] = []
            output_links_map[source_id][source_idx].append(link_id)

        # Update nodes with correct input links and output links
        for node in nodes:
            node_id = node["id"]
            
            # Update input links
            if node_id in target_input_links:
                input_links = target_input_links[node_id]
                for i, inp in enumerate(node["inputs"]):
                    if i in input_links:
                        inp["link"] = input_links[i]
            
            # Update outputs links
            if node_id in output_links_map:
                output_links = output_links_map[node_id]
                for i, out in enumerate(node["outputs"]):
                    if i in output_links:
                        out["links"] = output_links[i]
                    else:
                        out["links"] = []
            else:
                # No links from this node, set all outputs links to empty
                for out in node["outputs"]:
                    out["links"] = []

        # Create standard workflow
        standard = {
            "id": lite.get("name", "workflow"),
            "revision": 0,
            "last_node_id": len(nodes),
            "last_link_id": len(links),
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
            standard["id"] = original_workflow.get("id", standard["id"])
            if "extra" in original_workflow:
                standard["extra"].update(original_workflow["extra"])

        return standard

    def _generate_node_name(self, node_type: str, node_id: int) -> str:
        """
        Generate a readable node name from type.

        Converts CamelCase to snake_case and removes 'node' suffix.
        Handles consecutive capitals (LLM -> llm, not l_l_m).
        The node_id is NOT included in the name - it's added as 'index' field.
        """
        # Convert CamelCase to snake_case, handling consecutive capitals
        # This regex: 1) Insert underscore before capital letters (except at start)
        #             2) But NOT before capitals that follow another capital
        #             3) Then insert before the last capital in a sequence
        # First, add underscore before capital letters that are not at start
        # and not preceded by another capital (handles "TestLLM" -> "Test_LLM")
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', node_type)
        # Then handle consecutive capitals (LLM -> LLM, then lowercase)
        name = re.sub('([a-z0-9])([A-Z]+)', r'\1_\2', name)
        name = name.lower()

        # Remove 'node' suffix if present
        if name.endswith('_node'):
            name = name[:-5]

        # If name is too short after conversion, use 'node_' + type
        if len(name) < 3:
            name = f"node_{node_type.lower()}"

        return name

    def _build_socket_name_mapping(self, nodes: List[Dict]) -> Dict[int, Dict]:
        """
        Build a mapping of node IDs to their socket names by index.

        Returns:
            Dict mapping node_id -> {"inputs": {idx: name}, "outputs": {idx: name}}
        """
        socket_names = {}
        for node in nodes:
            node_id = node.get("id")
            inputs = node.get("inputs", [])
            outputs = node.get("outputs", [])

            input_map = {}
            for idx, inp in enumerate(inputs):
                if inp.get("name"):
                    input_map[idx] = inp.get("name")

            output_map = {}
            for idx, out in enumerate(outputs):
                if out.get("name"):
                    output_map[idx] = out.get("name")

            socket_names[node_id] = {
                "inputs": input_map,
                "outputs": output_map
            }

        return socket_names

    def _build_input_connections(
        self,
        links: List[List],
        node_id_to_name: Dict[int, str],
        socket_names: Dict[int, Dict]
    ) -> Dict[int, Dict]:
        """
        Build input connections mapping from links.

        Returns:
            Dict mapping {node_id: {input_name: {node_id: source_id, output_name: name}}}
        """
        input_connections = {}

        for link in links:
            if len(link) >= 6:
                link_id, source_id, source_idx, target_id, target_idx, link_type = link[:6]

                # Get actual socket names if available
                source_sockets = socket_names.get(source_id, {}).get("outputs", {})
                target_sockets = socket_names.get(target_id, {}).get("inputs", {})

                output_name = source_sockets.get(source_idx, f"output_{source_idx}")
                input_name = target_sockets.get(target_idx, f"input_{target_idx}")

                if target_id not in input_connections:
                    input_connections[target_id] = {}
                # New format: {node_id: source_id, output_name: name}
                input_connections[target_id][input_name] = {
                    "node_id": source_id,
                    "output_name": output_name
                }

        return input_connections

    def _convert_node_to_lite(
        self,
        node: Dict,
        input_connections: Dict,
        node_id_to_name: Dict[int, str]
    ) -> Dict:
        """
        Convert a single node to lite format.

        New simplified format:
        - inputs: dict with parameter values or {node_id, output_name} connections
        - outputs: list of output names only
        """
        node_type = node.get("type", "")
        inputs = node.get("inputs", [])
        outputs = node.get("outputs", [])

        # Build inputs: parameter values or connections
        lite_inputs = {}
        for inp in inputs:
            input_name = inp.get("name", "")
            input_type = inp.get("type", "")
            # Skip ENV inputs (they're usually auto-provided)
            if input_name and input_type != "ENV":
                # Check if this input has a connection
                if input_name in input_connections:
                    lite_inputs[input_name] = input_connections[input_name]
                # Check if input has a widget value (parameter)
                elif inp.get("widget"):
                    # This input has a widget, will be handled in _extract_parameters
                    pass
                else:
                    # No connection, no widget - could be a default value
                    lite_inputs[input_name] = None

        # Extract parameters (widget values) and map to actual input names
        # This includes ALL widget values, even for connected inputs
        parameters = self._extract_parameters_with_names(node, node_type, inputs, input_connections)

        # Merge parameters into inputs (for non-connected inputs only)
        # For connected inputs with widgets, we don't save the widget value in lite format
        # because it's typically the default value and can be restored from node_info in to_standard
        for param_name, param_value in parameters.items():
            if param_name not in lite_inputs:
                # Non-connected input with widget value
                lite_inputs[param_name] = param_value

        # Build outputs as list of names only
        lite_outputs = []
        for out in outputs:
            output_name = out.get("name", "")
            if output_name:
                lite_outputs.append(output_name)

        return {
            "type": node_type,
            "inputs": lite_inputs,
            "outputs": lite_outputs,
            "index": node.get("id", 0)
        }

    def _get_node_description(self, node_type: str) -> str:
        """Get description for a node type from node_info."""
        if node_type in self._node_info:
            node_data = self._node_info[node_type]
            desc = node_data.get("description", "")
            if desc:
                return desc
        return f"{node_type} node"

    def _extract_parameters_with_names(
        self,
        node: Dict,
        node_type: str,
        inputs: List[Dict],
        input_connections: Dict
    ) -> Dict[str, Any]:
        """
        Extract parameters from widgets_values and map to actual input names.

        Uses node_info for accurate mapping, falls back to heuristic-based naming.

        Args:
            node: Node dictionary
            node_type: Type of the node
            inputs: List of input definitions
            input_connections: Mapping of connected inputs {input_name: connection_dict}
        """
        widgets_values = node.get("widgets_values", [])
        if not widgets_values:
            return {}

        # Method 1: Use node_info if available
        if node_type in self._node_info:
            return self._extract_using_node_info(
                node,
                self._node_info[node_type],
                widgets_values,
                inputs,
                input_connections
            )

        # Method 2: Map widget values to input names from the node
        parameter_inputs = [
            inp.get("name") for inp in inputs
            if inp.get("widget") and inp.get("name") and inp.get("name") not in input_connections
        ]

        parameters = {}
        for i, value in enumerate(widgets_values):
            if i < len(parameter_inputs):
                parameters[parameter_inputs[i]] = value
            else:
                # Method 3: Use heuristic based on node type
                param_name = self._guess_parameter_name(node_type, i, value)
                parameters[param_name] = value

        return parameters

    def _guess_parameter_name(self, node_type: str, index: int, value: Any) -> str:
        """
        Generate a generic parameter name.

        This is a fallback when node_info is not available.
        Uses generic naming without node-specific heuristics.
        """
        # Generic fallback - use param_N format
        return f"param_{index}"

    def _extract_parameters(
        self,
        node: Dict,
        node_type: str,
        lite_inputs: Dict,
        lite_outputs: Dict
    ) -> Dict[str, Any]:
        """
        Extract parameters from node using node_info for accurate mapping.

        Uses node_info to get proper parameter names for widgets_values.

        Args:
            node: Node dictionary from workflow
            node_type: Type of the node
            lite_inputs: Input names and types
            lite_outputs: Output names and types

        Returns:
            Dictionary mapping parameter names to values
        """
        widgets_values = node.get("widgets_values", [])
        if not widgets_values:
            return {}

        # Method 1: Use node_info if available
        if node_type in self._node_info:
            return self._extract_using_node_info(
                node,
                self._node_info[node_type],
                widgets_values
            )

        # Method 2: Try widget definitions
        widgets_info = self._get_widgets_info(node)
        if widgets_info and len(widgets_info) == len(widgets_values):
            return self._extract_using_widgets(widgets_values, widgets_info)

        # Method 3: Generic fallback using input/output mapping
        return self._extract_generic_fallback(
            widgets_values,
            lite_inputs,
            lite_outputs
        )

    def _extract_using_node_info(
        self,
        node: Dict,
        node_info: Dict,
        widgets_values: List[Any],
        inputs: List[Dict],
        input_connections: Dict
    ) -> Dict[str, Any]:
        """
        Extract parameters using node_info from get_node_info API.

        The key insight is that widgets_values order matches the order of inputs
        that have widgets and are not connected, not the order in node_info.

        node_info structure:
        {
          "input": {
            "required": {"param_name": [type, {...}], ...},
            "optional": {"param_name": [type, {...}], ...}
          }
        }
        """
        parameters = {}

        # Get connected input names to skip (for final output, not for mapping)
        connected_input_names = set(input_connections.keys())

        # Get input definitions from node_info
        input_defs = node_info.get("input", {})
        
        # Build parameter order from node_info (required first, then optional)
        # widgets_values order matches node_info parameter order, BUT skips connected inputs
        # So we need to build the order including all params, then map widgets_values
        # by skipping connected ones
        all_params_order = []
        for category in ["required", "optional"]:
            if category in input_defs:
                category_params = input_defs[category]
                if isinstance(category_params, dict):
                    for param_name, param_def in category_params.items():
                        all_params_order.append(param_name)

        # Map widgets_values to input names
        # In ComfyUI, widgets_values includes ALL inputs with widgets, even if they have connections
        # The order matches node_info parameter order, including connected ones
        # So widgets_values[i] corresponds to all_params_order[i], regardless of connection status
        for i, value in enumerate(widgets_values):
            if i < len(all_params_order):
                param_name = all_params_order[i]
                # Add to parameters even if connected - the connection will be in inputs,
                # but the widget value should also be preserved for to_standard conversion
                # However, we only add it if it's not already in lite_inputs (which would have the connection)
                # Actually, we should always add it, because in lite format we want to preserve
                # the widget value even for connected inputs
                parameters[param_name] = value
            else:
                # Fallback for extra values not in node_info
                parameters[f"param_{i}"] = value

        return parameters

    def _extract_using_widgets(
        self,
        widgets_values: List[Any],
        widgets_info: List[Dict]
    ) -> Dict[str, Any]:
        """Extract parameters using widget definitions from the node."""
        parameters = {}
        for i, (value, widget) in enumerate(zip(widgets_values, widgets_info)):
            widget_name = widget.get("name", "")
            if widget_name:
                parameters[widget_name] = value
            else:
                parameters[f"param_{i}"] = value
        return parameters

    def _extract_generic_fallback(
        self,
        widgets_values: List[Any],
        lite_inputs: Dict,
        lite_outputs: Dict
    ) -> Dict[str, Any]:
        """
        Generic parameter extraction fallback.

        Tries to map widgets_values to input/output names when no
        node_info or widget definitions are available.
        """
        parameters = {}
        input_names = list(lite_inputs.keys())
        output_names = list(lite_outputs.keys())

        for i, value in enumerate(widgets_values):
            # Try to match with input names first
            if i < len(input_names):
                parameters[input_names[i]] = value
            # Then try output names
            elif i < len(output_names):
                parameters[output_names[i]] = value
            # Fall back to generic name
            else:
                parameters[f"param_{i}"] = value

        return parameters

    def _get_widgets_info(self, node: Dict) -> Optional[List[Dict]]:
        """
        Extract widget definitions from a node.

        Widgets are typically defined in inputs with 'widget' field.
        """
        widgets = []
        inputs = node.get("inputs", [])

        for inp in inputs:
            if "widget" in inp and inp["widget"]:
                widgets.append(inp["widget"])

        return widgets if widgets else None

    def _convert_links_to_connections(
        self,
        links: List[List],
        node_id_to_name: Dict[int, str],
        socket_names: Dict[int, Dict]
    ) -> List[Dict]:
        """
        Convert links array to readable connections.

        Uses socket name mapping to create readable connection definitions.
        """
        connections = []

        for link in links:
            if len(link) >= 6:
                link_id, source_id, source_idx, target_id, target_idx, link_type = link[:6]

                source_name = node_id_to_name.get(source_id, f"node_{source_id}")
                target_name = node_id_to_name.get(target_id, f"node_{target_id}")

                # Get actual socket names if available
                source_sockets = socket_names.get(source_id, {}).get("outputs", {})
                target_sockets = socket_names.get(target_id, {}).get("inputs", {})

                output_name = source_sockets.get(source_idx, f"output_{source_idx}")
                input_name = target_sockets.get(target_idx, f"input_{target_idx}")

                connections.append({
                    "from": source_name,
                    "output": output_name,
                    "to": target_name,
                    "input": input_name
                })

        return connections

    def _convert_node_to_standard(
        self,
        node_name: str,
        lite_node: Dict,
        node_id: int
    ) -> Dict:
        """
        Convert a lite node to standard format.

        New simplified format:
        - inputs: dict with parameter values or {node_id, output_name} connections
        - outputs: list of output names only
        """
        node_type = lite_node.get("type", "PrimitiveNode")
        inputs = lite_node.get("inputs", {})
        outputs = lite_node.get("outputs", [])

        # Get node_info for this node type to extract type information
        node_info = self._node_info.get(node_type, {})
        input_defs = node_info.get("input", {})
        output_types = node_info.get("output", [])
        output_names = node_info.get("output_name", [])

        # Build a mapping from input name to type
        input_type_map = {}
        for category in ["required", "optional"]:
            if category in input_defs:
                category_params = input_defs[category]
                if isinstance(category_params, dict):
                    for param_name, param_def in category_params.items():
                        if isinstance(param_def, list) and len(param_def) > 0:
                            # param_def can be:
                            # 1. ["STRING", {...}] - simple type
                            # 2. [[选项列表], {...}] - enum type (options list)
                            first_elem = param_def[0]
                            if isinstance(first_elem, str):
                                # Simple type like "STRING", "INT", "FLOAT"
                                input_type_map[param_name] = first_elem
                            elif isinstance(first_elem, list):
                                # Enum type - options list, default to "STRING"
                                input_type_map[param_name] = "STRING"

        # Separate inputs into parameters (values) and connections (dicts)
        # In ComfyUI standard format, inputs array only contains:
        # 1. Connected inputs (will have link set later)
        # 2. Inputs with widgets (even if not connected)
        # 3. Special inputs like ENV type (even if not in lite format)
        # Parameter-only inputs (no widget, no connection) are only in widgets_values
        
        parameters = []
        inputs_array = []
        
        # Track which inputs are connections (will be in inputs array)
        connected_input_names = set()
        for input_name, input_value in inputs.items():
            if isinstance(input_value, dict) and "node_id" in input_value:
                connected_input_names.add(input_name)

        # Build widgets_values in the correct order (matching node_info parameter order)
        # In ComfyUI, widgets_values includes values for ALL inputs with widgets,
        # even if they have connections. The order matches node_info parameter order.
        widgets_values_list = []
        
        # Get parameter order from node_info (required first, then optional)
        all_params_order = []
        for category in ["required", "optional"]:
            if category in input_defs:
                category_params = input_defs[category]
                if isinstance(category_params, dict):
                    for param_name, param_def in category_params.items():
                        all_params_order.append(param_name)
        
        # Build widgets_values in node_info order
        # In ComfyUI, widgets_values includes values for ALL inputs with widgets,
        # even if they have connections. The order matches node_info parameter order.
        for param_name in all_params_order:
            if param_name in inputs:
                input_value = inputs[param_name]
                # Check if it's a connection
                if isinstance(input_value, dict) and "node_id" in input_value:
                    # It's a connected input - check if it has a widget value stored
                    # In lite format, we store widget values for connected inputs in _widget_value
                    widget_value = input_value.get("_widget_value")
                    if widget_value is not None:
                        # Use the stored widget value from lite format
                        widgets_values_list.append(widget_value)
                    else:
                        # No widget value stored - check if it should have one from node_info
                        # This handles cases where the widget value wasn't preserved in to_lite
                        default_value = None
                        param_type = None
                        for category in ["required", "optional"]:
                            if category in input_defs:
                                category_params = input_defs[category]
                                if isinstance(category_params, dict) and param_name in category_params:
                                    param_def = category_params[param_name]
                                    if isinstance(param_def, list) and len(param_def) > 0:
                                        first_elem = param_def[0]
                                        param_type = first_elem if isinstance(first_elem, str) else "STRING"
                                        if len(param_def) > 1:
                                            default_info = param_def[1] if isinstance(param_def[1], dict) else {}
                                            default_value = default_info.get("default")
                                        break
                        widgets_values_list.append(default_value)
                else:
                    # It's a parameter value - use value from lite format
                    widgets_values_list.append(input_value)
        
        # First, add all connected inputs
        for input_name, input_value in inputs.items():
            # Get type from node_info, fallback to "AUTO"
            input_type = input_type_map.get(input_name, "AUTO")
            
            # Check if it's a connection (dict with node_id and output_name)
            if isinstance(input_value, dict) and "node_id" in input_value:
                # It's a connection - must be in inputs array
                inputs_array.append({
                    "name": input_name,
                    "type": input_type,
                    "link": None  # Will be filled in when processing connections
                })
            else:
                # It's a parameter value - already added to widgets_values_list above
                pass
        
        # Add special inputs that should be in inputs array but weren't in lite format
        # (e.g., ENV type inputs that were skipped during to_lite conversion)
        for category in ["required", "optional"]:
            if category in input_defs:
                category_params = input_defs[category]
                if isinstance(category_params, dict):
                    for param_name, param_def in category_params.items():
                        # Skip if already added (connected input)
                        if param_name in connected_input_names:
                            continue
                        # Skip if already in lite inputs (parameter value)
                        if param_name in inputs:
                            continue
                        
                        # Check if it's a special type that should be in inputs array
                        if isinstance(param_def, list) and len(param_def) > 0:
                            first_elem = param_def[0]
                            param_type = first_elem if isinstance(first_elem, str) else "STRING"
                            
                            # ENV type inputs should be in inputs array
                            if param_type == "ENV":
                                inputs_array.append({
                                    "name": param_name,
                                    "type": "ENV",
                                    "link": None
                                })

        # Build outputs array with types from node_info
        outputs_array = []
        for idx, output_name in enumerate(outputs):
            # Try to get type from output_types array by index
            # If output_names is available, try to match by name first
            output_type = "AUTO"
            if output_names and output_name in output_names:
                name_idx = output_names.index(output_name)
                if name_idx < len(output_types):
                    output_type = output_types[name_idx]
            elif idx < len(output_types):
                output_type = output_types[idx]
            
            outputs_array.append({
                "name": output_name,
                "type": output_type,
                "links": []
            })

        return {
            "id": node_id,
            "type": node_type,
            "pos": [0, 0],
            "size": [270, 82],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": inputs_array,
            "outputs": outputs_array,
            "properties": {},
            "widgets_values": widgets_values_list
        }

    def _convert_input_connections_to_links(
        self,
        lite_nodes: Dict[str, Dict],
        node_name_to_id: Dict[str, int]
    ) -> List[List]:
        """
        Convert embedded input connections to links array.

        Scans all node inputs for {node_id, output_name} patterns
        and converts them to standard links.
        
        The node_id in lite format connections refers to the original workflow's node index,
        which is now the same as the new node_id (since we preserve the index).
        """
        links = []

        # First, build output name to index mapping for each node
        node_outputs = {}  # node_id -> {output_name: idx}

        for node_name, node_data in lite_nodes.items():
            node_id = node_name_to_id.get(node_name)
            if node_id is None:
                continue

            outputs = node_data.get("outputs", [])
            output_map = {}
            for idx, output_name in enumerate(outputs):
                output_map[output_name] = idx
            node_outputs[node_id] = output_map

        # Also build a reverse mapping from node_id to node_name
        node_id_to_name = {v: k for k, v in node_name_to_id.items()}

        # Process connections from inputs
        for node_name, node_data in lite_nodes.items():
            target_id = node_name_to_id.get(node_name)
            if target_id is None:
                continue

            inputs = node_data.get("inputs", {})

            for input_name, input_value in inputs.items():
                # Check if it's a connection (dict with node_id and output_name)
                if isinstance(input_value, dict):
                    source_id = input_value.get("node_id")
                    output_name = input_value.get("output_name")

                    if source_id is not None:
                        # source_id is already the correct node_id (same as index)
                        
                        # Get output index
                        output_idx = 0
                        if source_id in node_outputs:
                            output_map = node_outputs[source_id]
                            output_idx = output_map.get(output_name, 0)

                        # Get input index (find in node's inputs array)
                        # In standard format, inputs_array contains:
                        # 1. Connected inputs (in order from lite inputs dict)
                        # 2. Special inputs like ENV (from node_info)
                        # So we need to count only these inputs to get the correct index
                        target_inputs = node_data.get("inputs", {})
                        node_type = node_data.get("type", "")
                        
                        # Get node_info to check for ENV inputs
                        node_info = self._node_info.get(node_type, {})
                        input_defs = node_info.get("input", {})
                        
                        # Count inputs that will be in inputs_array before this input
                        input_idx = 0
                        for inp_name in target_inputs.keys():
                            if inp_name == input_name:
                                break
                            inp_value = target_inputs[inp_name]
                            # Count if it's a connection
                            if isinstance(inp_value, dict) and "node_id" in inp_value:
                                input_idx += 1
                            # Count if it's an ENV type (check node_info)
                            else:
                                # Check if this input is ENV type in node_info
                                for category in ["required", "optional"]:
                                    if category in input_defs:
                                        category_params = input_defs[category]
                                        if isinstance(category_params, dict) and inp_name in category_params:
                                            param_def = category_params[inp_name]
                                            if isinstance(param_def, list) and len(param_def) > 0:
                                                first_elem = param_def[0]
                                                param_type = first_elem if isinstance(first_elem, str) else "STRING"
                                                if param_type == "ENV":
                                                    input_idx += 1
                                                    break

                        # Get link type from source node's output type
                        link_type = "AUTO"
                        source_node_name = node_id_to_name.get(source_id)
                        if source_node_name:
                            source_node_data = lite_nodes.get(source_node_name, {})
                            source_node_type = source_node_data.get("type")
                            if source_node_type and source_node_type in self._node_info:
                                source_node_info = self._node_info[source_node_type]
                                source_output_types = source_node_info.get("output", [])
                                source_output_names = source_node_info.get("output_name", [])
                                if source_output_names and output_name in source_output_names:
                                    name_idx = source_output_names.index(output_name)
                                    if name_idx < len(source_output_types):
                                        link_type = source_output_types[name_idx]
                                elif output_idx < len(source_output_types):
                                    link_type = source_output_types[output_idx]

                        # Create link (temporarily use 0 as link_id, will reassign after sorting)
                        links.append([0, source_id, output_idx, target_id, input_idx, link_type])

        # Sort links by (target_id, source_id) to match original workflow order
        # This matches how ComfyUI orders links: by target node first, then source node
        links.sort(key=lambda x: (x[3], x[1]))  # Sort by target_id, then source_id
        
        # Reassign link_id in sorted order
        for i, link in enumerate(links):
            link[0] = i + 1
        
        return links

    def _convert_connections_to_links(
        self,
        connections: List[Dict],
        node_name_to_id: Dict[str, int]
    ) -> List[List]:
        """
        Convert readable connections to links array.

        This is a lossy conversion as we need to determine socket indices.
        We'll use a simple heuristic: try to match by name.
        """
        links = []

        # First, build a reverse mapping to help with index lookup
        # For simplicity, we'll assign indices sequentially
        node_inputs = {}  # node_id -> {input_name: idx}
        node_outputs = {}  # node_id -> {output_name: idx}

        for conn in connections:
            source_name = conn.get("from")
            output_name = conn.get("output")
            target_name = conn.get("to")
            input_name = conn.get("input")

            source_id = node_name_to_id.get(source_name)
            target_id = node_name_to_id.get(target_name)

            if source_id is not None and target_id is not None:
                link_id = self._next_link_id
                self._next_link_id += 1

                # Get or assign socket indices
                if source_id not in node_outputs:
                    node_outputs[source_id] = {}
                if output_name not in node_outputs[source_id]:
                    node_outputs[source_id][output_name] = len(node_outputs[source_id])
                source_idx = node_outputs[source_id][output_name]

                if target_id not in node_inputs:
                    node_inputs[target_id] = {}
                if input_name not in node_inputs[target_id]:
                    node_inputs[target_id][input_name] = len(node_inputs[target_id])
                target_idx = node_inputs[target_id][input_name]

                # For link type, we'd need to look up the actual type from the node
                # Use "AUTO" as placeholder
                link_type = "AUTO"

                links.append([link_id, source_id, source_idx, target_id, target_idx, link_type])

        return links


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
