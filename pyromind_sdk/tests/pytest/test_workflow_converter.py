"""
Tests for Workflow Lite Converter

Tests the conversion between standard workflow format and workflow_lite format.

New simplified format:
- No 'name' or 'description' fields
- No separate 'connections' field
- inputs dict contains parameter values OR {node_id, output_name} connections
- outputs is a list of names only
"""

import json
import pytest
from pathlib import Path
from pyromind_sdk.workflow import WorkflowLiteConverter, to_workflow_lite, to_workflow_standard


class TestWorkflowLiteConverter:
    """Test WorkflowLiteConverter class."""

    def test_converter_initialization(self):
        """Test converter can be initialized."""
        # Without node_info
        converter = WorkflowLiteConverter()
        assert converter is not None
        assert converter._node_info == {}

        # With node_info
        node_info = {
            "TestNode": {
                "input": {"param1": "STRING"},
                "output": ["result"],
                "description": "Test node"
            }
        }
        converter = WorkflowLiteConverter(node_info=node_info)
        assert converter._node_info == node_info

    def test_set_node_info(self):
        """Test updating node_info after initialization."""
        converter = WorkflowLiteConverter()
        assert converter._node_info == {}

        node_info = {"TestNode": {"input": {}}}
        converter.set_node_info(node_info)
        assert converter._node_info == node_info

    def test_to_lite_basic(self):
        """Test basic conversion to lite format."""
        workflow = {
            "id": "test-workflow",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "pos": [0, 0],
                    "size": [100, 100],
                    "flags": {},
                    "order": 0,
                    "mode": 0,
                    "inputs": [
                        {
                            "name": "input1",
                            "type": "STRING",
                            "link": None
                        }
                    ],
                    "outputs": [
                        {
                            "name": "output1",
                            "type": "STRING",
                            "links": []
                        }
                    ],
                    "properties": {},
                    "widgets_values": ["test_value"]
                }
            ],
            "links": []
        }

        converter = WorkflowLiteConverter()
        lite = converter.to_lite(workflow)

        assert "version" in lite
        assert "nodes" in lite
        assert "test" in lite["nodes"]
        assert lite["nodes"]["test"]["type"] == "TestNode"
        assert lite["nodes"]["test"]["index"] == 1
        # outputs is a list now
        assert isinstance(lite["nodes"]["test"]["outputs"], list)
        assert "output1" in lite["nodes"]["test"]["outputs"]
        # No name or description fields
        assert "name" not in lite
        assert "description" not in lite["nodes"]["test"]

    def test_to_standard_basic(self):
        """Test basic conversion to standard format."""
        lite = {
            "version": "1.0",
            "nodes": {
                "test_node": {
                    "type": "TestNode",
                    "inputs": {"input1": "value1"},
                    "outputs": ["output1"]
                }
            }
        }

        converter = WorkflowLiteConverter()
        standard = converter.to_standard(lite)

        assert "id" in standard
        assert "nodes" in standard
        assert len(standard["nodes"]) == 1
        assert standard["nodes"][0]["type"] == "TestNode"

    def test_connection_conversion(self):
        """Test connections are embedded in inputs correctly."""
        workflow = {
            "id": "test-workflow",
            "nodes": [
                {
                    "id": 1,
                    "type": "NodeA",
                    "inputs": [],
                    "outputs": [
                        {"name": "out1", "type": "STRING", "links": [1]}
                    ],
                    "properties": {},
                    "widgets_values": [],
                    "pos": [0, 0],
                    "size": [100, 100],
                    "flags": {},
                    "order": 0,
                    "mode": 0
                },
                {
                    "id": 2,
                    "type": "NodeB",
                    "inputs": [
                        {"name": "in1", "type": "STRING", "link": 1}
                    ],
                    "outputs": [],
                    "properties": {},
                    "widgets_values": [],
                    "pos": [0, 0],
                    "size": [100, 100],
                    "flags": {},
                    "order": 0,
                    "mode": 0
                }
            ],
            "links": [
                [1, 1, 0, 2, 0, "STRING"]
            ]
        }

        converter = WorkflowLiteConverter()
        lite = converter.to_lite(workflow)

        # Connection should be embedded in node_b's inputs
        assert "node_b" in lite["nodes"]
        assert "in1" in lite["nodes"]["node_b"]["inputs"]
        # Value should be {node_id, output_name}
        conn = lite["nodes"]["node_b"]["inputs"]["in1"]
        assert isinstance(conn, dict)
        assert conn["node_id"] == 1
        assert conn["output_name"] == "out1"

    def test_round_trip_conversion(self):
        """Test converting standard -> lite -> standard preserves core data."""
        # Create a simple workflow
        original = {
            "id": "test-workflow",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [],
                    "outputs": [
                        {"name": "result", "type": "STRING", "links": []}
                    ],
                    "widgets_values": ["test_value"],
                    "pos": [100, 200],
                    "size": [300, 400],
                    "flags": {},
                    "order": 0,
                    "mode": 0,
                    "properties": {}
                }
            ],
            "links": []
        }

        converter = WorkflowLiteConverter()
        lite = converter.to_lite(original)
        back_to_standard = converter.to_standard(lite)

        # Check core data is preserved
        assert back_to_standard["nodes"][0]["type"] == "TestNode"
        assert back_to_standard["nodes"][0]["widgets_values"] == ["test_value"]

        # UI metadata may be reset to defaults
        assert back_to_standard["nodes"][0]["pos"] == [0, 0]
        assert back_to_standard["nodes"][0]["size"] == [270, 82]


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_to_workflow_lite(self):
        """Test to_workflow_lite convenience function."""
        workflow = {
            "id": "test",
            "nodes": [],
            "links": []
        }

        lite = to_workflow_lite(workflow)
        assert "version" in lite
        assert "nodes" in lite

    def test_to_workflow_standard(self):
        """Test to_workflow_standard convenience function."""
        lite = {
            "version": "1.0",
            "nodes": {}
        }

        standard = to_workflow_standard(lite)
        assert "nodes" in standard


class TestParameterExtraction:
    """Test parameter extraction strategies."""

    def test_parameter_extraction_with_node_info(self):
        """Test parameter extraction using node_info."""
        workflow = {
            "id": "test",
            "nodes": [
                {
                    "id": 1,
                    "type": "CloneAndCacheModel",
                    "inputs": [
                        {
                            "name": "model",
                            "type": "COMBO",
                            "widget": {"name": "model"}
                        }
                    ],
                    "outputs": [
                        {"name": "model_path", "type": "MODEL", "links": []}
                    ],
                    "widgets_values": ["Qwen/Qwen3-0.6B", "/workspace/models/"],
                    "pos": [0, 0],
                    "size": [270, 82],
                    "flags": {},
                    "order": 0,
                    "mode": 0,
                    "properties": {}
                }
            ],
            "links": []
        }

        # Mock node_info
        node_info = {
            "CloneAndCacheModel": {
                "input": {
                    "model": "COMBO",
                    "save_path": "STRING"
                }
            }
        }

        converter = WorkflowLiteConverter(node_info=node_info)
        lite = converter.to_lite(workflow)

        # Parameters should be in inputs dict
        inputs = lite["nodes"]["clone_and_cache_model"]["inputs"]
        assert len(inputs) > 0

    def test_parameter_extraction_fallback(self):
        """Test parameter extraction fallback without node_info."""
        workflow = {
            "id": "test",
            "nodes": [
                {
                    "id": 1,
                    "type": "CustomNode",
                    "inputs": [
                        {"name": "input_value", "type": "STRING", "link": None}
                    ],
                    "outputs": [
                        {"name": "output_value", "type": "STRING", "links": []}
                    ],
                    "widgets_values": ["test_data"],
                    "pos": [0, 0],
                    "size": [270, 82],
                    "flags": {},
                    "order": 0,
                    "mode": 0,
                    "properties": {}
                }
            ],
            "links": []
        }

        converter = WorkflowLiteConverter()  # No node_info
        lite = converter.to_lite(workflow)

        # Should use generic fallback
        node_key = list(lite["nodes"].keys())[0]
        inputs = lite["nodes"][node_key]["inputs"]
        assert len(inputs) > 0


class TestRealWorkflowFiles:
    """Test with real workflow files."""

    def test_convert_llm_test_workflow(self):
        """Test converting the actual llm_test.json workflow."""
        workflow_file = Path(__file__).parent.parent.parent / "examples/openapi/workflows/llm_test.json"
        if not workflow_file.exists():
            pytest.skip("llm_test.json not found")

        with open(workflow_file, "r") as f:
            workflow = json.load(f)

        converter = WorkflowLiteConverter()
        lite = converter.to_lite(workflow)

        # Validate structure
        assert "version" in lite
        assert "nodes" in lite

        # Should have nodes
        assert len(lite["nodes"]) > 0

        # Check that connections are embedded in inputs
        for node_name, node_data in lite["nodes"].items():
            inputs = node_data.get("inputs", {})
            for input_name, input_value in inputs.items():
                if isinstance(input_value, dict):
                    # It's a connection: {node_id, output_name}
                    assert "node_id" in input_value
                    assert "output_name" in input_value

    def test_validate_lite_workflows(self):
        """Validate all lite workflow examples."""
        workflows_dir = Path(__file__).parent.parent.parent / "examples/openapi/workflows"

        for lite_file in workflows_dir.glob("*.lite.json"):
            with open(lite_file, "r") as f:
                lite = json.load(f)

            # Required fields
            assert "nodes" in lite, f"{lite_file} missing 'nodes' field"

            # Validate connections in inputs reference valid nodes
            node_ids = {}
            for node_name, node_data in lite["nodes"].items():
                if "index" in node_data:
                    node_ids[node_data["index"]] = node_name

            for node_name, node_data in lite["nodes"].items():
                inputs = node_data.get("inputs", {})
                for input_name, input_value in inputs.items():
                    if isinstance(input_value, dict) and "node_id" in input_value:
                        source_id = input_value["node_id"]
                        assert source_id in node_ids, \
                            f"{lite_file}: {node_name}.{input_name} references unknown node_id '{source_id}'"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_workflow(self):
        """Test converting an empty workflow."""
        workflow = {"id": "empty", "nodes": [], "links": []}

        converter = WorkflowLiteConverter()
        lite = converter.to_lite(workflow)

        assert "version" in lite
        assert lite["nodes"] == {}

    def test_workflow_without_links(self):
        """Test workflow with nodes but no connections."""
        workflow = {
            "id": "no-links",
            "nodes": [
                {
                    "id": 1,
                    "type": "Node",
                    "inputs": [],
                    "outputs": [],
                    "widgets_values": [],
                    "pos": [0, 0],
                    "size": [100, 100],
                    "flags": {},
                    "order": 0,
                    "mode": 0,
                    "properties": {}
                }
            ],
            "links": []
        }

        converter = WorkflowLiteConverter()
        lite = converter.to_lite(workflow)

        # All inputs should be None or parameter values, no connections
        node_data = lite["nodes"]["node"]
        for input_value in node_data.get("inputs", {}).values():
            assert not isinstance(input_value, dict) or "node_id" not in input_value  # No connections

    def test_node_without_widgets_values(self):
        """Test node with no widgets_values."""
        workflow = {
            "id": "test",
            "nodes": [
                {
                    "id": 1,
                    "type": "SimpleNode",
                    "inputs": [],
                    "outputs": [],
                    "widgets_values": [],
                    "pos": [0, 0],
                    "size": [100, 100],
                    "flags": {},
                    "order": 0,
                    "mode": 0,
                    "properties": {}
                }
            ],
            "links": []
        }

        converter = WorkflowLiteConverter()
        lite = converter.to_lite(workflow)

        # Should have empty inputs
        assert len(lite["nodes"]) == 1
        node_key = list(lite["nodes"].keys())[0]
        assert lite["nodes"][node_key].get("inputs") == {}
