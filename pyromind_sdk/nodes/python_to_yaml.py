"""
Python node class to YAML configuration converter

Converts Python class-defined nodes to YAML configuration files.
"""

import yaml
import inspect
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path


# Base class to name mapping (reverse mapping)
CLASS_TO_NAME_MAP = {
    "PodExecutionNode": "PodExecutionNode",
    "GpuPodExecutionNode": "GpuPodExecutionNode",
    "JupyterLabPodExecutionNode": "JupyterLabPodExecutionNode",
    "PortPodExecutionNode": "PortPodExecutionNode",
    "DaemonPodExecutionNode": "DaemonPodExecutionNode",
    "EndpointNode": "EndpointNode",
}


def get_base_classes(node_class: type) -> List[str]:
    """
    Get base class name list for node
    
    Args:
        node_class: Node class
        
    Returns:
        Base class name list
    """
    base_classes = []
    for base in node_class.__bases__:
        base_name = base.__name__
        # Only include base classes we support
        if base_name in CLASS_TO_NAME_MAP:
            base_classes.append(base_name)
    
    return base_classes


def parse_input_type_spec(input_spec: Tuple) -> Dict[str, Any]:
    """
    Parse input type specification
    
    Args:
        input_spec: Input type tuple, e.g., ("STRING", {"default": "value"}) or ("STRING",)
        
    Returns:
        Parsed configuration dictionary
    """
    if not input_spec:
        return {"type": "STRING"}
    
    if len(input_spec) == 1:
        # Only type, no options
        type_spec = input_spec[0]
        if isinstance(type_spec, str):
            return {"type": type_spec}
        elif isinstance(type_spec, list):
            return {"type": type_spec}
        else:
            return {"type": "STRING"}
    
    # Has type and options
    type_spec = input_spec[0]
    options = input_spec[1] if len(input_spec) > 1 else {}
    
    config = {}
    if isinstance(type_spec, str):
        config["type"] = type_spec
    elif isinstance(type_spec, list):
        config["type"] = type_spec
    else:
        config["type"] = "STRING"
    
    # Add options
    if isinstance(options, dict):
        config.update(options)
    
    return config


def convert_node_class_to_yaml(node_class: type, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert Python node class to YAML configuration dictionary
    
    Args:
        node_class: Node class
        output_path: Optional output file path
        
    Returns:
        YAML configuration dictionary
    """
    config = {}
    
    # Basic information
    config["name"] = node_class.__name__
    
    if hasattr(node_class, "DESCRIPTION"):
        config["description"] = node_class.DESCRIPTION
    if hasattr(node_class, "CATEGORY"):
        config["category"] = node_class.CATEGORY
    if hasattr(node_class, "DISPLAY_NAME"):
        config["display_name"] = node_class.DISPLAY_NAME
    
    # Base classes
    base_classes = get_base_classes(node_class)
    if len(base_classes) == 1:
        config["base_class"] = base_classes[0]
    elif len(base_classes) > 1:
        config["base_class"] = base_classes
    
    # Return types
    if hasattr(node_class, "RETURN_TYPES") and node_class.RETURN_TYPES:
        config["return_types"] = list(node_class.RETURN_TYPES)
    if hasattr(node_class, "RETURN_NAMES") and node_class.RETURN_NAMES:
        config["return_names"] = list(node_class.RETURN_NAMES)
    if hasattr(node_class, "OUTPUT_NODE"):
        config["output_node"] = node_class.OUTPUT_NODE
    
    # PodExecutionNode related attributes
    if hasattr(node_class, "COMMAND_TEMPLATE"):
        config["command_template"] = node_class.COMMAND_TEMPLATE
    if hasattr(node_class, "ARGS_TEMPLATE"):
        config["args_template"] = node_class.ARGS_TEMPLATE
    
    # Resource limits
    resources = {}
    if hasattr(node_class, "MEMORY_LIMIT") and node_class.MEMORY_LIMIT is not None:
        resources["memory_limit"] = node_class.MEMORY_LIMIT
    if hasattr(node_class, "CPU_LIMIT") and node_class.CPU_LIMIT is not None:
        resources["cpu_limit"] = node_class.CPU_LIMIT
    if hasattr(node_class, "GPU_MIN_COUNT"):
        resources["gpu_min_count"] = node_class.GPU_MIN_COUNT
    if hasattr(node_class, "GPU_MAX_COUNT"):
        resources["gpu_max_count"] = node_class.GPU_MAX_COUNT
    if resources:
        config["resources"] = resources
    
    # Input types
    if hasattr(node_class, "BASE_INPUT_TYPES"):
        try:
            input_types = node_class.BASE_INPUT_TYPES()
            inputs_config = {}
            
            # Process required inputs
            if "required" in input_types and input_types["required"]:
                inputs_config["required"] = {}
                for name, spec in input_types["required"].items():
                    inputs_config["required"][name] = parse_input_type_spec(spec)
            
            # Process optional inputs
            if "optional" in input_types and input_types["optional"]:
                inputs_config["optional"] = {}
                for name, spec in input_types["optional"].items():
                    inputs_config["optional"][name] = parse_input_type_spec(spec)
            
            if inputs_config:
                config["inputs"] = inputs_config
        except Exception as e:
            print(f"Warning: Could not parse BASE_INPUT_TYPES for {node_class.__name__}: {e}")
    
    # Customer inputs
    if hasattr(node_class, "CUSTOMER_INPUTS"):
        try:
            customer_inputs = node_class.CUSTOMER_INPUTS()
            if customer_inputs:
                config["customer_inputs"] = list(customer_inputs)
        except Exception as e:
            print(f"Warning: Could not parse CUSTOMER_INPUTS for {node_class.__name__}: {e}")
    
    # If output path is specified, save to file
    if output_path:
        save_yaml_config(config, output_path)
    
    return config


def save_yaml_config(config: Dict[str, Any], output_path: str):
    """
    Save configuration as YAML file
    
    Args:
        config: Configuration dictionary
        output_path: Output file path
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"✓ YAML configuration saved to: {output_path}")


def convert_module_to_yaml(module, output_dir: str = "nodes"):
    """
    Convert all node classes in module to YAML files
    
    Args:
        module: Python module
        output_dir: Output directory
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all node classes in module
    node_classes = []
    for name, obj in inspect.getmembers(module):
        if (inspect.isclass(obj) and 
            obj.__module__ == module.__name__ and
            name.endswith("Node")):
            node_classes.append((name, obj))
    
    print(f"Found {len(node_classes)} node classes")
    
    for class_name, node_class in node_classes:
        try:
            config = convert_node_class_to_yaml(node_class)
            output_path = output_dir / f"{class_name.lower()}.yaml"
            save_yaml_config(config, output_path)
        except Exception as e:
            print(f"Error converting {class_name}: {e}")


def yaml_to_node_class(yaml_path: str) -> type:
    """
    Convert YAML configuration to Python class object (returns class directly, does not generate code file)
    
    Args:
        yaml_path: YAML configuration file path
        
    Returns:
        Node class object
    """
    from .yaml_loader import load_nodes_from_yaml
    
    # Use existing loader to directly load node classes
    nodes = load_nodes_from_yaml(yaml_path)
    
    if not nodes:
        raise ValueError(f"No nodes found in {yaml_path}")
    
    # If only one node, return directly
    if len(nodes) == 1:
        return list(nodes.values())[0]
    
    # If multiple nodes, return dictionary
    return nodes


def yaml_to_python_code(yaml_path: str, output_path: Optional[str] = None) -> str:
    """
    Convert YAML configuration to Python code string (for generating code files)
    
    Note: If you need to use class objects directly, use yaml_to_node_class() function
    
    Args:
        yaml_path: YAML configuration file path
        output_path: Optional output Python file path
        
    Returns:
        Python code string
    """
    import yaml
    
    # Load YAML configuration
    with open(yaml_path, "r", encoding="utf-8") as f:
        yaml_config = yaml.safe_load(f)
    
    # If multi-node file, take the first one
    if isinstance(yaml_config, dict) and "nodes" in yaml_config:
        node_config = yaml_config["nodes"][0]
    else:
        node_config = yaml_config
    
    # Generate Python code
    code_lines = []
    code_lines.append(f'"""')
    code_lines.append(f'{node_config.get("description", "Node")}')
    code_lines.append(f'"""')
    code_lines.append("")
    
    # Import statements
    base_classes = node_config.get("base_class", [])
    if isinstance(base_classes, str):
        base_classes = [base_classes]
    
    imports = set()
    for base in base_classes:
        imports.add(base)
    
    if imports:
        imports_str = ", ".join(sorted(imports))
        # Use pyromind_sdk
        code_lines.append(f"from pyromind_sdk import {imports_str}")
        code_lines.append("")
    
    # Class definition
    class_name = node_config.get("name", "Node")
    if len(base_classes) == 1:
        base_str = base_classes[0]
    else:
        base_str = ", ".join(base_classes)
    
    code_lines.append(f"class {class_name}({base_str}):")
    
    # Class attributes
    if node_config.get("description"):
        code_lines.append(f'    DESCRIPTION = "{node_config["description"]}"')
    if node_config.get("category"):
        code_lines.append(f'    CATEGORY = "{node_config["category"]}"')
    if node_config.get("display_name"):
        code_lines.append(f'    DISPLAY_NAME = "{node_config["display_name"]}"')
    if node_config.get("return_types"):
        return_types = node_config["return_types"]
        code_lines.append(f'    RETURN_TYPES = {return_types}')
    if node_config.get("return_names"):
        return_names = node_config["return_names"]
        code_lines.append(f'    RETURN_NAMES = {return_names}')
    
    # Resource limits
    resources = node_config.get("resources", {})
    if resources:
        code_lines.append("")
        if "memory_limit" in resources:
            code_lines.append(f'    MEMORY_LIMIT = {resources["memory_limit"]}')
        if "cpu_limit" in resources:
            code_lines.append(f'    CPU_LIMIT = {resources["cpu_limit"]}')
        if "gpu_min_count" in resources:
            code_lines.append(f'    GPU_MIN_COUNT = {resources["gpu_min_count"]}')
        if "gpu_max_count" in resources:
            code_lines.append(f'    GPU_MAX_COUNT = {resources["gpu_max_count"]}')
    
    # Command template
    if node_config.get("command_template"):
        code_lines.append("")
        code_lines.append("    COMMAND_TEMPLATE = [")
        for cmd in node_config["command_template"]:
            code_lines.append(f'        "{cmd}",')
        code_lines.append("    ]")
    
    # BASE_INPUT_TYPES method
    if node_config.get("inputs"):
        code_lines.append("")
        code_lines.append("    @classmethod")
        code_lines.append("    def BASE_INPUT_TYPES(cls):")
        code_lines.append("        return {")
        
        inputs = node_config["inputs"]
        if inputs.get("required"):
            code_lines.append('            "required": {')
            for name, config in inputs["required"].items():
                type_spec = config.get("type", "STRING")
                options = {k: v for k, v in config.items() if k != "type"}
                if options:
                    code_lines.append(f'                "{name}": ({repr(type_spec)}, {options}),')
                else:
                    code_lines.append(f'                "{name}": ({repr(type_spec)},),')
            code_lines.append("            },")
        
        if inputs.get("optional"):
            code_lines.append('            "optional": {')
            for name, config in inputs["optional"].items():
                type_spec = config.get("type", "STRING")
                options = {k: v for k, v in config.items() if k != "type"}
                if options:
                    code_lines.append(f'                "{name}": ({repr(type_spec)}, {options}),')
                else:
                    code_lines.append(f'                "{name}": ({repr(type_spec)},),')
            code_lines.append("            },")
        else:
            code_lines.append('            "optional": {},')
        
        code_lines.append("        }")
    
    # CUSTOMER_INPUTS method
    if node_config.get("customer_inputs"):
        code_lines.append("")
        code_lines.append("    @classmethod")
        code_lines.append("    def CUSTOMER_INPUTS(cls) -> set:")
        code_lines.append('        """')
        code_lines.append("        Define which inputs are for customer use")
        code_lines.append('        """')
        customer_inputs = node_config["customer_inputs"]
        code_lines.append(f"        return {set(customer_inputs)}")
    
    code = "\n".join(code_lines)
    
    # If output path is specified, save to file
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"✓ Python code saved to: {output_path}")
    
    return code


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    from custom_gui_nodes_template.training import (
        TrainingConfigNodeV2,
        LoggingConfigNode,
        CtrlWorldTrainingNode,
    )
    
    print("=" * 60)
    print("Python to YAML Conversion Example")
    print("=" * 60)
    
    # Convert single node
    print("\n1. Convert TrainingConfigNodeV2:")
    config = convert_node_class_to_yaml(TrainingConfigNodeV2)
    print(f"   Node name: {config['name']}")
    print(f"   Base class: {config.get('base_class')}")
    print(f"   Input field count: {len(config.get('inputs', {}).get('required', {}))}")
    
    # Save to file
    output_dir = Path(__file__).parent / "converted_from_python"
    output_dir.mkdir(exist_ok=True)
    convert_node_class_to_yaml(TrainingConfigNodeV2, output_dir / "training_config_node_v2.yaml")
    convert_node_class_to_yaml(LoggingConfigNode, output_dir / "logging_config_node.yaml")
    convert_node_class_to_yaml(CtrlWorldTrainingNode, output_dir / "ctrl_world_training_node.yaml")
    
    print("\n2. YAML to Python Class Object Conversion Example:")
    yaml_path = Path(__file__).parent.parent / "tests" / "nodes" / "hello_world_node.yaml"
    if yaml_path.exists():
        # Directly convert to class object (recommended method)
        node_class = yaml_to_node_class(str(yaml_path))
        print(f"   Node class: {node_class.__name__}")
        print(f"   Base classes: {[b.__name__ for b in node_class.__bases__]}")
        print(f"   Description: {node_class.DESCRIPTION}")
        print(f"   Input fields: {list(node_class.BASE_INPUT_TYPES()['required'].keys())[:3]}...")
        
        # If code file generation is needed, can use yaml_to_python_code
        print("\n3. YAML to Python Code File Conversion Example:")
        python_code = yaml_to_python_code(str(yaml_path))
        print("\nGenerated Python code preview:")
        print("-" * 60)
        print("\n".join(python_code.split("\n")[:20]) + "...")
        print("-" * 60)
    
    print("\n" + "=" * 60)
    print("Conversion complete!")
    print("=" * 60)

