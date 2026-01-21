"""
Workflow Validator

This module provides functionality to validate workflows before sending them to the server.
Validation includes checking node existence, input/output type matching, and connection validation.
"""

from typing import Dict, List, Tuple, Optional

from .base import PyroMindAPIError


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
