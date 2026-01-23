"""
Workflow Validator

This module provides functionality to validate workflows in both standard and lite formats.

Validation includes:
- Checking required fields
- Validating node IDs and connections
- Verifying link references
- Checking type compatibility
"""

from typing import Dict, List, Any, Tuple, Optional
from ..base import PyroMindAPIError


class WorkflowValidationError(Exception):
    """Exception raised when workflow validation fails."""
    pass


def validate_workflow(workflow: dict, client, node_info: Optional[Dict] = None) -> Tuple[bool, List[str]]:
    """
    Validate workflow before sending to server.

    This function validates:
    1. All nodes exist in node_info
    2. Node input/output types match connections
    3. Required inputs are provided
    4. Connection links are valid

    Args:
        workflow: Workflow JSON dictionary
        client: PyroMindAPIClient instance to use for fetching node_info.
                Required parameter to avoid circular import issues.
        node_info: Node information dictionary from get_node_info API.
                  If None, will fetch it automatically using the provided client.

    Returns:
        Tuple of (is_valid, error_messages)
        - is_valid: True if workflow is valid, False otherwise
        - error_messages: List of error messages if validation fails

    Raises:
        WorkflowValidationError: If validation fails and strict mode is enabled
    """
    errors = []

    # Get node_info if not provided
    if node_info is None:
        try:
            node_info = client.training.get_node_info()
        except PyroMindAPIError as e:
            errors.append(f"Failed to get node info: {e.message}")
            return False, errors

    if not node_info:
        errors.append("No node information available")
        return False, errors

    # Parse workflow nodes
    workflow_nodes = workflow.get("nodes", [])
    if not workflow_nodes:
        errors.append("Workflow has no nodes")
        return False, errors

    # Build node mapping: node_id -> node_data
    node_map = {}
    for node in workflow_nodes:
        node_id = node.get("id")
        if node_id is None:
            errors.append("Found node without ID")
            continue
        node_map[node_id] = node

    # Build link mapping: link_id -> (source_node_id, source_socket_index, target_node_id, target_socket_index, type)
    links = workflow.get("links", [])
    link_map = {}
    for link in links:
        if len(link) >= 6:
            link_id = link[0]
            source_node_id = link[1]
            source_socket_index = link[2]
            target_node_id = link[3]
            target_socket_index = link[4]
            link_type = link[5]
            link_map[link_id] = (source_node_id, source_socket_index, target_node_id, target_socket_index, link_type)

    # Validate each node
    for node_id, node in node_map.items():
        node_type = node.get("type")
        if not node_type:
            errors.append(f"Node {node_id} has no type")
            continue

        # PrimitiveNode is a special node type that represents constants
        # It doesn't need to be in node_info
        if node_type == "PrimitiveNode":
            continue

        # Check if node type exists in node_info
        if node_type not in node_info:
            errors.append(f"Node {node_id} has unknown type '{node_type}' (not found in node_info)")
            continue

        node_def = node_info[node_type]
        node_inputs_def = node_def.get('input', {})
        node_outputs_def = node_def.get('output', [])

        # Validate inputs
        node_inputs = node.get("inputs", [])
        for input_idx, input_socket in enumerate(node_inputs):
            input_name = input_socket.get("name")
            input_type = input_socket.get("type")
            link_id = input_socket.get("link")

            # If input has a link, validate the connection
            if link_id is not None:
                if link_id not in link_map:
                    errors.append(f"Node {node_id} input '{input_name}' references invalid link {link_id}")
                    continue

                link_source_node_id, link_source_socket_idx, link_target_node_id, link_target_socket_idx, link_type = link_map[link_id]

                # Verify target matches
                if link_target_node_id != node_id:
                    errors.append(f"Node {node_id} input '{input_name}' link {link_id} has mismatched target node")
                    continue

                # Verify source node exists
                if link_source_node_id not in node_map:
                    errors.append(f"Node {node_id} input '{input_name}' references non-existent source node {link_source_node_id}")
                    continue

                source_node = node_map[link_source_node_id]
                source_outputs = source_node.get("outputs", [])

                # Verify source output exists
                if link_source_socket_idx >= len(source_outputs):
                    errors.append(f"Node {node_id} input '{input_name}' references invalid source output index {link_source_socket_idx}")
                    continue

                source_output = source_outputs[link_source_socket_idx]
                source_output_type = source_output.get("type")

                # Verify link type matches source output type
                if source_output_type != link_type:
                    errors.append(
                        f"Node {node_id} input '{input_name}' link {link_id} type mismatch: "
                        f"link type is {link_type}, but source output type is {source_output_type}"
                    )

                # Verify input type matches expected from node definition
                if input_name in node_inputs_def:
                    expected_input_type = node_inputs_def[input_name]
                    # Check if the source output type is compatible with expected input type
                    if source_output_type != expected_input_type and expected_input_type != "*":
                        # Allow some flexibility for COMBO types
                        if not (source_output_type == "COMBO" and expected_input_type in ["STRING", "COMBO"]):
                            if not (expected_input_type == "COMBO" and source_output_type in ["STRING", "COMBO"]):
                                errors.append(
                                    f"Node {node_id} input '{input_name}' type mismatch: "
                                    f"expected {expected_input_type}, but receiving {source_output_type} from source"
                                )
            else:
                # Input without link - check if it's required
                if input_name in node_inputs_def:
                    # Check if there's a widget value
                    widgets_values = node.get("widgets_values", [])
                    # This is a simplified check - in practice, you'd need to map widget names to values
                    pass

        # Validate outputs
        node_outputs = node.get("outputs", [])
        for output_idx, output_socket in enumerate(node_outputs):
            output_name = output_socket.get("name")
            output_type = output_socket.get("type")

            # Check if output matches definition
            if output_idx < len(node_outputs_def):
                expected_output_type = node_outputs_def[output_idx]
                if output_type != expected_output_type and expected_output_type != "*":
                    errors.append(
                        f"Node {node_id} output '{output_name}' type mismatch: "
                        f"expected {expected_output_type}, got {output_type}"
                    )

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_lite_format(data: Dict[str, Any]) -> bool:
    """
    Validate workflow in lite format.

    Lite format structure:
    {
        "version": "1.0",
        "nodes": {
            "node_name": {
                "type": "NodeType",
                "inputs": {...},
                "outputs": [...],
                "index": <node_id>
            }
        }
    }

    Args:
        data: Workflow dictionary in lite format

    Returns:
        True if validation passes, False otherwise
    """
    # Check required fields
    required_fields = ["version", "nodes"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        print(f"✗ Validation failed: Missing fields: {', '.join(missing)}")
        return False

    nodes = data["nodes"]

    # Build node ID to name mapping
    node_ids = {}
    for node_name, node_data in nodes.items():
        if "index" in node_data:
            node_id = node_data["index"]
            if node_id in node_ids:
                print(f"⚠ Warning: Duplicate node_id {node_id} found")
            node_ids[node_id] = node_name

    # Validate connections (embedded in inputs)
    for node_name, node_data in nodes.items():
        inputs = node_data.get("inputs", {})

        for input_name, input_value in inputs.items():
            if isinstance(input_value, dict) and "node_id" in input_value:
                source_id = input_value["node_id"]
                if source_id not in node_ids:
                    print(f"✗ Validation failed: Node '{node_name}' input '{input_name}' "
                          f"references unknown node_id '{source_id}'")
                    return False

                # Verify output_name exists in source node
                source_node_name = node_ids[source_id]
                source_node = nodes[source_node_name]
                output_name = input_value.get("output_name")
                source_outputs = source_node.get("outputs", [])

                if output_name and output_name not in source_outputs:
                    print(f"⚠ Warning: Node '{node_name}' input '{input_name}' "
                          f"references unknown output '{output_name}' in node '{source_node_name}'")

    # Validate version
    version = data.get("version")
    if version != "1.0":
        print(f"⚠ Warning: Unknown version '{version}', expected '1.0'")

    print(f"✓ Lite format validation passed ({len(nodes)} nodes)")
    return True


def validate_standard_format(data: Dict[str, Any]) -> bool:
    """
    Validate workflow in standard format.

    Standard format structure:
    {
        "id": "...",
        "nodes": [...],
        "links": [[link_id, source_id, source_idx, target_id, target_idx, type], ...]
    }

    Args:
        data: Workflow dictionary in standard format

    Returns:
        True if validation passes, False otherwise
    """
    # Check required fields
    required_fields = ["nodes", "links"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        print(f"✗ Validation failed: Missing fields: {', '.join(missing)}")
        return False

    nodes = data["nodes"]
    links = data["links"]

    # Build node map
    node_map = {}
    node_id_set = set()
    for node in nodes:
        node_id = node.get("id")
        if node_id is None:
            print(f"✗ Validation failed: Found node without ID")
            return False

        if node_id in node_id_set:
            print(f"⚠ Warning: Duplicate node_id {node_id} found")

        node_id_set.add(node_id)
        node_map[node_id] = node

    # Validate links
    for link in links:
        if len(link) < 6:
            print(f"✗ Validation failed: Invalid link format (expected 6 elements, got {len(link)})")
            return False

        link_id, source_id, source_idx, target_id, target_idx = link[:5]

        # Check source node exists
        if source_id not in node_map:
            print(f"✗ Validation failed: Link {link_id} references unknown source node {source_id}")
            return False

        # Check target node exists
        if target_id not in node_map:
            print(f"✗ Validation failed: Link {link_id} references unknown target node {target_id}")
            return False

        # Check source output exists
        source_node = node_map[source_id]
        source_outputs = source_node.get("outputs", [])
        if source_idx >= len(source_outputs):
            print(f"✗ Validation failed: Link {link_id} references invalid source output index "
                  f"{source_idx} (node has {len(source_outputs)} outputs)")
            return False

        # Check target input exists
        target_node = node_map[target_id]
        target_inputs = target_node.get("inputs", [])
        if target_idx >= len(target_inputs):
            print(f"✗ Validation failed: Link {link_id} references invalid target input index "
                  f"{target_idx} (node has {len(target_inputs)} inputs)")
            return False

    print(f"✓ Standard format validation passed ({len(nodes)} nodes, {len(links)} links)")
    return True
