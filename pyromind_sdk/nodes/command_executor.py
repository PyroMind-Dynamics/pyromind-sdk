"""
Command template execution utility

Provides common functionality for executing PodExecutionNode's COMMAND_TEMPLATE.
"""

import os
import re
import json
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple


def extract_placeholders(command_template: List[str]) -> Set[str]:
    """Extract all {{}} wrapped placeholders from command template"""
    placeholders = set()
    for part in command_template:
        if isinstance(part, str):
            matches = re.findall(r'\{\{([a-zA-Z0-9_-]+)\}\}', part)
            placeholders.update(matches)
    return placeholders


def replace_template(template: str, replacements: Dict[str, Any], exclude_keys: set = None) -> str:
    """Replace placeholders in template
    
    Args:
        template: Template string
        replacements: Replacement dictionary
        exclude_keys: Keys to exclude (not replaced)
    """
    if exclude_keys is None:
        exclude_keys = set()
    result = template
    for key, value in replacements.items():
        if key not in exclude_keys:
            result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def get_default_inputs(input_types: Dict[str, Any]) -> Dict[str, Any]:
    """Extract default values from input types"""
    def parse_input_spec(input_spec: Any) -> Tuple[str, Dict[str, Any]]:
        """Parse input type specification"""
        if isinstance(input_spec, (tuple, list)) and len(input_spec) >= 1:
            input_type = input_spec[0]
            input_config = input_spec[1] if len(input_spec) > 1 else {}
            return str(input_type), input_config
        return "UNKNOWN", {}
    
    inputs = {}
    for input_name, input_spec in input_types.get("required", {}).items():
        _, config = parse_input_spec(input_spec)
        if "default" in config:
            inputs[input_name] = config["default"]
    for input_name, input_spec in input_types.get("optional", {}).items():
        _, config = parse_input_spec(input_spec)
        if "default" in config:
            inputs[input_name] = config["default"]
    return inputs


def read_output_file(file_path: str) -> Optional[str]:
    """Read output file content"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
    except Exception:
        pass
    return None

def print_node_info(node_name: str, node_class: type, validation: Dict[str, Any], execution_result: Optional[Dict[str, Any]] = None):
    """Print detailed node information"""
    print(f"\n{'='*60}")
    print(f"Node: {node_name} ({node_class.__name__})")
    print(f"{'='*60}")
    print(f"Valid: {validation['valid']}")
    
    if validation["errors"]:
        print(f"\nErrors:")
        for error in validation["errors"]:
            print(f"  ✗ {error}")
    
    if validation["warnings"]:
        print(f"\nWarnings:")
        for warning in validation["warnings"]:
            print(f"  ⚠ {warning}")
    
    print(f"\nBasic Info:")
    info = validation["info"]
    print(f"  Category: {info.get('category', 'N/A')}")
    print(f"  Display Name: {info.get('display_name', 'N/A')}")
    print(f"  Description: {info.get('description', 'N/A')}")
    print(f"  Base Classes: {', '.join(info.get('base_classes', []))}")
    print(f"  Node Type: {info.get('node_type', 'N/A')}")
    
    # Input information
    if "detailed_inputs" in info:
        print(f"\n{'─'*60}")
        print("Inputs:")
        print(f"{'─'*60}")
        for input_name, input_info in info["detailed_inputs"].items():
            req_mark = "[REQUIRED]" if input_info.get("required") else "[OPTIONAL]"
            print(f"  {input_name} {req_mark}")
            print(f"    Type: {input_info.get('type', 'Unknown')}")
            default = input_info.get('default', None)
            if default is not None:
                default_str = json.dumps(default) if isinstance(default, (str, dict, list)) else str(default)
                print(f"    Default: {default_str}")
    
    # Output information
    if "outputs" in info:
        print(f"\n{'─'*60}")
        print("Outputs:")
        print(f"{'─'*60}")
        for output_name, output_info in info["outputs"].items():
            print(f"  {output_name}")
            print(f"    Type: {output_info.get('type', 'Unknown')}")
            print(f"    Index: {output_info.get('index', 'Unknown')}")
    
    # Customer Use information (including inputs and outputs)
    if "customer_use" in info:
        print(f"\n{'─'*60}")
        print("Customer Use:")
        print(f"{'─'*60}")
        customer_use = info["customer_use"]
        if customer_use:
            for param_name in customer_use:
                print(f"  {param_name}")
        else:
            print("  (none)")
    
    # Command template
    if "command_template" in info:
        print(f"\n{'─'*60}")
        print("Command Template:")
        print(f"{'─'*60}")
        cmd_template = info["command_template"]
        if isinstance(cmd_template, list):
            # Display command template, keep placeholder form
            cmd_str = ' '.join(str(part) for part in cmd_template)
            print(f"  {cmd_str}")
            
            # Display placeholders
            placeholders = extract_placeholders(cmd_template)
            if placeholders:
                print(f"\n  Placeholders:")
                for placeholder in sorted(placeholders):
                    print(f"    {{{{ {placeholder} }}}}")
        else:
            print(f"  {cmd_template}")
    
    # Resource information
    if "resources" in info:
        print(f"\n{'─'*60}")
        print("Resources:")
        print(f"{'─'*60}")
        for key, value in info["resources"].items():
            print(f"  {key}: {value}")
    
    # Execution result (if provided)
    if execution_result:
        print(f"\n{'─'*60}")
        print("Execution Result:")
        print(f"{'─'*60}")
        
        # Return code
        returncode = execution_result.get('returncode', 'N/A')
        status = "✓" if returncode == 0 else "✗"
        print(f"  {status} Return code: {returncode}")
        
        # Output content
        if execution_result.get("outputs"):
            print(f"\n  Outputs:")
            for output_name, output_value in execution_result["outputs"].items():
                value_preview = str(output_value).strip()
                # For multiline output, show first few lines
                lines = value_preview.split('\n')
                if len(lines) > 5:
                    value_preview = '\n'.join(lines[:5]) + f"\n    ... ({len(lines) - 5} more lines)"
                print(f"    {output_name}: {value_preview}")
        
        # Standard output
        if execution_result.get("stdout"):
            stdout = execution_result["stdout"].strip()
            if stdout:
                print(f"\n  Stdout:")
                stdout_lines = stdout.split('\n')
                for line in stdout_lines[:10]:  # Show at most 10 lines
                    if line.strip():
                        print(f"    {line}")
                if len(stdout_lines) > 10:
                    more_lines = len(stdout_lines) - 10
                    print(f"    ... ({more_lines} more lines)")
        
        # Standard error
        if execution_result.get("stderr"):
            stderr = execution_result["stderr"].strip()
            if stderr:
                print(f"\n  Stderr:")
                stderr_lines = stderr.split('\n')
                for line in stderr_lines[:10]:  # Show at most 10 lines
                    if line.strip():
                        print(f"    {line}")
                if len(stderr_lines) > 10:
                    more_lines = len(stderr_lines) - 10
                    print(f"    ... ({more_lines} more lines)")
        
        # Errors and warnings
        if execution_result.get("errors"):
            print(f"\n  Errors:")
            for error in execution_result["errors"]:
                print(f"    ✗ {error}")
        
        if execution_result.get("warnings"):
            print(f"\n  Warnings:")
            for warning in execution_result["warnings"]:
                print(f"    ⚠ {warning}")


def prepare_command_template(
    command_template: List[str],
    inputs: Optional[Dict[str, Any]] = None,
    output_names: Optional[List[str]] = None
) -> Tuple[List[str], Dict[str, str], Set[str], Set[str]]:
    """Prepare command template, distinguish input and output placeholders
    
    Args:
        command_template: Command template list
        inputs: Input value dictionary
        output_names: Output name list
        
    Returns:
        (command_parts, output_file_paths, input_placeholders, output_placeholders)
    """
    # Extract all placeholders
    all_placeholders = extract_placeholders(command_template)
    
    # Distinguish input and output placeholders
    input_placeholders = set()
    output_placeholders = set()
    
    if output_names:
        output_placeholders = set(output_names) & all_placeholders
        input_placeholders = all_placeholders - output_placeholders
    else:
        # If output_names not provided, assume all placeholders are inputs
        input_placeholders = all_placeholders
    
    # Create temporary files for output placeholders
    output_file_paths = {}
    for output_name in output_placeholders:
        temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=f'_{output_name}')
        temp_file.close()
        output_file_paths[output_name] = temp_file.name
    
    # Process command template, keep placeholder form
    command_parts = []
    for part in command_template:
        if isinstance(part, str):
            # Check if contains parameters that need processing (special parameters for Python nodes)
            if "--output-paths" in part or "--inputs" in part:
                # Use shlex.split to correctly parse command line arguments
                try:
                    parsed_args = shlex.split(part)
                except:
                    parsed_args = part.split()
                
                # Process each argument, keep placeholders unchanged
                new_parts = []
                i = 0
                while i < len(parsed_args):
                    arg = parsed_args[i]
                    new_parts.append(arg)
                    
                    # Process --output-paths and --inputs parameters, keep placeholders
                    if arg in ("--output-paths", "--inputs") and i + 1 < len(parsed_args):
                        new_parts.append(parsed_args[i + 1])  # Keep original value (contains placeholder)
                        i += 1
                    i += 1
                
                # Recombine command (use shlex.quote for JSON parameters)
                quoted_parts = []
                for p in new_parts:
                    # If JSON string (contains { or [), need to quote
                    if isinstance(p, str) and ('{' in p or '[' in p):
                        quoted_parts.append(shlex.quote(p))
                    else:
                        quoted_parts.append(p)
                part = " ".join(quoted_parts)
            
            command_parts.append(part)
        else:
            command_parts.append(str(part))
    
    return command_parts, output_file_paths, input_placeholders, output_placeholders


def execute_command_template(
    command_template: List[str],
    inputs: Optional[Dict[str, Any]] = None,
    output_names: Optional[List[str]] = None,
    timeout: int = 300
) -> Dict[str, Any]:
    """Execute command template
    
    Args:
        command_template: Command template list
        inputs: Input value dictionary
        output_names: Output name list
        timeout: Execution timeout (seconds)
        
    Returns:
        Dictionary containing execution results:
        - success: Whether successful
        - returncode: Return code
        - stdout: Standard output
        - stderr: Standard error
        - outputs: Output file content dictionary
        - command: Actually executed command
        - errors: Error list
        - warnings: Warning list
    """
    result = {
        "success": True,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "outputs": {},
        "command": None,
        "errors": [],
        "warnings": []
    }
    
    try:
        # 准备命令模板
        command_parts, output_file_paths, input_placeholders, output_placeholders = prepare_command_template(
            command_template, inputs, output_names
        )
        
        # 在执行时，需要替换所有占位符为实际值
        actual_command_parts = []
        all_replacements = {}
        if inputs:
            all_replacements.update(inputs)
        all_replacements.update(output_file_paths)
        
        for part in command_parts:
            if isinstance(part, str):
                # 检查是否是 Python 节点的特殊参数（--inputs 或 --output-paths）
                if ("--inputs" in part and inputs) or "--output-paths" in part:
                    # 解析命令部分，替换特殊参数中的占位符
                    try:
                        parsed_args = shlex.split(part)
                    except:
                        parsed_args = part.split()
                    
                    new_parts = []
                    j = 0
                    while j < len(parsed_args):
                        arg = parsed_args[j]
                        new_parts.append(arg)
                        
                        # 处理 --inputs 参数
                        if arg == "--inputs" and j + 1 < len(parsed_args) and inputs:
                            inputs_str = parsed_args[j + 1]
                            try:
                                inputs_dict = json.loads(inputs_str)
                                # 替换占位符为实际值
                                for key, value in inputs.items():
                                    if key in inputs_dict:
                                        placeholder = f"{{{{{key}}}}}"
                                        if inputs_dict[key] == placeholder:
                                            inputs_dict[key] = str(value)
                                # 重新构建 JSON 字符串
                                new_inputs_json = json.dumps(inputs_dict, ensure_ascii=False)
                                new_parts.append(new_inputs_json)
                                j += 1  # 跳过原值
                            except (json.JSONDecodeError, IndexError):
                                new_parts.append(parsed_args[j + 1])
                                j += 1
                        
                        # 处理 --output-paths 参数
                        elif arg == "--output-paths" and j + 1 < len(parsed_args):
                            output_paths_str = parsed_args[j + 1]
                            try:
                                output_paths_dict = json.loads(output_paths_str)
                                # 替换占位符为实际文件路径
                                for output_name, output_path in output_file_paths.items():
                                    if output_name in output_paths_dict:
                                        placeholder = f"{{{{{output_name}}}}}"
                                        if output_paths_dict[output_name] == placeholder:
                                            output_paths_dict[output_name] = output_path
                                # 重新构建 JSON 字符串
                                new_output_paths_json = json.dumps(output_paths_dict, ensure_ascii=False)
                                new_parts.append(new_output_paths_json)
                                j += 1  # 跳过原值
                            except (json.JSONDecodeError, IndexError):
                                new_parts.append(parsed_args[j + 1])
                                j += 1
                        
                        j += 1
                    
                    # 重新组合命令部分
                    actual_command_parts.append(" ".join(shlex.quote(str(p)) for p in new_parts))
                else:
                    # 普通命令模板：替换所有占位符
                    actual_part = replace_template(part, all_replacements)
                    actual_command_parts.append(actual_part)
            else:
                actual_command_parts.append(part)
        
        result["command"] = actual_command_parts
        
        # 执行命令
        process_result = subprocess.run(
            actual_command_parts,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        result["returncode"] = process_result.returncode
        result["stdout"] = process_result.stdout
        result["stderr"] = process_result.stderr
        result["success"] = process_result.returncode == 0
        
        # 读取输出文件
        for output_name, file_path in output_file_paths.items():
            # 等待一下确保文件写入完成
            time.sleep(0.1)
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                result["warnings"].append(f"Output file not found: {file_path}")
                continue
            
            # 读取文件内容
            content = read_output_file(file_path)
            if content is not None:
                content = content.rstrip('\n\r')
                if content:
                    result["outputs"][output_name] = content
                else:
                    file_size = os.path.getsize(file_path)
                    result["warnings"].append(
                        f"Output file exists but is empty: {file_path} (size: {file_size})"
                    )
            else:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    result["warnings"].append(
                        f"Output file exists but could not be read: {file_path} (size: {file_size})"
                    )
                else:
                    result["warnings"].append(f"Output file not found: {file_path}")
            
            # 清理临时文件
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception:
                pass
                
    except subprocess.TimeoutExpired:
        result["success"] = False
        result["errors"].append(f"Command execution timeout (exceeded {timeout} seconds)")
    except Exception as e:
        result["success"] = False
        result["errors"].append(f"Error executing command: {e}")
    
    return result

