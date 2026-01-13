#!/usr/bin/env python3
"""
Pytest test cases for YAML nodes using test_yaml_nodes module

This module provides pytest-based unit tests that use the test_yaml_nodes
functions to test YAML node configurations.
"""

import pytest
from pathlib import Path
import sys

try:
    import torch
    TORCH_AVALIABLE = True
except ImportError:
    TORCH_AVALIABLE = False

from pyromind_sdk.tests.test_yaml_nodes import test_yaml_file, test_directory


# Get the examples directory path
# From tests/pytest/ to examples/ requires going up 3 levels
EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"


class TestYAMLNodes:
    """Test class for YAML node configurations"""
    
    @pytest.mark.parametrize("yaml_file", [
        "hello_world_node.yaml",
        "echo_node.yaml",
        "python_calculator_node.yaml",
        "multi_input_node.yaml",
        "customer_inputs_node.yaml",
        "multiline_text_node.yaml",
        "simple_gpu_node.yaml",
        "jupyter_gpu_node.yaml",
    ])
    def test_yaml_file_validation(self, yaml_file):
        """Test that YAML files can be loaded and validated"""
        yaml_path = EXAMPLES_DIR / yaml_file
        if not yaml_path.exists():
            pytest.skip(f"YAML file not found: {yaml_file}")
        
        result = test_yaml_file(str(yaml_path), verbose=False, execute=False)
        
        assert result["success"], f"Failed to load {yaml_file}: {result.get('error', 'Unknown error')}"
        assert "nodes" in result, f"No nodes found in {yaml_file}"
        assert len(result["nodes"]) > 0, f"Empty nodes list in {yaml_file}"
        
        # Check that all nodes are valid
        for node_result in result["nodes"]:
            validation = node_result.get("validation", {})
            assert validation.get("valid", False), \
                f"Node validation failed in {yaml_file}: {validation.get('errors', [])}"
    
    @pytest.mark.parametrize("yaml_file,expected_success", [
        ("hello_world_node.yaml", True),
        ("echo_node.yaml", True),
        ("multi_input_node.yaml", True),
        ("customer_inputs_node.yaml", True),
        ("jupyter_gpu_node.yaml", TORCH_AVALIABLE),  # Will be dynamically adjusted based on GPU availability
    ])
    def test_yaml_file_execution(self, yaml_file, expected_success):
        """Test that YAML files can be executed successfully (or fail as expected)"""
        yaml_path = EXAMPLES_DIR / yaml_file
        if not yaml_path.exists():
            pytest.skip(f"YAML file not found: {yaml_file}")
        
        result = test_yaml_file(str(yaml_path), verbose=False, execute=True)
        
        assert result["success"], f"Failed to load {yaml_file}: {result.get('error', 'Unknown error')}"
        assert "nodes" in result, f"No nodes found in {yaml_file}"
        
        # Check execution results
        for node_result in result["nodes"]:
            validation = node_result.get("validation", {})
            assert validation.get("valid", False), \
                f"Node validation failed in {yaml_file}: {validation.get('errors', [])}"
            
            execution = node_result.get("execution")
            if execution:
                returncode = execution.get('returncode', None)
                has_errors = execution.get('errors') and len(execution.get('errors', [])) > 0
                
                if expected_success:
                    # Should succeed
                    assert returncode == 0, \
                        f"Command execution failed with return code {returncode} in {yaml_file}"
                    assert not has_errors, \
                        f"Execution errors in {yaml_file}: {execution.get('errors', [])}"
                    
                    # Check that outputs are not empty
                    outputs = execution.get("outputs", {})
                    for output_name, output_value in outputs.items():
                        assert output_value, \
                            f"Empty output '{output_name}' in {yaml_file}"
                else:
                    # Should fail (has errors or non-zero return code)
                    assert has_errors or returncode != 0, \
                        f"Expected {yaml_file} to have execution errors or non-zero return code, " \
                        f"but got returncode={returncode}, errors={execution.get('errors', [])}"
    
    def test_hello_world_node_with_custom_input(self):
        """Test hello_world_node with custom input"""
        yaml_path = EXAMPLES_DIR / "hello_world_node.yaml"
        if not yaml_path.exists():
            pytest.skip("hello_world_node.yaml not found")
        
        custom_inputs = {"name": "Pytest"}
        result = test_yaml_file(str(yaml_path), verbose=False, execute=True, inputs=custom_inputs)
        
        assert result["success"]
        assert "nodes" in result
        
        for node_result in result["nodes"]:
            execution = node_result.get("execution")
            if execution:
                outputs = execution.get("outputs", {})
                if "output" in outputs:
                    assert "Pytest" in outputs["output"], \
                        f"Expected 'Pytest' in output, got: {outputs['output']}"
    
    def test_examples_directory(self):
        """Test all YAML files in examples directory"""
        if not EXAMPLES_DIR.exists():
            pytest.skip("Examples directory not found")
        
        result = test_directory(str(EXAMPLES_DIR), verbose=False, execute=False)
        
        assert result["success"], f"Failed to test directory: {result.get('error', 'Unknown error')}"
        assert result.get("total_nodes", 0) > 0, "No nodes found in examples directory"
        
        # Check that all nodes are valid
        for node_result in result.get("nodes", []):
            validation = node_result.get("validation", {})
            assert validation.get("valid", False), \
                f"Node validation failed: {validation.get('errors', [])}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
