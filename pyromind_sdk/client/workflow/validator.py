"""
Workflow Validator

This module provides comprehensive validation for workflows in both standard and lite formats.

Validation includes:
- Schema validation (required fields, types, formats)
- Link relationship validation (node existence, connections, cycles)
- Type compatibility validation (input/output type matching)
- Business logic validation (orphan nodes, duplicate IDs, etc.)
"""

import re
import uuid
from typing import Dict, List, Any, Tuple, Optional, Set
from ..base import PyroMindAPIError


class ValidationError(Exception):
    """Base exception for validation errors."""
    pass


class SchemaValidationError(ValidationError):
    """Exception raised when schema validation fails."""
    pass


class LinkValidationError(ValidationError):
    """Exception raised when link validation fails."""
    pass


class TypeValidationError(ValidationError):
    """Exception raised when type validation fails."""
    pass


def validate_workflow(
    workflow: dict,
    client=None,
    node_info: Optional[Dict] = None,
    strict: bool = False
) -> Tuple[bool, List[str]]:
    """
    Validate workflow in standard format before sending to server.

    Comprehensive validation including:
    1. Schema validation
    2. Node validation
    3. Link validation
    4. Type compatibility validation

    Args:
        workflow: Workflow JSON dictionary in standard format
        client: PyroMindAPIClient instance (optional, for fetching node_info)
        node_info: Node information dictionary from get_node_info API
        strict: If True, raise exception on first error instead of collecting all errors

    Returns:
        Tuple of (is_valid, error_messages)

    Raises:
        SchemaValidationError: If strict mode and schema validation fails
        LinkValidationError: If strict mode and link validation fails
        TypeValidationError: If strict mode and type validation fails
    """
    errors = []

    # Step 1: Schema validation
    schema_errors = _validate_schema(workflow)
    errors.extend(schema_errors)

    if errors and strict:
        raise SchemaValidationError(f"Schema validation failed: {errors[0]}")

    # Step 2: Build mappings
    try:
        node_map = _build_node_map(workflow.get("nodes", []))
        link_map = _build_link_map(workflow.get("links", []))
    except Exception as e:
        errors.append(f"Failed to build mappings: {str(e)}")
        if strict:
            raise SchemaValidationError(str(e))
        return False, errors

    # Step 3: Node validation
    node_errors = _validate_nodes(workflow.get("nodes", []), node_map, node_info)
    errors.extend(node_errors)

    # Step 4: Link validation
    link_errors = _validate_links(
        workflow.get("links", []),
        node_map,
        link_map,
        node_info
    )
    errors.extend(link_errors)

    # Step 5: Type compatibility validation (if node_info available)
    if node_info:
        type_errors = _validate_type_compatibility(workflow, node_map, link_map, node_info)
        errors.extend(type_errors)
        
        # Step 5.5: Validate widgets_values order (if node_info available)
        widgets_order_errors = []
        for node in workflow.get("nodes", []):
            order_errors = _validate_widgets_values_order(node, node_info)
            widgets_order_errors.extend(order_errors)
        errors.extend(widgets_order_errors)

    # Step 6: Business logic validation
    business_errors = _validate_business_logic(workflow, node_map, link_map)
    errors.extend(business_errors)

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_lite_format(
    data: Dict[str, Any],
    node_info: Optional[Dict] = None,
    strict: bool = False
) -> Tuple[bool, List[str]]:
    """
    Validate workflow in lite format.

    Comprehensive validation including:
    1. Schema validation
    2. Node validation
    3. Connection validation
    4. Type compatibility (if node_info provided)

    Args:
        data: Workflow dictionary in lite format
        node_info: Optional node information for type validation
        strict: If True, raise exception on first error

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Step 1: Schema validation
    schema_errors = _validate_lite_schema(data)
    errors.extend(schema_errors)

    if errors and strict:
        raise SchemaValidationError(f"Schema validation failed: {errors[0]}")

    nodes = data.get("nodes", {})

    # Step 2: Build node ID mapping
    node_ids = {}
    node_ids_reverse = {}  # node_id -> node_name
    for node_name, node_data in nodes.items():
        if "index" in node_data:
            node_id = node_data["index"]
            if node_id in node_ids:
                errors.append(f"Duplicate node_id {node_id} found in nodes '{node_ids[node_id]}' and '{node_name}'")
            node_ids[node_id] = node_name
            node_ids_reverse[node_id] = node_name

    # Step 3: Node validation
    for node_name, node_data in nodes.items():
        # Validate type field
        node_type = node_data.get("type")
        if not node_type:
            errors.append(f"Node '{node_name}' is missing 'type' field")
            continue

        # Validate inputs
        if "inputs" not in node_data:
            errors.append(f"Node '{node_name}' is missing 'inputs' field")
            continue

        if not isinstance(node_data["inputs"], dict):
            errors.append(f"Node '{node_name}' 'inputs' must be a dictionary, got {type(node_data['inputs']).__name__}")
            continue

        # Validate outputs
        if "outputs" not in node_data:
            errors.append(f"Node '{node_name}' is missing 'outputs' field")
            continue

        if not isinstance(node_data["outputs"], list):
            errors.append(f"Node '{node_name}' 'outputs' must be a list, got {type(node_data['outputs']).__name__}")
            continue
        
        # Step 3.5: Validate node definition against node_info (if available)
        if node_info:
            definition_errors = _validate_lite_node_definition(node_name, node_data, node_info)
            errors.extend(definition_errors)

    # Step 4: Connection validation
    for node_name, node_data in nodes.items():
        inputs = node_data.get("inputs", {})

        for input_name, input_value in inputs.items():
            if isinstance(input_value, dict):
                # It's a connection
                if "node_id" not in input_value:
                    errors.append(f"Node '{node_name}' input '{input_name}' connection missing 'node_id'")
                    continue

                if "output_name" not in input_value:
                    errors.append(f"Node '{node_name}' input '{input_name}' connection missing 'output_name'")
                    continue

                source_id = input_value["node_id"]
                output_name = input_value["output_name"]

                # Check source node exists
                if source_id not in node_ids_reverse:
                    errors.append(f"Node '{node_name}' input '{input_name}' references unknown node_id '{source_id}'")
                    continue

                # Check output exists in source node
                source_node_name = node_ids_reverse[source_id]
                source_node = nodes[source_node_name]
                source_outputs = source_node.get("outputs", [])

                if output_name and output_name not in source_outputs:
                    errors.append(f"Node '{node_name}' input '{input_name}' references unknown output '{output_name}' in node '{source_node_name}'")
                    continue

                # Type compatibility check (if node_info available)
                if node_info and output_name:
                    type_errors = _validate_lite_connection_types(
                        node_name, input_name, node_data,
                        source_node_name, output_name, source_node,
                        node_info
                    )
                    errors.extend(type_errors)

    # Step 5: Check for orphan nodes (no connections in or out)
    connected_nodes = set()
    for node_name, node_data in nodes.items():
        inputs = node_data.get("inputs", {})
        for input_value in inputs.values():
            if isinstance(input_value, dict) and "node_id" in input_value:
                source_id = input_value["node_id"]
                connected_nodes.add(node_name)
                if source_id in node_ids_reverse:
                    connected_nodes.add(node_ids_reverse[source_id])

    orphan_nodes = [name for name in nodes.keys() if name not in connected_nodes and len(nodes) > 1]
    if orphan_nodes:
        errors.append(f"Warning: Orphan nodes found (no connections): {', '.join(orphan_nodes)}")

    # Step 6: Validate version
    version = data.get("version")
    if version != "1.0":
        errors.append(f"Warning: Unknown version '{version}', expected '1.0'")

    is_valid = not any(e for e in errors if not e.startswith("Warning:"))
    return is_valid, errors


def validate_standard_format(
    data: Dict[str, Any],
    node_info: Optional[Dict] = None,
    strict: bool = False
) -> Tuple[bool, List[str]]:
    """
    Validate workflow in standard format.

    Comprehensive validation including:
    1. Schema validation
    2. Node validation
    3. Link validation
    4. Type compatibility

    Args:
        data: Workflow dictionary in standard format
        node_info: Optional node information for type validation
        strict: If True, raise exception on first error

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Step 1: Schema validation
    schema_errors = _validate_standard_schema(data)
    errors.extend(schema_errors)

    if errors and strict:
        raise SchemaValidationError(f"Schema validation failed: {errors[0]}")

    nodes = data.get("nodes", [])
    links = data.get("links", [])

    # Step 2: Build mappings
    try:
        node_map = _build_node_map(nodes)
        link_map = _build_link_map(links)
    except Exception as e:
        errors.append(f"Failed to build mappings: {str(e)}")
        if strict:
            raise SchemaValidationError(str(e))
        return False, errors

    # Step 3: Node validation
    node_errors = _validate_nodes(nodes, node_map, node_info)
    errors.extend(node_errors)

    # Step 4: Link validation
    link_errors = _validate_links(links, node_map, link_map, node_info)
    errors.extend(link_errors)

    # Step 5: Type compatibility validation
    if node_info:
        type_errors = _validate_type_compatibility(data, node_map, link_map, node_info)
        errors.extend(type_errors)
        
        # Step 5.5: Validate widgets_values order (if node_info available)
        widgets_order_errors = []
        for node in nodes:
            order_errors = _validate_widgets_values_order(node, node_info)
            widgets_order_errors.extend(order_errors)
        errors.extend(widgets_order_errors)

    # Step 6: Business logic validation
    business_errors = _validate_business_logic(data, node_map, link_map)
    errors.extend(business_errors)

    is_valid = not any(e for e in errors if not e.startswith("Warning:"))
    return is_valid, errors


# ============================================================================
# Schema Validation
# ============================================================================

def _validate_schema(workflow: Dict[str, Any]) -> List[str]:
    """Validate standard workflow schema."""
    errors = []

    # Check required top-level fields
    required_fields = ["id", "nodes", "links"]
    for field in required_fields:
        if field not in workflow:
            errors.append(f"Missing required field: '{field}'")

    # Validate workflow ID (should be UUID or string)
    if "id" in workflow:
        workflow_id = workflow["id"]
        if not isinstance(workflow_id, str):
            errors.append(f"Workflow 'id' must be a string, got {type(workflow_id).__name__}")
        elif workflow_id != "workflow" and not _is_valid_uuid(workflow_id):
            errors.append(f"Warning: Workflow 'id' should be a UUID format, got '{workflow_id}'")

    # Validate nodes is a list
    if "nodes" in workflow:
        nodes = workflow["nodes"]
        if not isinstance(nodes, list):
            errors.append(f"'nodes' must be a list, got {type(nodes).__name__}")

    # Validate links is a list
    if "links" in workflow:
        links = workflow["links"]
        if not isinstance(links, list):
            errors.append(f"'links' must be a list, got {type(links).__name__}")

    return errors


def _validate_lite_schema(data: Dict[str, Any]) -> List[str]:
    """Validate lite workflow schema."""
    errors = []

    # Check required top-level fields
    required_fields = ["version", "nodes"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")

    # Validate version
    if "version" in data:
        version = data["version"]
        if not isinstance(version, str):
            errors.append(f"'version' must be a string, got {type(version).__name__}")
        elif version != "1.0":
            errors.append(f"Warning: Unknown version '{version}', expected '1.0'")

    # Validate nodes is a dict
    if "nodes" in data:
        nodes = data["nodes"]
        if not isinstance(nodes, dict):
            errors.append(f"'nodes' must be a dictionary, got {type(nodes).__name__}")

    return errors


def _validate_standard_schema(data: Dict[str, Any]) -> List[str]:
    """Validate standard format schema (alias for consistency)."""
    return _validate_schema(data)


# ============================================================================
# Node Validation
# ============================================================================

def _validate_nodes(nodes: List[Dict], node_map: Dict[int, Dict], node_info: Optional[Dict] = None) -> List[str]:
    """Validate nodes structure and content."""
    errors = []

    for node in nodes:
        node_id = node.get("id")
        if node_id is None:
            errors.append("Found node without 'id' field")
            continue

        # Validate type
        node_type = node.get("type")
        if not node_type:
            errors.append(f"Node {node_id} is missing 'type' field")
        elif not isinstance(node_type, str):
            errors.append(f"Node {node_id} 'type' must be a string, got {type(node_type).__name__}")

        # Validate inputs
        if "inputs" in node:
            inputs = node["inputs"]
            if not isinstance(inputs, list):
                errors.append(f"Node {node_id} 'inputs' must be a list, got {type(inputs).__name__}")
            else:
                for idx, inp in enumerate(inputs):
                    if not isinstance(inp, dict):
                        errors.append(f"Node {node_id} input at index {idx} must be a dictionary")
                        continue

                    if "name" not in inp:
                        errors.append(f"Node {node_id} input at index {idx} is missing 'name' field")

                    if "type" not in inp:
                        errors.append(f"Node {node_id} input '{inp.get('name', idx)}' is missing 'type' field")

        # Validate outputs
        if "outputs" in node:
            outputs = node["outputs"]
            if not isinstance(outputs, list):
                errors.append(f"Node {node_id} 'outputs' must be a list, got {type(outputs).__name__}")
            else:
                for idx, out in enumerate(outputs):
                    if not isinstance(out, dict):
                        errors.append(f"Node {node_id} output at index {idx} must be a dictionary")
                        continue

                    if "name" not in out:
                        errors.append(f"Node {node_id} output at index {idx} is missing 'name' field")

                    if "type" not in out:
                        errors.append(f"Node {node_id} output '{out.get('name', idx)}' is missing 'type' field")

                    # Validate links field
                    if "links" in out and not isinstance(out["links"], list):
                        errors.append(f"Node {node_id} output '{out.get('name')}' 'links' must be a list")

        # Validate widgets_values
        if "widgets_values" in node:
            widgets_values = node["widgets_values"]
            if not isinstance(widgets_values, list):
                errors.append(f"Node {node_id} 'widgets_values' must be a list, got {type(widgets_values).__name__}")

    return errors


def _is_widgetable_type(param_type: str) -> bool:
    """
    Check if parameter type is widget-able (primitive type that can be displayed as a widget).
    
    Widget-able types are primitive types that can be directly edited in the UI:
    - STRING, INT, FLOAT, BOOLEAN, COMBO
    
    Non-widget types are complex objects that require connections:
    - MODEL, VAE, CLIP, CONDITIONING, LATENT, IMAGE, etc.
    
    Args:
        param_type: Parameter type string (e.g., "STRING", "MODEL", "INT")
        
    Returns:
        True if the type is widget-able, False otherwise
    """
    widgetable_types = {"STRING", "INT", "FLOAT", "BOOLEAN", "COMBO"}
    return param_type in widgetable_types


def _validate_widgets_values_order(
    node: Dict,
    node_info: Optional[Dict] = None
) -> List[str]:
    """
    Validate widgets_values order and content correctness.
    
    Rules:
    1. widgets_values should contain all required parameters
    2. widgets_values should contain optional parameters that have links
    3. Order: required first (widget-able types first, then non-widget), 
       then optional (widget-able types first, then non-widget)
    
    Args:
        node: Node dictionary from standard workflow
        node_info: Optional node information for validation
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if "widgets_values" not in node:
        return errors
    
    if not node_info:
        # Cannot validate without node_info
        return errors
    
    node_type = node.get("type")
    if not node_type or node_type not in node_info:
        return errors
    
    widgets_values = node["widgets_values"]
    node_def = node_info[node_type]
    input_defs = node_def.get("input", {})
    required_params = input_defs.get("required", {})
    optional_params = input_defs.get("optional", {})
    
    # Get inputs array to determine which optional params have links
    inputs_array = node.get("inputs", [])
    connected_input_names = set()
    for inp in inputs_array:
        if isinstance(inp, dict) and inp.get("link") is not None:
            connected_input_names.add(inp.get("name"))
    
    # Helper to get parameter type
    def get_param_type(param_name: str, param_def: Any) -> str:
        if isinstance(param_def, list) and len(param_def) > 0:
            first_elem = param_def[0]
            if isinstance(first_elem, str):
                return first_elem
            elif isinstance(first_elem, list):
                return "COMBO"
        return "STRING"
    
    # Build expected order
    expected_order = []
    
    # Required: widget-able first (maintain original order)
    for param_name, param_def in required_params.items():
        param_type = get_param_type(param_name, param_def)
        if _is_widgetable_type(param_type):
            expected_order.append((param_name, param_type, True))
    
    # Required: non-widget (maintain original order)
    for param_name, param_def in required_params.items():
        param_type = get_param_type(param_name, param_def)
        if not _is_widgetable_type(param_type):
            expected_order.append((param_name, param_type, True))
    
    # Optional with links: widget-able first (maintain original order)
    for param_name, param_def in optional_params.items():
        if param_name in connected_input_names:
            param_type = get_param_type(param_name, param_def)
            if _is_widgetable_type(param_type):
                expected_order.append((param_name, param_type, False))
    
    # Optional with links: non-widget (maintain original order)
    for param_name, param_def in optional_params.items():
        if param_name in connected_input_names:
            param_type = get_param_type(param_name, param_def)
            if not _is_widgetable_type(param_type):
                expected_order.append((param_name, param_type, False))
    
    # Validate count
    if len(widgets_values) != len(expected_order):
        errors.append(
            f"Node {node.get('id')} 'widgets_values' has incorrect count: "
            f"expected {len(expected_order)} (required: {len(required_params)}, "
            f"optional with links: {len([p for p in optional_params.keys() if p in connected_input_names])}), "
            f"got {len(widgets_values)}"
        )
    
    # Note: We don't validate the exact order here as it's complex and may vary
    # The converter is responsible for generating correct order
    
    return errors


# ============================================================================
# Link Validation
# ============================================================================

def _validate_links(
    links: List[List],
    node_map: Dict[int, Dict],
    link_map: Dict[int, Tuple],
    node_info: Optional[Dict] = None
) -> List[str]:
    """Validate links structure and relationships."""
    errors = []
    link_ids = set()

    for link in links:
        # Validate link format
        if len(link) < 6:
            errors.append(f"Link {link} has invalid format (expected 6 elements, got {len(link)})")
            continue

        link_id, source_id, source_idx, target_id, target_idx, link_type = link[:6]

        # Validate link_id uniqueness
        if link_id in link_ids:
            errors.append(f"Duplicate link_id {link_id} found")
        link_ids.add(link_id)

        # Validate source node exists
        if source_id not in node_map:
            errors.append(f"Link {link_id} references unknown source node {source_id}")
            continue

        # Validate target node exists
        if target_id not in node_map:
            errors.append(f"Link {link_id} references unknown target node {target_id}")
            continue

        # Validate source output exists
        source_node = node_map[source_id]
        source_outputs = source_node.get("outputs", [])
        if source_idx >= len(source_outputs):
            errors.append(
                f"Link {link_id} references invalid source output index {source_idx} "
                f"(node {source_id} has {len(source_outputs)} outputs)"
            )
            continue

        # Validate target input exists
        target_node = node_map[target_id]
        target_inputs = target_node.get("inputs", [])
        if target_idx >= len(target_inputs):
            errors.append(
                f"Link {link_id} references invalid target input index {target_idx} "
                f"(node {target_id} has {len(target_inputs)} inputs)"
            )
            continue

        # Validate link type matches source output type
        source_output = source_outputs[source_idx]
        source_output_type = source_output.get("type", "AUTO")
        if link_type != source_output_type and link_type != "AUTO" and source_output_type != "*":
            errors.append(
                f"Link {link_id} type mismatch: link type is '{link_type}' "
                f"but source output type is '{source_output_type}'"
            )

        # Validate link type is compatible with target input type
        target_input = target_inputs[target_idx]
        target_input_type = target_input.get("type", "AUTO")
        if link_type != target_input_type and link_type != "AUTO" and target_input_type != "*":
            # Allow some type conversions
            if not _is_type_compatible(link_type, target_input_type):
                errors.append(
                    f"Link {link_id} type incompatibility: link type '{link_type}' "
                    f"is not compatible with target input type '{target_input_type}'"
                )

    return errors


def _validate_lite_node_definition(
    node_name: str,
    node_data: Dict,
    node_info: Dict
) -> List[str]:
    """
    Validate node definition against node_info for lite format.
    
    Checks:
    1. Node type exists in node_info
    2. Required parameters are present
    3. Input parameters exist in node_info
    4. Output names match node_info (if defined)
    
    Args:
        node_name: Node name
        node_data: Node data dictionary
        node_info: Node information dictionary
        
    Returns:
        List of error messages
    """
    errors = []
    node_type = node_data.get("type")
    
    if not node_type:
        return errors
    
    # Check if node type exists in node_info
    if node_type not in node_info:
        errors.append(f"Node '{node_name}' has unknown type '{node_type}' (not found in node_info)")
        return errors
    
    node_def = node_info[node_type]
    input_defs = node_def.get("input", {})
    required_params = input_defs.get("required", {})
    optional_params = input_defs.get("optional", {})
    all_params = {**required_params, **optional_params}
    
    # Get node inputs
    node_inputs = node_data.get("inputs", {})
    
    # Check required parameters are present
    for param_name in required_params.keys():
        if param_name not in node_inputs:
            errors.append(
                f"Node '{node_name}' (type '{node_type}') is missing required parameter '{param_name}'"
            )
    
    # Check that all input parameters exist in node_info
    for input_name in node_inputs.keys():
        if input_name not in all_params:
            errors.append(
                f"Node '{node_name}' (type '{node_type}') has unknown input parameter '{input_name}' "
                f"(not defined in node_info)"
            )
    
    # Check outputs (if node_info defines output names)
    node_outputs = node_data.get("outputs", [])
    expected_output_names = node_def.get("output_name", [])
    
    if expected_output_names:
        # If node_info defines output names, check they match
        if len(node_outputs) != len(expected_output_names):
            errors.append(
                f"Node '{node_name}' (type '{node_type}') has {len(node_outputs)} outputs, "
                f"but node_info expects {len(expected_output_names)} outputs: {expected_output_names}"
            )
        else:
            # Check each output name matches
            for i, output_name in enumerate(node_outputs):
                if i < len(expected_output_names):
                    expected_name = expected_output_names[i]
                    if output_name != expected_name:
                        errors.append(
                            f"Node '{node_name}' (type '{node_type}') output[{i}] is '{output_name}', "
                            f"but node_info expects '{expected_name}'"
                        )
    
    return errors


def _validate_standard_node_definition(
    node_id: int,
    node: Dict,
    node_info: Dict
) -> List[str]:
    """
    Validate node definition against node_info for standard format.
    
    Checks:
    1. Node type exists in node_info
    2. Required parameters are present (in inputs array or widgets_values)
    3. Input parameters exist in node_info
    4. Output names match node_info (if defined)
    
    Args:
        node_id: Node ID
        node: Node dictionary
        node_info: Node information dictionary
        
    Returns:
        List of error messages
    """
    errors = []
    node_type = node.get("type")
    
    if not node_type:
        return errors
    
    # Check if node type exists in node_info
    if node_type not in node_info:
        errors.append(f"Node {node_id} has unknown type '{node_type}' (not found in node_info)")
        return errors
    
    node_def = node_info[node_type]
    input_defs = node_def.get("input", {})
    required_params = input_defs.get("required", {})
    optional_params = input_defs.get("optional", {})
    all_params = {**required_params, **optional_params}
    
    # Get node inputs (from inputs array)
    inputs_array = node.get("inputs", [])
    node_input_names = set()
    for inp in inputs_array:
        if isinstance(inp, dict) and "name" in inp:
            node_input_names.add(inp["name"])
    
    # Check required parameters are present
    for param_name in required_params.keys():
        if param_name not in node_input_names:
            errors.append(
                f"Node {node_id} (type '{node_type}') is missing required parameter '{param_name}' "
                f"(not found in inputs array)"
            )
    
    # Check that all input parameters exist in node_info
    for input_name in node_input_names:
        if input_name not in all_params:
            errors.append(
                f"Node {node_id} (type '{node_type}') has unknown input parameter '{input_name}' "
                f"(not defined in node_info)"
            )
    
    # Check outputs (if node_info defines output names)
    outputs_array = node.get("outputs", [])
    expected_output_names = node_def.get("output_name", [])
    
    if expected_output_names:
        # If node_info defines output names, check they match
        node_output_names = [out.get("name") for out in outputs_array if isinstance(out, dict) and "name" in out]
        
        if len(node_output_names) != len(expected_output_names):
            errors.append(
                f"Node {node_id} (type '{node_type}') has {len(node_output_names)} outputs, "
                f"but node_info expects {len(expected_output_names)} outputs: {expected_output_names}"
            )
        else:
            # Check each output name matches
            for i, output_name in enumerate(node_output_names):
                if i < len(expected_output_names):
                    expected_name = expected_output_names[i]
                    if output_name != expected_name:
                        errors.append(
                            f"Node {node_id} (type '{node_type}') output[{i}] is '{output_name}', "
                            f"but node_info expects '{expected_name}'"
                        )
    
    return errors


def _validate_lite_connection_types(
    target_node_name: str,
    target_input_name: str,
    target_node: Dict,
    source_node_name: str,
    source_output_name: str,
    source_node: Dict,
    node_info: Dict
) -> List[str]:
    """Validate type compatibility for lite format connections."""
    errors = []

    target_node_type = target_node.get("type")
    source_node_type = source_node.get("type")

    # Get target input type from node_info
    target_input_type = None
    if target_node_type in node_info:
        input_defs = node_info[target_node_type].get("input", {})
        for category in ["required", "optional"]:
            if category in input_defs and target_input_name in input_defs[category]:
                param_def = input_defs[category][target_input_name]
                if isinstance(param_def, list) and len(param_def) > 0:
                    target_input_type = param_def[0]
                    if isinstance(target_input_type, list):
                        target_input_type = "STRING"  # Enum type
                break

    # Get source output type from node_info
    source_output_type = None
    if source_node_type in node_info:
        output_types = node_info[source_node_type].get("output", [])
        output_names = node_info[source_node_type].get("output_name", [])

        if source_output_name in output_names:
            name_idx = output_names.index(source_output_name)
            if name_idx < len(output_types):
                source_output_type = output_types[name_idx]
        elif len(output_types) > 0:
            source_output_type = output_types[0]  # Use first output as fallback

    # Check compatibility
    if target_input_type and source_output_type:
        if not _is_type_compatible(source_output_type, target_input_type):
            errors.append(
                f"Type incompatibility: {source_node_name}.{source_output_name} ({source_output_type}) "
                f"-> {target_node_name}.{target_input_name} ({target_input_type})"
            )

    return errors


# ============================================================================
# Type Compatibility Validation
# ============================================================================

def _validate_type_compatibility(
    workflow: Dict,
    node_map: Dict[int, Dict],
    link_map: Dict,
    node_info: Dict
) -> List[str]:
    """Validate type compatibility across all connections."""
    errors = []

    for link in workflow.get("links", []):
        if len(link) < 6:
            continue

        link_id, source_id, source_idx, target_id, target_idx, link_type = link[:6]

        if source_id not in node_map or target_id not in node_map:
            continue

        source_node = node_map[source_id]
        target_node = node_map[target_id]
        source_node_type = source_node.get("type")
        target_node_type = target_node.get("type")

        # Skip if node types not in node_info
        if source_node_type not in node_info or target_node_type not in node_info:
            continue

        # Get expected types from node_info
        source_outputs = node_info[source_node_type].get("output", [])
        target_inputs = node_info[target_node_type].get("input", {})

        if source_idx >= len(source_outputs):
            continue

        source_expected_type = source_outputs[source_idx]

        # Get target input definition
        target_input_name = None
        target_inputs_list = target_node.get("inputs", [])
        if target_idx < len(target_inputs_list):
            target_input_name = target_inputs_list[target_idx].get("name")

        target_expected_type = "AUTO"
        if target_input_name:
            for category in ["required", "optional"]:
                if category in target_inputs and target_input_name in target_inputs[category]:
                    param_def = target_inputs[category][target_input_name]
                    if isinstance(param_def, list) and len(param_def) > 0:
                        target_expected_type = param_def[0]
                        if isinstance(target_expected_type, list):
                            target_expected_type = "STRING"
                    break

        # Validate type compatibility
        if not _is_type_compatible(source_expected_type, target_expected_type):
            errors.append(
                f"Link {link_id}: Type mismatch between source ({source_expected_type}) "
                f"and target ({target_expected_type})"
            )

    return errors


def _is_type_compatible(source_type: str, target_type: str) -> bool:
    """Check if source type is compatible with target type."""
    # Same types are always compatible
    if source_type == target_type:
        return True

    # AUTO is compatible with everything
    if source_type == "AUTO" or target_type == "AUTO":
        return True

    # Wildcard types
    if source_type == "*" or target_type == "*":
        return True

    # COMBO can be used as STRING
    if source_type == "COMBO" and target_type == "STRING":
        return True
    if source_type == "STRING" and target_type == "COMBO":
        return True

    # Model types
    model_types = ["MODEL", "VAE", "LATENT", "CLIP", "STYLE_MODEL"]
    if source_type in model_types and target_type in model_types:
        return True

    # Number types
    number_types = ["INT", "FLOAT", "NUMBER"]
    if source_type in number_types and target_type in number_types:
        return True

    return False


# ============================================================================
# Business Logic Validation
# ============================================================================

def _validate_business_logic(
    workflow: Dict,
    node_map: Dict[int, Dict],
    link_map: Dict
) -> List[str]:
    """Validate business logic rules."""
    errors = []

    # Check for orphan nodes (no connections in or out)
    connected_nodes = set()

    for link in workflow.get("links", []):
        if len(link) >= 6:
            _, source_id, _, target_id, _, _ = link[:6]
            connected_nodes.add(source_id)
            connected_nodes.add(target_id)

    orphan_nodes = [
        node_id for node_id in node_map.keys()
        if node_id not in connected_nodes and len(node_map) > 1
    ]

    if orphan_nodes:
        errors.append(f"Warning: Orphan nodes found (no connections): {orphan_nodes}")

    # Check for self-loops (nodes that connect to themselves)
    for link in workflow.get("links", []):
        if len(link) >= 6:
            link_id, source_id, _, target_id, _, _ = link[:6]
            if source_id == target_id:
                errors.append(f"Warning: Link {link_id} is a self-loop (node {source_id} connects to itself)")

    # Check for cycles (detect circular dependencies)
    cycles = _detect_cycles(node_map, link_map)
    if cycles:
        errors.append(f"Warning: Circular dependencies detected: {cycles}")

    # Check last_node_id and last_link_id consistency
    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])

    if nodes:
        max_node_id = max(node.get("id", 0) for node in nodes)
        if workflow.get("last_node_id", 0) < max_node_id:
            errors.append(
                f"Warning: last_node_id ({workflow.get('last_node_id')}) "
                f"is less than max node_id ({max_node_id})"
            )

    if links:
        max_link_id = max(link[0] for link in links if len(link) > 0)
        if workflow.get("last_link_id", 0) < max_link_id:
            errors.append(
                f"Warning: last_link_id ({workflow.get('last_link_id')}) "
                f"is less than max link_id ({max_link_id})"
            )

    return errors


def _detect_cycles(
    node_map: Dict[int, Dict],
    link_map: Dict
) -> List[List[int]]:
    """Detect circular dependencies using DFS."""
    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(node_id: int, path: List[int]) -> bool:
        """DFS to detect cycles."""
        visited.add(node_id)
        rec_stack.add(node_id)
        path.append(node_id)

        # Check all outgoing links from this node
        for link in link_map.values():
            _, source_id, _, target_id, _, _ = link
            if source_id == node_id:
                if target_id not in visited:
                    if dfs(target_id, path):
                        return True
                elif target_id in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(target_id)
                    cycle = path[cycle_start:] + [target_id]
                    cycles.append(cycle)
                    return True

        path.pop()
        rec_stack.remove(node_id)
        return False

    for node_id in node_map.keys():
        if node_id not in visited:
            if dfs(node_id, []):
                break

    return cycles


# ============================================================================
# Helper Functions
# ============================================================================

def _build_node_map(nodes: List[Dict]) -> Dict[int, Dict]:
    """Build mapping from node ID to node data."""
    node_map = {}
    for node in nodes:
        node_id = node.get("id")
        if node_id is not None:
            node_map[node_id] = node
    return node_map


def _build_link_map(links: List[List]) -> Dict[int, Tuple]:
    """Build mapping from link ID to link data."""
    link_map = {}
    for link in links:
        if len(link) >= 6:
            link_id = link[0]
            link_map[link_id] = tuple(link[:6])
    return link_map


def _is_valid_uuid(id_string: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(id_string)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


# ============================================================================
# Legacy Functions (for backward compatibility)
# ============================================================================

def validate_workflow_lite(
    data: Dict[str, Any],
    node_info: Optional[Dict] = None
) -> bool:
    """
    Legacy function to validate lite format.

    Deprecated: Use validate_lite_format() instead.
    """
    is_valid, errors = validate_lite_format(data, node_info)
    for error in errors:
        if not error.startswith("Warning:"):
            print(f"✗ {error}")
        else:
            print(f"⚠ {error}")

    if is_valid:
        print(f"✓ Lite format validation passed ({len(data.get('nodes', {}))} nodes)")
    else:
        print("✗ Lite format validation failed")

    return is_valid


def validate_workflow_standard(
    data: Dict[str, Any],
    node_info: Optional[Dict] = None
) -> bool:
    """
    Legacy function to validate standard format.

    Deprecated: Use validate_standard_format() instead.
    """
    is_valid, errors = validate_standard_format(data, node_info)
    for error in errors:
        if not error.startswith("Warning:"):
            print(f"✗ {error}")
        else:
            print(f"⚠ {error}")

    if is_valid:
        print(f"✓ Standard format validation passed ({len(data.get('nodes', []))} nodes, {len(data.get('links', []))} links)")
    else:
        print("✗ Standard format validation failed")

    return is_valid


# Legacy function for backward compatibility (renamed to avoid conflict)
def validate_workflow_legacy(
    workflow: dict,
    client,
    node_info: Optional[Dict] = None
) -> Tuple[bool, List[str]]:
    """
    Legacy validate workflow function (backward compatibility).

    This function wraps the new validate_workflow function.
    """
    return validate_workflow(workflow, client, node_info)
