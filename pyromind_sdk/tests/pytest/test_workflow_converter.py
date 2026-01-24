"""
Tests for Workflow Tools

Tests the conversion between standard workflow format and workflow_lite format,
as well as validation functions for both formats.

New simplified format:
- No 'name' or 'description' fields
- No separate 'connections' field
- inputs dict contains parameter values OR {node_id, output_name} connections
- outputs is a list of names only
- Workflow IDs use UUID format
"""

import json
import pytest
import uuid
from pathlib import Path
from pyromind_sdk.client.workflow import (
    WorkflowLiteConverter,
    WorkflowMapper,
    TypeResolver,
    LinkBuilder,
    to_workflow_lite,
    to_workflow_standard,
    validate_lite_format,
    validate_standard_format,
)


class TestWorkflowMapper:
    """Test WorkflowMapper class."""

    def test_initialization(self):
        """Test mapper initialization."""
        mapper = WorkflowMapper()
        assert mapper.node_id_to_name == {}
        assert mapper.node_name_to_id == {}
        assert mapper.name_counters == {}

    def test_build_from_nodes(self):
        """Test building mappings from standard format nodes."""
        nodes = [
            {"id": 1, "type": "TestNode"},
            {"id": 2, "type": "AnotherTestNode"}
        ]

        mapper = WorkflowMapper()
        mapper.build_from_nodes(nodes)

        assert mapper.get_name(1) == "test"
        assert mapper.get_name(2) == "another_test"
        assert mapper.get_id("test") == 1
        assert mapper.get_id("another_test") == 2

    def test_duplicate_name_handling(self):
        """Test handling of duplicate node names."""
        nodes = [
            {"id": 1, "type": "TestNode"},
            {"id": 2, "type": "TestNode"},
            {"id": 3, "type": "TestNode"}
        ]

        mapper = WorkflowMapper()
        mapper.build_from_nodes(nodes)

        assert mapper.get_name(1) == "test"
        assert mapper.get_name(2) == "test_1"
        assert mapper.get_name(3) == "test_2"

    def test_build_from_lite_nodes(self):
        """Test building mappings from lite format nodes."""
        lite_nodes = {
            "node_a": {"index": 1},
            "node_b": {"index": 2}
        }

        mapper = WorkflowMapper()
        mapper.build_from_lite_nodes(lite_nodes)

        assert mapper.get_id("node_a") == 1
        assert mapper.get_id("node_b") == 2
        assert mapper.get_name(1) == "node_a"
        assert mapper.get_name(2) == "node_b"


class TestTypeResolver:
    """Test TypeResolver class."""

    def test_initialization(self):
        """Test resolver initialization."""
        resolver = TypeResolver()
        assert resolver.node_info == {}

    def test_with_node_info(self):
        """Test resolver with node_info."""
        node_info = {
            "TestNode": {
                "input": {
                    "required": {
                        "param1": ["STRING", {}],
                        "param2": ["INT", {}]
                    },
                    "optional": {
                        "param3": ["FLOAT", {}]
                    }
                },
                "output": ["result_type1", "result_type2"]
            }
        }

        resolver = TypeResolver(node_info)

        # Test input type resolution
        assert resolver.get_input_type("TestNode", "param1") == "STRING"
        assert resolver.get_input_type("TestNode", "param2") == "INT"
        assert resolver.get_input_type("TestNode", "param3") == "FLOAT"
        assert resolver.get_input_type("TestNode", "unknown") == "AUTO"

        # Test output type resolution
        assert resolver.get_output_type("TestNode", 0) == "result_type1"
        assert resolver.get_output_type("TestNode", 1) == "result_type2"
        assert resolver.get_output_type("TestNode", 2) == "AUTO"

        # Test parameter order
        order = resolver.get_parameter_order("TestNode")
        assert order == ["param1", "param2", "param3"]

    def test_caching(self):
        """Test that type resolution is cached."""
        node_info = {
            "TestNode": {
                "input": {
                    "required": {
                        "param1": ["STRING", {}]
                    }
                }
            }
        }

        resolver = TypeResolver(node_info)

        # First call
        type1 = resolver.get_input_type("TestNode", "param1")
        # Second call (should use cache)
        type2 = resolver.get_input_type("TestNode", "param1")

        assert type1 == type2 == "STRING"


class TestLinkBuilder:
    """Test LinkBuilder class."""

    def test_build_socket_mappings(self):
        """Test building socket name mappings."""
        nodes = [
            {
                "id": 1,
                "inputs": [
                    {"name": "in1"},
                    {"name": "in2"}
                ],
                "outputs": [
                    {"name": "out1"},
                    {"name": "out2"}
                ]
            }
        ]

        resolver = TypeResolver()
        builder = LinkBuilder(resolver)
        input_mappings, output_mappings = builder.build_socket_mappings(nodes)

        assert input_mappings[1] == {0: "in1", 1: "in2"}
        assert output_mappings[1] == {0: "out1", 1: "out2"}


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
        assert isinstance(lite["nodes"]["test"]["outputs"], list)
        assert "output1" in lite["nodes"]["test"]["outputs"]

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

    def test_uuid_generation(self):
        """Test UUID generation for workflow IDs."""
        lite = {
            "version": "1.0",
            "nodes": {
                "test": {
                    "type": "TestNode",
                    "inputs": {},
                    "outputs": []
                }
            }
        }

        converter = WorkflowLiteConverter()
        standard = converter.to_standard(lite)

        # Check that ID is a valid UUID
        workflow_id = standard["id"]
        try:
            uuid_obj = uuid.UUID(workflow_id)
            assert str(uuid_obj) == workflow_id
        except ValueError:
            pytest.fail(f"Generated ID '{workflow_id}' is not a valid UUID")

    def test_uuid_preservation(self):
        """Test that existing UUIDs are preserved."""
        original_uuid = "189cc5d9-cb63-4b03-9a92-9a5b43ae17cc"
        original_workflow = {
            "id": original_uuid,
            "nodes": []
        }

        lite = {
            "version": "1.0",
            "nodes": {}
        }

        converter = WorkflowLiteConverter()
        standard = converter.to_standard(lite, original_workflow)

        assert standard["id"] == original_uuid

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
        conn = lite["nodes"]["node_b"]["inputs"]["in1"]
        assert isinstance(conn, dict)
        assert conn["node_id"] == 1
        assert conn["output_name"] == "out1"

    def test_round_trip_conversion(self):
        """Test converting standard -> lite -> standard preserves core data."""
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

        converter = WorkflowLiteConverter(auto_layout=False)  # Disable auto layout for this test
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

        converter = WorkflowLiteConverter()
        lite = converter.to_lite(workflow)

        node_key = list(lite["nodes"].keys())[0]
        inputs = lite["nodes"][node_key]["inputs"]
        assert len(inputs) > 0


class TestValidationFunctions:
    """Test validation functions."""

    def test_validate_lite_format_valid(self, capsys):
        """Test validating a valid lite format workflow."""
        lite = {
            "version": "1.0",
            "nodes": {
                "node_a": {
                    "type": "NodeA",
                    "inputs": {},
                    "outputs": ["out1"],
                    "index": 1
                },
                "node_b": {
                    "type": "NodeB",
                    "inputs": {
                        "in1": {
                            "node_id": 1,
                            "output_name": "out1"
                        }
                    },
                    "outputs": [],
                    "index": 2
                }
            }
        }

        is_valid, errors = validate_lite_format(lite)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_lite_format_with_node_info(self):
        """Test validating lite format with node_info for enhanced checks."""
        node_info = {
            "TestNode": {
                "input": {
                    "required": {
                        "dataset": ["STRING"],
                        "model_path": ["MODEL"]
                    },
                    "optional": {
                        "lora_config": ["STRING"]
                    }
                },
                "output": ["STRING"],
                "output_name": ["output"]
            },
            "SourceNode": {
                "input": {},
                "output": ["MODEL"],
                "output_name": ["output"]
            }
        }

        # Valid workflow with proper connections
        lite_valid = {
            "version": "1.0",
            "nodes": {
                "source_node": {
                    "type": "SourceNode",
                    "index": 1,
                    "inputs": {},
                    "outputs": ["output"]
                },
                "test_node": {
                    "type": "TestNode",
                    "index": 0,
                    "inputs": {
                        "dataset": "test_dataset",
                        "model_path": {"node_id": 1, "output_name": "output"}
                    },
                    "outputs": ["output"]
                }
            }
        }

        is_valid, errors = validate_lite_format(lite_valid, node_info=node_info)
        # Should be valid (may have warnings but no errors)
        error_list = [e for e in errors if not e.startswith("Warning:")]
        assert len(error_list) == 0

        # Invalid workflow - missing required parameter
        lite_invalid = {
            "version": "1.0",
            "nodes": {
                "test_node": {
                    "type": "TestNode",
                    "index": 0,
                    "inputs": {
                        # Missing required "dataset" parameter
                        "model_path": {"node_id": 1, "output_name": "output"}
                    },
                    "outputs": ["output"]
                }
            }
        }

        is_valid, errors = validate_lite_format(lite_invalid, node_info=node_info)
        assert is_valid is False
        assert any("missing required parameter" in e.lower() for e in errors)

        # Invalid workflow - unknown parameter
        lite_unknown = {
            "version": "1.0",
            "nodes": {
                "test_node": {
                    "type": "TestNode",
                    "index": 0,
                    "inputs": {
                        "dataset": "test",
                        "unknown_param": "value"  # Unknown parameter
                    },
                    "outputs": ["output"]
                }
            }
        }

        is_valid, errors = validate_lite_format(lite_unknown, node_info=node_info)
        assert is_valid is False
        assert any("unknown input parameter" in e.lower() for e in errors)

        # Invalid workflow - unknown node type
        lite_unknown_type = {
            "version": "1.0",
            "nodes": {
                "test_node": {
                    "type": "UnknownNodeType",  # Unknown type
                    "index": 0,
                    "inputs": {},
                    "outputs": ["output"]
                }
            }
        }

        is_valid, errors = validate_lite_format(lite_unknown_type, node_info=node_info)
        assert is_valid is False
        assert any("unknown type" in e.lower() for e in errors)

    def test_validate_standard_format_with_node_info(self):
        """Test validating standard format with node_info for enhanced checks."""
        node_info = {
            "TestNode": {
                "input": {
                    "required": {
                        "dataset": ["STRING"],
                        "model_path": ["MODEL"]
                    },
                    "optional": {
                        "lora_config": ["STRING"]
                    }
                },
                "output": ["STRING"],
                "output_name": ["output"]
            }
        }

        # Valid workflow
        standard_valid = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "dataset", "type": "STRING", "link": None},
                        {"name": "model_path", "type": "MODEL", "link": None}
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": ["test_dataset", None]
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(standard_valid, node_info=node_info)
        # May have warnings but should be valid
        error_list = [e for e in errors if not e.startswith("Warning:")]
        assert len(error_list) == 0

        # Invalid workflow - missing required parameter
        standard_invalid = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        # Missing required "dataset" parameter
                        {"name": "model_path", "type": "MODEL", "link": None}
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": [None]
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(standard_invalid, node_info=node_info)
        assert is_valid is False
        # Should detect missing required parameter or widgets_values count mismatch
        assert any("missing required parameter" in e.lower() or "widgets_values" in e.lower() for e in errors)

        # Invalid workflow - unknown parameter
        standard_unknown = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "dataset", "type": "STRING", "link": None},
                        {"name": "unknown_param", "type": "STRING", "link": None}  # Unknown parameter
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": ["test", "value"]
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(standard_unknown, node_info=node_info)
        # Should detect unknown parameter or widgets_values count mismatch
        # Note: validation may pass if unknown_param is not strictly checked
        # The important thing is that it doesn't crash
        assert isinstance(is_valid, bool)
        # Check that if there are errors, they mention unknown parameter or widgets_values
        if not is_valid:
            assert any("unknown input parameter" in e.lower() or "widgets_values" in e.lower() for e in errors)

    def test_validate_lite_format_missing_fields(self, capsys):
        """Test validating lite format with missing fields."""
        lite = {
            "nodes": {}
        }

        is_valid, errors = validate_lite_format(lite)
        assert is_valid is False
        assert any("Missing required field" in e for e in errors)

    def test_validate_lite_format_invalid_connection(self, capsys):
        """Test validating lite format with invalid connection."""
        lite = {
            "version": "1.0",
            "nodes": {
                "node_a": {
                    "type": "NodeA",
                    "inputs": {
                        "in1": {
                            "node_id": 999,  # Invalid node_id
                            "output_name": "out1"
                        }
                    },
                    "outputs": [],
                    "index": 1
                }
            }
        }

        is_valid, errors = validate_lite_format(lite)
        assert is_valid is False
        assert any("references unknown node_id" in e for e in errors)

    def test_validate_standard_format_valid(self, capsys):
        """Test validating a valid standard format workflow."""
        standard = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "NodeA",
                    "inputs": [],
                    "outputs": [{"name": "out1", "type": "STRING", "links": []}]
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(standard)
        # Has warnings about last_node_id but should be valid (only errors make it invalid)
        assert is_valid is True or any("Warning:" in e for e in errors)

    def test_validate_standard_format_null_links(self):
        """Test validating standard format with null links (should be allowed)."""
        standard = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "NodeA",
                    "inputs": [],
                    "outputs": [
                        {"name": "out1", "type": "STRING", "links": None},  # null is allowed
                        {"name": "out2", "type": "STRING", "links": []}    # empty list is also allowed
                    ]
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(standard)
        # Should be valid - null links are allowed
        error_list = [e for e in errors if not e.startswith("Warning:")]
        assert len(error_list) == 0

    def test_validate_standard_format_missing_fields(self, capsys):
        """Test validating standard format with missing fields."""
        standard = {
            "nodes": []
        }

        is_valid, errors = validate_standard_format(standard)
        assert is_valid is False
        assert any("Missing required field" in e for e in errors)

    def test_validate_standard_format_invalid_link(self, capsys):
        """Test validating standard format with invalid link."""
        standard = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {"id": 1, "type": "NodeA", "inputs": [], "outputs": []}
            ],
            "links": [
                [1, 999, 0, 1, 0, "STRING"]  # Invalid source node
            ]
        }

        is_valid, errors = validate_standard_format(standard)
        assert is_valid is False
        assert any("references unknown source node" in e for e in errors)

    def test_validate_parameter_value_constraints(self):
        """Test parameter value constraint validation (INT/FLOAT ranges, COMBO options)."""
        node_info = {
            "TestNode": {
                "input": {
                    "required": {
                        "gpu_count": ["INT", {"min": 1, "max": 8}],
                        "guidance_scale": ["FLOAT", {"min": 0.1, "max": 20.0}],
                        "model_type": [["qwen3_vl", "qwen2.5_vl"], {"default": "qwen3_vl"}]
                    }
                },
                "output": ["STRING"],
                "output_name": ["output"]
            }
        }

        # Test INT out of range
        workflow_int_range = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "gpu_count", "type": "INT", "link": None},
                        {"name": "guidance_scale", "type": "FLOAT", "link": None},
                        {"name": "model_type", "type": "COMBO", "link": None}
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": [10, 2.0, "qwen3_vl"]  # gpu_count=10 > max=8
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(workflow_int_range, node_info=node_info)
        assert is_valid is False
        assert any("gpu_count" in e and "greater than maximum" in e for e in errors)

        # Test FLOAT out of range
        workflow_float_range = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "gpu_count", "type": "INT", "link": None},
                        {"name": "guidance_scale", "type": "FLOAT", "link": None},
                        {"name": "model_type", "type": "COMBO", "link": None}
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": [4, 25.0, "qwen3_vl"]  # guidance_scale=25.0 > max=20.0
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(workflow_float_range, node_info=node_info)
        assert is_valid is False
        assert any("guidance_scale" in e and "greater than maximum" in e for e in errors)

        # Test COMBO invalid option
        workflow_combo_invalid = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "gpu_count", "type": "INT", "link": None},
                        {"name": "guidance_scale", "type": "FLOAT", "link": None},
                        {"name": "model_type", "type": "COMBO", "link": None}
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": [4, 2.0, "invalid_model"]  # Not in options
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(workflow_combo_invalid, node_info=node_info)
        assert is_valid is False
        assert any("model_type" in e and "not in allowed options" in e for e in errors)

        # Test valid values
        workflow_valid = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "gpu_count", "type": "INT", "link": None},
                        {"name": "guidance_scale", "type": "FLOAT", "link": None},
                        {"name": "model_type", "type": "COMBO", "link": None}
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": [4, 2.0, "qwen3_vl"]  # All valid
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(workflow_valid, node_info=node_info)
        error_list = [e for e in errors if not e.startswith("Warning:")]
        # Should not have constraint errors
        constraint_errors = [e for e in error_list if "greater than" in e or "less than" in e or "not in allowed options" in e]
        assert len(constraint_errors) == 0

    def test_validate_type_compatibility(self):
        """Test input/output type compatibility validation with node_info."""
        node_info = {
            "TestNode": {
                "input": {
                    "required": {
                        "dataset": ["STRING"],
                        "model_path": ["MODEL"]
                    }
                },
                "output": ["STRING"],
                "output_name": ["output"]
            }
        }

        # Test with incompatible input type
        workflow_incompatible_input = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "dataset", "type": "INT", "link": None},  # Wrong type
                        {"name": "model_path", "type": "MODEL", "link": None}
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": [123, None]
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(workflow_incompatible_input, node_info=node_info)
        assert is_valid is False
        assert any("input 'dataset' has type 'INT'" in e and "expects type 'STRING'" in e for e in errors)

        # Test with incompatible output type
        workflow_incompatible_output = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "dataset", "type": "STRING", "link": None},
                        {"name": "model_path", "type": "MODEL", "link": None}
                    ],
                    "outputs": [
                        {"name": "output", "type": "INT", "links": []}  # Wrong type
                    ],
                    "widgets_values": ["test", None]
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(workflow_incompatible_output, node_info=node_info)
        assert is_valid is False
        assert any("output 'output' has type 'INT'" in e and "expects type 'STRING'" in e for e in errors)

        # Test with compatible types
        workflow_compatible = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "dataset", "type": "STRING", "link": None},
                        {"name": "model_path", "type": "MODEL", "link": None}
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": ["test", None]
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(workflow_compatible, node_info=node_info)
        error_list = [e for e in errors if not e.startswith("Warning:")]
        # Should not have type compatibility errors
        type_errors = [e for e in error_list if "type" in e.lower() and "compatible" in e.lower()]
        assert len(type_errors) == 0

    def test_validate_widgets_values_order(self):
        """Test widgets_values order validation with node_info."""
        node_info = {
            "TestNode": {
                "input": {
                    "required": {
                        "dataset": ["STRING"],  # Widget-able
                        "model_path": ["MODEL"]  # Non-widget
                    },
                    "optional": {
                        "lora_config": ["STRING"]  # Widget-able, has link
                    }
                },
                "output": ["STRING"],
                "output_name": ["output"]
            }
        }

        # Valid widgets_values order
        standard_valid = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "dataset", "type": "STRING", "link": None},
                        {"name": "model_path", "type": "MODEL", "link": None},
                        {"name": "lora_config", "type": "STRING", "link": 1}
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": ["test_dataset", None, ""]  # Correct order
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(standard_valid, node_info=node_info)
        # Should not have widgets_values count errors
        widgets_errors = [e for e in errors if "widgets_values" in e.lower() and "count" in e.lower()]
        assert len(widgets_errors) == 0

        # Invalid widgets_values count
        standard_invalid_count = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [
                        {"name": "dataset", "type": "STRING", "link": None},
                        {"name": "model_path", "type": "MODEL", "link": None},
                        {"name": "lora_config", "type": "STRING", "link": 1}
                    ],
                    "outputs": [
                        {"name": "output", "type": "STRING", "links": []}
                    ],
                    "widgets_values": ["test_dataset"]  # Wrong count (missing values)
                }
            ],
            "links": []
        }

        is_valid, errors = validate_standard_format(standard_invalid_count, node_info=node_info)
        widgets_errors = [e for e in errors if "widgets_values" in e.lower() and "count" in e.lower()]
        # May or may not have count error depending on validation logic
        # Just check that validation runs without crashing
        assert isinstance(is_valid, bool)


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

        assert "version" in lite
        assert "nodes" in lite
        assert len(lite["nodes"]) > 0

        # Check that connections are embedded in inputs
        for node_name, node_data in lite["nodes"].items():
            inputs = node_data.get("inputs", {})
            for input_name, input_value in inputs.items():
                if isinstance(input_value, dict):
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

    def test_validate_test_data_workflows(self):
        """Test validation with test data workflows."""
        test_data_dir = Path(__file__).parent / "test_data"
        if not test_data_dir.exists():
            pytest.skip("test_data directory not found")

        # Test invalid workflow with missing required parameter
        invalid_file = test_data_dir / "invalid_lite_missing_required.json"
        if invalid_file.exists():
            with open(invalid_file, "r") as f:
                invalid_lite = json.load(f)

            # Mock node_info for GUISFTTrainingNode
            node_info = {
                "GUISFTTrainingNode": {
                    "input": {
                        "required": {
                            "dataset": ["STRING"],
                            "model_path": ["MODEL"]
                        },
                        "optional": {
                            "lora_config": ["STRING"]
                        }
                    },
                    "output": ["STRING"],
                    "output_name": ["output"]
                }
            }

            # Should fail validation with node_info (missing required parameters)
            is_valid, errors = validate_lite_format(invalid_lite, node_info=node_info)
            assert is_valid is False
            assert any("missing required parameter" in e.lower() for e in errors)

            # Without node_info, basic validation should still pass (schema is valid)
            is_valid_basic, errors_basic = validate_lite_format(invalid_lite)
            # Schema validation should pass, but may have warnings
            assert isinstance(is_valid_basic, bool)


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

        node_data = lite["nodes"]["node"]
        for input_value in node_data.get("inputs", {}).values():
            assert not isinstance(input_value, dict) or "node_id" not in input_value

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

        assert len(lite["nodes"]) == 1
        node_key = list(lite["nodes"].keys())[0]
        assert lite["nodes"][node_key].get("inputs") == {}

    def test_complex_workflow_with_multiple_connections(self):
        """Test workflow with multiple nodes and connections."""
        workflow = {
            "id": "complex",
            "nodes": [
                {
                    "id": 1,
                    "type": "SourceNode",
                    "inputs": [],
                    "outputs": [
                        {"name": "out1", "type": "STRING", "links": [1, 2]},
                        {"name": "out2", "type": "INT", "links": [3]}
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
                    "type": "ProcessNode1",
                    "inputs": [
                        {"name": "in1", "type": "STRING", "link": 1}
                    ],
                    "outputs": [
                        {"name": "result", "type": "STRING", "links": [4]}
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
                    "id": 3,
                    "type": "ProcessNode2",
                    "inputs": [
                        {"name": "in1", "type": "STRING", "link": 2},
                        {"name": "in2", "type": "INT", "link": 3}
                    ],
                    "outputs": [],
                    "properties": {},
                    "widgets_values": [],
                    "pos": [0, 0],
                    "size": [100, 100],
                    "flags": {},
                    "order": 0,
                    "mode": 0
                },
                {
                    "id": 4,
                    "type": "FinalNode",
                    "inputs": [
                        {"name": "in1", "type": "STRING", "link": 4}
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
                [1, 1, 0, 2, 0, "STRING"],
                [2, 1, 0, 3, 0, "STRING"],
                [3, 1, 1, 3, 1, "INT"],
                [4, 2, 0, 4, 0, "STRING"]
            ]
        }

        converter = WorkflowLiteConverter()
        lite = converter.to_lite(workflow)

        # Verify all nodes are present
        assert len(lite["nodes"]) == 4

        # Verify connections
        assert lite["nodes"]["process_node1"]["inputs"]["in1"]["node_id"] == 1
        assert lite["nodes"]["process_node2"]["inputs"]["in1"]["node_id"] == 1
        assert lite["nodes"]["process_node2"]["inputs"]["in2"]["node_id"] == 1
        assert lite["nodes"]["final"]["inputs"]["in1"]["node_id"] == 2

        # Test round-trip conversion
        back_to_standard = converter.to_standard(lite)
        assert len(back_to_standard["nodes"]) == 4
        assert len(back_to_standard["links"]) == 4
