"""
Node validation utility

Provides common functionality for validating PodExecutionNode class structure.
"""

from typing import Dict, Any, Tuple
from pyromind_sdk.common.node_sdk import PodExecutionNode


def parse_input_spec(input_spec: Any) -> Tuple[str, Dict[str, Any]]:
    """Parse input type specification
    
    Args:
        input_spec: Input type specification, can be string, list, or tuple
        
    Returns:
        (type_str, config_dict) tuple
    """
    if isinstance(input_spec, (tuple, list)) and len(input_spec) >= 1:
        input_type = input_spec[0]
        input_config = input_spec[1] if len(input_spec) > 1 else {}
        type_str = str(input_type) if not isinstance(input_type, list) else f"CHOICE[{', '.join(map(str, input_type))}]"
        return type_str, input_config
    return "UNKNOWN", {}


def validate_node_class(node_class: type, node_name: str) -> Dict[str, Any]:
    """Validate node class structure
    
    Args:
        node_class: Node class
        node_name: Node name
        
    Returns:
        Dictionary containing validation results:
        - valid: Whether valid
        - errors: Error list
        - warnings: Warning list
        - info: Node information dictionary
    """
    results = {
        "name": node_name,
        "class_name": node_class.__name__,
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": {}
    }
    
    # Check basic attributes
    required_attrs = ["CATEGORY", "RETURN_TYPES", "RETURN_NAMES", "DESCRIPTION"]
    for attr in required_attrs:
        if not hasattr(node_class, attr):
            results["errors"].append(f"Missing required attribute: {attr}")
            results["valid"] = False
        else:
            results["info"][attr.lower()] = getattr(node_class, attr)
    
    results["info"]["base_classes"] = [base.__name__ for base in node_class.__bases__]
    
    # Check PodExecutionNode specific attributes
    if issubclass(node_class, PodExecutionNode):
        results["info"]["node_type"] = "PodExecutionNode"
        
        if hasattr(node_class, "COMMAND_TEMPLATE"):
            command_template = node_class.COMMAND_TEMPLATE
            results["info"]["command_template"] = command_template
            if not command_template:
                results["warnings"].append("COMMAND_TEMPLATE is empty")
            elif not isinstance(command_template, list):
                results["errors"].append("COMMAND_TEMPLATE must be a list")
                results["valid"] = False
        else:
            results["warnings"].append("Missing COMMAND_TEMPLATE for PodExecutionNode")
        
        # Resource limits
        resource_info = {
            attr.lower(): getattr(node_class, attr)
            for attr in ["MEMORY_LIMIT", "CPU_LIMIT", "GPU_MIN_COUNT", "GPU_MAX_COUNT"]
            if hasattr(node_class, attr)
        }
        if resource_info:
            results["info"]["resources"] = resource_info
    
    # Check input types
    if hasattr(node_class, "BASE_INPUT_TYPES"):
        try:
            input_types = node_class.BASE_INPUT_TYPES()
            detailed_inputs = {}
            
            for section in ["required", "optional"]:
                for input_name, input_spec in input_types.get(section, {}).items():
                    type_str, config = parse_input_spec(input_spec)
                    if type_str == "UNKNOWN":
                        results["errors"].append(f"Invalid input type spec for '{input_name}': {input_spec}")
                        results["valid"] = False
                    else:
                        detailed_inputs[input_name] = {
                            "type": type_str,
                            "default": config.get("default", None),
                            "required": section == "required"
                        }
            
            results["info"]["input_types"] = {
                "required": list(input_types.get("required", {}).keys()),
                "optional": list(input_types.get("optional", {}).keys())
            }
            results["info"]["detailed_inputs"] = detailed_inputs
        except Exception as e:
            results["errors"].append(f"Error getting BASE_INPUT_TYPES: {e}")
            results["valid"] = False
    
    # Check INPUT_TYPES (includes resource types)
    if hasattr(node_class, "INPUT_TYPES"):
        try:
            all_input_types = node_class.INPUT_TYPES()
            results["info"]["all_input_types"] = {
                "required": list(all_input_types.get("required", {}).keys()),
                "optional": list(all_input_types.get("optional", {}).keys())
            }
        except Exception as e:
            results["warnings"].append(f"Error getting INPUT_TYPES: {e}")
    
    # Collect output type information
    if hasattr(node_class, "RETURN_TYPES") and hasattr(node_class, "RETURN_NAMES"):
        return_types = getattr(node_class, "RETURN_TYPES", ())
        return_names = getattr(node_class, "RETURN_NAMES", ())
        results["info"]["outputs"] = {
            name: {"type": typ, "index": i}
            for i, (typ, name) in enumerate(zip(return_types, return_names))
        }
    
    # Check CUSTOMER_INPUTS (now includes all customer_use parameters, including inputs and outputs)
    if hasattr(node_class, "CUSTOMER_INPUTS"):
        try:
            customer_use = node_class.CUSTOMER_INPUTS()
            if customer_use:
                results["info"]["customer_use"] = list(customer_use)
        except Exception as e:
            results["warnings"].append(f"Error getting CUSTOMER_INPUTS: {e}")
    
    return results

