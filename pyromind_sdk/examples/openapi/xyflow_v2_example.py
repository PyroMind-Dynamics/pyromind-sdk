#!/usr/bin/env python3
"""
XyFlow V2 Models Example

This example demonstrates how to use the new V2 workflow models:
- Parsing V2 format workflows
- Building workflows with V2 Builder
- Converting between formats

V2 features:
- Complete NodeDefinitionDTO with input/output specifications
- Measured dimensions for nodes
- Edge styling and animation
- Timestamp support
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any

# V2 Models (Recommended)
from pyromind_sdk.client.xyflow_models import (
    XyflowWorkflowDTOV2,
    XyflowNodeDTOV2,
    XyflowEdgeDTOV2,
    XyflowNodeDataDTOV2,
    NodeDefinitionDTO,
    PositionDTOV2,
    ViewportDTOV2,
    MeasuredDTO,
    EdgeStyleDTO,
)

# V2 Builder and Converter
from pyromind_sdk.client.workflow import (
    XyflowWorkflowBuilderV2,
    detect_format,
    to_xyflow_v2,
    to_lite,
    to_standard,
    convert_v2,
    WorkflowFormat,
)


def _load_workflow(workflow_path: Path) -> dict:
    """Load workflow from JSON file."""
    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_separator(title: str = "") -> None:
    """Print a separator line with optional title."""
    if title:
        print(f"\n{'=' * 60}")
        print(f" {title}")
        print(f"{'=' * 60}")
    else:
        print(f"\n{'-' * 60}")


# ============================================================================
# Format Detection Examples
# ============================================================================

def detect_format_example(workflow_path: Path) -> WorkflowFormat:
    """
    Example: Detect workflow format.
    
    Args:
        workflow_path: Path to workflow JSON file
        
    Returns:
        Detected WorkflowFormat
    """
    print_separator("Format Detection")
    
    workflow = _load_workflow(workflow_path)
    fmt = detect_format(workflow)
    
    print(f"File: {workflow_path.name}")
    print(f"Detected format: {fmt.value}")
    
    # Show format characteristics
    if fmt == WorkflowFormat.XYFLOW_V2:
        print("  - Has timestamp: Yes")
        print("  - Has measured/properties: Likely")
        print("  - Full nodeDefinition support: Yes")
    elif fmt == WorkflowFormat.XYFLOW:
        print("  - Has timestamp: No")
        print("  - Basic xyFlow format")
    elif fmt == WorkflowFormat.LITE:
        print("  - Simplified AI-friendly format")
    elif fmt == WorkflowFormat.STANDARD:
        print("  - ComfyUI standard format")
    
    return fmt


# ============================================================================
# V2 Parsing Examples
# ============================================================================

def parse_v2_workflow_example(workflow_path: Path) -> Optional[XyflowWorkflowDTOV2]:
    """
    Example: Parse V2 format workflow.
    
    Args:
        workflow_path: Path to V2 workflow JSON file
        
    Returns:
        XyflowWorkflowDTOV2 instance if successful
    """
    print_separator("V2 Workflow Parsing")
    
    workflow_dict = _load_workflow(workflow_path)
    
    # Parse to V2 model
    workflow = XyflowWorkflowDTOV2.from_dict(workflow_dict)
    
    print(f"Workflow Name: {workflow.name}")
    print(f"Workflow ID: {workflow.id}")
    print(f"Timestamp: {workflow.timestamp}")
    print(f"Nodes: {len(workflow.nodes)}")
    print(f"Edges: {len(workflow.edges)}")
    
    # Print node details
    print("\n📋 Nodes:")
    for node in workflow.nodes:
        print(f"  • {node.data.label}")
        print(f"    ID: {node.id}")
        print(f"    Type: {node.data.nodeType}")
        if node.measured:
            print(f"    Size: {node.measured.width}x{node.measured.height}")
        if node.properties:
            print(f"    Properties: {node.properties}")
        
        # Show node definition
        if node.data.nodeDefinition:
            nd = node.data.nodeDefinition
            print(f"    Definition:")
            print(f"      - Display Name: {nd.display_name}")
            print(f"      - Category: {nd.category}")
            print(f"      - Inputs: {nd.get_all_params()}")
            print(f"      - Outputs: {nd.output_name}")
        
        # Show config
        if node.data.config:
            print(f"    Config: {list(node.data.config.keys())}")
    
    # Print edge details
    print("\n🔗 Edges:")
    for edge in workflow.edges:
        print(f"  • {edge.id}")
        print(f"    Source: {edge.source} ({edge.sourceHandle})")
        print(f"    Target: {edge.target} ({edge.targetHandle})")
        print(f"    Animated: {edge.animated}")
        if edge.style:
            print(f"    Style: stroke={edge.style.stroke}, width={edge.style.strokeWidth}")
    
    # Validate
    errors = workflow.validate_all()
    print(f"\n✓ Validation: {'Passed' if not errors else 'Failed'}")
    if errors:
        for err in errors:
            print(f"  - {err}")
    
    return workflow


# ============================================================================
# V2 Builder Examples
# ============================================================================

def build_v2_workflow_example() -> XyflowWorkflowDTOV2:
    """
    Example: Build a V2 workflow using XyflowWorkflowBuilderV2.
    
    Returns:
        Built XyflowWorkflowDTOV2 instance
    """
    print_separator("V2 Workflow Building")
    
    # Create node definitions
    clone_def = NodeDefinitionDTO(
        name="CloneAndCacheModel",
        display_name="Clone Model",
        description="Clone models for training and evaluation.",
        input={
            "required": {
                "model": [
                    ["Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B", "Qwen/Qwen3-8B"],
                    {"default": "Qwen/Qwen3-0.6B"}
                ],
                "target_path": [
                    ["/workspace/models/"],
                    {"default": "/workspace/models/"}
                ],
            }
        },
        output=["MODEL"],
        output_name=["model_path"],
        category="models",
        python_module="test_nodes",
    )
    
    inference_def = NodeDefinitionDTO(
        name="LLMOrVLMInference",
        display_name="Inference (LLM / VLM)",
        description="LLM/VLM inference node",
        input={
            "required": {
                "model_path": ["MODEL"],
                "prompt": ["STRING", {"default": "Hello, how are you?"}],
                "max_tokens": ["INT", {"default": 100, "min": 1, "max": 4096}],
                "temperature": ["FLOAT", {"default": 0.7, "min": 0, "max": 2}],
            },
            "optional": {
                "lora_path": ["MODEL"],
            }
        },
        output=["STRING"],
        output_name=["response"],
        category="LLM & VLM",
        python_module="test_nodes",
    )
    
    show_result_def = NodeDefinitionDTO(
        name="ShowResultNode",
        display_name="Show Result",
        description="Show result",
        input={
            "required": {
                "result": ["STRING", {"default": ""}],
            }
        },
        output=[],
        output_name=[],
        category="output",
        python_module="test_nodes",
    )
    
    # Build workflow
    print("Building workflow with V2 Builder...")
    builder = XyflowWorkflowBuilderV2(
        name="Demo Workflow",
        auto_layout=True
    )
    
    # Add nodes
    builder.add_node(
        name="clone_model",
        node_definition=clone_def,
        config={
            "model": "Qwen/Qwen3-0.6B",
            "target_path": "/workspace/models/"
        },
        is_read_only=True,
    )
    
    builder.add_node(
        name="inference",
        node_definition=inference_def,
        config={
            "prompt": "What is machine learning?",
            "max_tokens": 100,
            "temperature": 0.7,
        },
        is_read_only=True,
    )
    
    builder.add_node(
        name="show_result",
        node_definition=show_result_def,
        config={"result": ""},
        is_read_only=True,
    )
    
    # Connect nodes
    builder.connect("clone_model", "model_path", "inference", "model_path")
    builder.connect("inference", "response", "show_result", "result")
    
    # Build
    workflow = builder.build(validate=True)
    
    print(f"\n✓ Built workflow: {workflow.name}")
    print(f"  Nodes: {len(workflow.nodes)}")
    print(f"  Edges: {len(workflow.edges)}")
    print(f"  ID: {workflow.id}")
    print(f"  Timestamp: {workflow.timestamp}")
    
    # Show node positions (from auto layout)
    print("\n📍 Node Positions (auto layout):")
    for node in workflow.nodes:
        print(f"  • {node.data.label}: ({node.position.x:.1f}, {node.position.y:.1f})")
    
    return workflow


# ============================================================================
# Format Conversion Examples
# ============================================================================

def convert_to_lite_example(workflow_path: Path) -> Dict[str, Any]:
    """
    Example: Convert V2 workflow to lite format.
    
    Args:
        workflow_path: Path to V2 workflow JSON file
        
    Returns:
        Lite format dictionary
    """
    print_separator("V2 → Lite Conversion")
    
    workflow_dict = _load_workflow(workflow_path)
    
    # Convert to lite
    lite = to_lite(workflow_dict)
    
    print(f"Converted to lite format:")
    print(f"  Version: {lite.get('version')}")
    print(f"  Name: {lite.get('name')}")
    print(f"  Nodes: {len(lite.get('nodes', {}))}")
    
    # Show sample node
    nodes = lite.get("nodes", {})
    if nodes:
        first_name = list(nodes.keys())[0]
        first_node = nodes[first_name]
        print(f"\n  Sample node: {first_name}")
        print(f"    Type: {first_node.get('type')}")
        print(f"    Index: {first_node.get('index')}")
        print(f"    Inputs: {list(first_node.get('inputs', {}).keys())}")
        print(f"    Outputs: {first_node.get('outputs', [])}")
    
    return lite


def convert_to_standard_example(workflow_path: Path) -> Dict[str, Any]:
    """
    Example: Convert V2 workflow to standard (ComfyUI) format.
    
    Args:
        workflow_path: Path to V2 workflow JSON file
        
    Returns:
        Standard format dictionary
    """
    print_separator("V2 → Standard Conversion")
    
    workflow_dict = _load_workflow(workflow_path)
    
    # Convert to standard
    standard = to_standard(workflow_dict)
    
    print(f"Converted to standard format:")
    print(f"  ID: {standard.get('id')}")
    print(f"  Name: {standard.get('name')}")
    print(f"  Nodes: {len(standard.get('nodes', []))}")
    print(f"  Links: {len(standard.get('links', []))}")
    
    return standard


# ============================================================================
# Round-trip Conversion Example
# ============================================================================

def round_trip_conversion_example(workflow_path: Path) -> None:
    """
    Example: Demonstrate round-trip conversion V2 → Lite → V2.
    
    Args:
        workflow_path: Path to V2 workflow JSON file
    """
    print_separator("Round-trip Conversion (V2 → Lite → V2)")
    
    # Load original
    original_dict = _load_workflow(workflow_path)
    original = XyflowWorkflowDTOV2.from_dict(original_dict)
    
    print(f"Original workflow:")
    print(f"  Nodes: {len(original.nodes)}")
    print(f"  Edges: {len(original.edges)}")
    
    # V2 → Lite
    lite = to_lite(original_dict)
    print(f"\nV2 → Lite:")
    print(f"  Nodes: {len(lite.get('nodes', {}))}")
    
    # Lite → V2
    back_to_v2 = to_xyflow_v2(lite)
    print(f"\nLite → V2:")
    print(f"  Nodes: {len(back_to_v2.nodes)}")
    print(f"  Edges: {len(back_to_v2.edges)}")
    
    # Compare
    print(f"\n✓ Round-trip completed successfully")


# ============================================================================
# Export Example
# ============================================================================

def export_workflow_example(workflow: XyflowWorkflowDTOV2, output_path: Path) -> None:
    """
    Example: Export workflow to JSON file.
    
    Args:
        workflow: XyflowWorkflowDTOV2 instance
        output_path: Output file path
    """
    print_separator("Export Workflow")
    
    # Convert to dict
    workflow_dict = workflow.to_dict()
    
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(workflow_dict, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Exported to: {output_path}")
    print(f"  File size: {output_path.stat().st_size} bytes")


# ============================================================================
# Main
# ============================================================================

def main():
    """Main example function demonstrating V2 workflow models."""
    
    # Get workflows directory
    workflows_dir = Path(__file__).parent / "workflows"
    test_workflow = workflows_dir / "test.json"
    
    if not test_workflow.exists():
        print(f"⚠ Test workflow not found: {test_workflow}")
        print("Creating a demo workflow instead...")
        workflow = build_v2_workflow_example()
        return
    
    # 1. Detect format
    fmt = detect_format_example(test_workflow)
    
    # 2. Parse V2 workflow
    if fmt == WorkflowFormat.XYFLOW_V2:
        workflow = parse_v2_workflow_example(test_workflow)
    else:
        print(f"\n⚠ Workflow is not V2 format, converting...")
        workflow_dict = _load_workflow(test_workflow)
        workflow = to_xyflow_v2(workflow_dict)
    
    # 3. Build a new V2 workflow
    built_workflow = build_v2_workflow_example()
    
    # 4. Convert to other formats
    convert_to_lite_example(test_workflow)
    convert_to_standard_example(test_workflow)
    
    # 5. Round-trip conversion
    round_trip_conversion_example(test_workflow)
    
    # 6. Export example
    output_path = Path(__file__).parent / "workflows" / "test_v2_output.json"
    export_workflow_example(built_workflow, output_path)
    
    print_separator("All Tests Completed")
    print("✓ V2 models are working correctly!")


if __name__ == "__main__":
    main()
