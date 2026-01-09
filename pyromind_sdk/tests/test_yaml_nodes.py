#!/usr/bin/env python3
"""
YAML Node Testing Tool

Used for testing and executing Python node classes generated from YAML.
Main features:
1. Load specific YAML, check if it can be converted to Python class
2. Print detailed class information when using verbose
3. Execute command_template through Python class
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any, Optional
from pprint import pprint

try:
    import pyromind_sdk
except ImportError:
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

from pyromind_sdk.nodes import (
    load_nodes_from_yaml,
    load_all_nodes_from_directory,
    execute_command_template,
    get_default_inputs,
    extract_placeholders,
    parse_input_spec,
    validate_node_class,
    print_node_info,
)
from pyromind_sdk.common.node_sdk import PodExecutionNode


# validate_node_class and parse_input_spec have been moved to nodes.node_validator module




def test_yaml_file(yaml_path: str, verbose: bool = False, execute: bool = False, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Test a single YAML file"""
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        return {"success": False, "error": f"File not found: {yaml_path}"}
    
    try:
        nodes = load_nodes_from_yaml(str(yaml_path))
        if not nodes:
            return {"success": False, "error": "No nodes found in YAML file"}
        
        results = {"success": True, "file": str(yaml_path), "nodes": []}
        
        for node_name, node_class in nodes.items():
            # 验证节点类
            validation = validate_node_class(node_class, node_name)
            
            # 执行命令模板
            execution_result = None
            if execute and validation["valid"] and hasattr(node_class, "COMMAND_TEMPLATE"):
                command_template = node_class.COMMAND_TEMPLATE
                if command_template:
                    # 获取输入类型和默认值
                    input_types = {}
                    if hasattr(node_class, "BASE_INPUT_TYPES"):
                        input_types = node_class.BASE_INPUT_TYPES()
                    
                    # 如果没有提供输入，使用默认值
                    if inputs is None:
                        inputs = get_default_inputs(input_types)
                    
                    # 获取输出名称
                    return_names = list(getattr(node_class, "RETURN_NAMES", ()))
                    
                    # 执行命令模板
                    execution_result = execute_command_template(
                        command_template,
                        inputs=inputs,
                        output_names=return_names if return_names else None
                    )
            
            # 如果 verbose，打印详细信息（包括执行结果）
            if verbose:
                print_node_info(node_name, node_class, validation, execution_result)
            
            node_result = {
                "validation": validation,
                "execution": execution_result
            }
            results["nodes"].append(node_result)
        
        return results
    except Exception as e:
        return {"success": False, "error": str(e), "file": str(yaml_path)}


def test_directory(directory: str, verbose: bool = False, execute: bool = False) -> Dict[str, Any]:
    """Test all YAML files in directory"""
    directory = Path(directory)
    if not directory.exists():
        return {"success": False, "error": f"Directory not found: {directory}"}
    
    try:
        all_nodes = load_all_nodes_from_directory(str(directory))
        results = {
            "success": True,
            "directory": str(directory),
            "total_nodes": len(all_nodes),
            "nodes": []
        }
        
        for node_name, node_class in all_nodes.items():
            validation = validate_node_class(node_class, node_name)
            
            # 执行命令模板
            execution_result = None
            if execute and validation["valid"] and hasattr(node_class, "COMMAND_TEMPLATE"):
                command_template = node_class.COMMAND_TEMPLATE
                if command_template:
                    # 获取输入类型和默认值
                    input_types = {}
                    if hasattr(node_class, "BASE_INPUT_TYPES"):
                        input_types = node_class.BASE_INPUT_TYPES()
                    
                    # 使用默认值
                    inputs = get_default_inputs(input_types)
                    
                    # 获取输出名称
                    return_names = list(getattr(node_class, "RETURN_NAMES", ()))
                    
                    # 执行命令模板
                    execution_result = execute_command_template(
                        command_template,
                        inputs=inputs,
                        output_names=return_names if return_names else None
                    )
            
            # 如果 verbose，打印详细信息（包括执行结果）
            if verbose:
                print_node_info(node_name, node_class, validation, execution_result)
            
            results["nodes"].append({
                "validation": validation,
                "execution": execution_result
            })
        
        return results
    except Exception as e:
        return {"success": False, "error": str(e), "directory": str(directory)}


def print_summary(results: Dict[str, Any], verbose: bool = False, execute: bool = False):
    """Print test results summary"""
    if "nodes" not in results:
        return
    
    total = len(results["nodes"])
    valid = sum(1 for n in results["nodes"] if n.get("validation", {}).get("valid", False))
    
    print(f"\n{'='*60}")
    print(f"Test Results")
    print(f"{'='*60}")
    print(f"Total nodes: {total}")
    print(f"Valid: {valid}")
    print(f"{'='*60}")
    
    if not verbose:
        for node_result in results["nodes"]:
            validation = node_result.get("validation", {})
            status = "✓" if validation.get("valid", False) else "✗"
            print(f"{status} {validation.get('name', 'Unknown')} ({validation.get('class_name', 'Unknown')})")
            
            if not validation.get("valid", False) and validation.get("errors"):
                for error in validation["errors"][:3]:
                    print(f"    ✗ {error}")
            
            # 执行信息
            execution = node_result.get("execution")
            validation = node_result.get("validation", {})
            
            # 获取命令模板用于显示
            cmd_template = None
            if "info" in validation and "command_template" in validation["info"]:
                cmd_template = validation["info"]["command_template"]
            
            # 显示输入输出数量
            input_types = validation.get("info", {}).get("input_types", {})
            inputs_count = len(input_types.get("required", [])) + len(input_types.get("optional", []))
            outputs_info = validation.get("info", {}).get("outputs", {})
            outputs_count = len(outputs_info) if outputs_info else (len(execution.get("outputs", {})) if execution else 0)
            print(f"    Inputs: {inputs_count} | Outputs: {outputs_count}")
            
            # 显示命令模板（保持占位符形式）
            if cmd_template:
                cmd_str = ' '.join(str(part) for part in cmd_template) if isinstance(cmd_template, list) else str(cmd_template)
                print(f"    Command: {cmd_str}")
            
            # 输出内容
            if execute and execution and execution.get("outputs"):
                print(f"    Outputs:")
                for output_name, output_value in execution["outputs"].items():
                    value_preview = str(output_value).strip()
                    if len(value_preview) > 100:
                        value_preview = value_preview[:100] + "..."
                    print(f"      {output_name}: {value_preview}")
            
            # 执行结果
            if execute and execution:
                returncode = execution.get('returncode', 'N/A')
                status = "✓" if returncode == 0 else "✗"
                print(f"    {status} Return code: {returncode}")
                if returncode != 0 and execution.get("stderr"):
                    stderr_preview = execution["stderr"].strip()[:200]
                    if len(execution["stderr"].strip()) > 200:
                        stderr_preview += "..."
                    print(f"      Error: {stderr_preview}")


def main():
    parser = argparse.ArgumentParser(
        description="Test and validate YAML node configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test a single YAML file
  python test_yaml_nodes.py hello_world_node.yaml
  
  # Test with verbose output
  python test_yaml_nodes.py hello_world_node.yaml --verbose
  
  # Execute the command template
  python test_yaml_nodes.py hello_world_node.yaml --execute
  
  # Test with custom inputs
  python test_yaml_nodes.py hello_world_node.yaml --execute --inputs '{"name": "Alice"}'
  
  # Test all YAML files in a directory
  python test_yaml_nodes.py --directory examples
        """
    )
    
    parser.add_argument("yaml_path", nargs="?", help="Path to YAML file or directory")
    parser.add_argument("--directory", "-d", action="store_true", help="Treat path as directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed information")
    parser.add_argument("--execute", "-e", action="store_true", help="Execute the command template")
    parser.add_argument("--inputs", type=str, help="Input values as JSON string")
    parser.add_argument("--json", "-j", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    # 默认路径
    if not args.yaml_path:
        script_dir = Path(__file__).parent.parent
        default_dir = script_dir / "examples"
        if default_dir.exists():
            args.yaml_path = str(default_dir)
            args.directory = True
        else:
            parser.error("No YAML path provided and default directory not found")
    
    # 解析输入参数
    inputs = None
    if args.inputs:
        try:
            inputs = json.loads(args.inputs)
        except json.JSONDecodeError as e:
            print(f"Error parsing inputs JSON: {e}", file=sys.stderr)
            sys.exit(1)
    
    # 执行测试
    if args.directory or Path(args.yaml_path).is_dir():
        results = test_directory(args.yaml_path, verbose=args.verbose, execute=args.execute)
    else:
        results = test_yaml_file(args.yaml_path, verbose=args.verbose, execute=args.execute, inputs=inputs)
    
    # 输出结果
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        if not results.get("success"):
            print(f"Error: {results.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)
        print_summary(results, verbose=args.verbose, execute=args.execute)


if __name__ == "__main__":
    main()
