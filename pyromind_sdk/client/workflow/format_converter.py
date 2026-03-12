"""
Workflow Format Converter

Provides conversion between different workflow formats:
- xyFlow V2: React Flow format with full nodeDefinition (recommended)
- xyFlow Legacy: Legacy format (deprecated)
- Lite: Simplified format (AI-friendly, readable)
- Standard: ComfyUI format (complex structure)

V2 Usage (Recommended):
    ```python
    from pyromind_sdk.client.workflow.format_converter import (
        detect_format,
        to_xyflow_v2,
        to_xyflow,
        to_lite,
        to_standard,
        convert_v2,
    )
    
    # Auto-detect and convert to V2
    format_type = detect_format(workflow_dict)
    xyflow_v2 = to_xyflow_v2(workflow_dict, node_info=node_info)
    
    # Convert between formats
    lite = to_lite(workflow_dict, node_info=node_info)
    standard = to_standard(workflow_dict, node_info=node_info)
    ```
"""
import warnings
import time
from typing import Dict, List, Any, Optional, Literal, Union
from enum import Enum
from datetime import datetime

# V2 Models (Recommended)
from ..xyflow_models import (
    XyflowWorkflowDTOV2,
    XyflowNodeDTOV2,
    XyflowEdgeDTOV2,
    XyflowNodeDataDTOV2,
    NodeDefinitionDTO,
    PositionDTOV2,
    ViewportDTOV2,
    MeasuredDTO,
    EdgeStyleDTO,
    InputDefinitionDTO,
)

# Legacy Models (Deprecated)
from ..xyflow_models import (
    XyflowWorkflowDTO,
    XyflowNodeDTO,
    XyflowEdgeDTO,
    XyflowNodeDataDTO,
    PositionDTO,
    ViewportDTO,
)


class WorkflowFormat(str, Enum):
    """Supported workflow formats"""
    XYFLOW_V2 = "xyflow_v2"
    XYFLOW = "xyflow"
    LITE = "lite"
    STANDARD = "standard"
    UNKNOWN = "unknown"


# ==================== Format Detection ====================

def detect_format(workflow: Dict[str, Any]) -> WorkflowFormat:
    """
    Detect the format of a workflow.
    
    Args:
        workflow: Workflow dictionary
        
    Returns:
        Detected format type
    """
    if not isinstance(workflow, dict):
        return WorkflowFormat.UNKNOWN
    
    # xyFlow V2 format: has 'nodes' and 'edges' arrays, nodes have 'measured' or full 'nodeDefinition'
    if "nodes" in workflow and "edges" in workflow:
        if isinstance(workflow["nodes"], list) and isinstance(workflow["edges"], list):
            # Check if it's V2 format (has measured or timestamp)
            if workflow.get("timestamp"):
                return WorkflowFormat.XYFLOW_V2
            # Check nodes for V2 indicators
            nodes = workflow.get("nodes", [])
            if nodes and isinstance(nodes[0], dict):
                if "measured" in nodes[0] or "properties" in nodes[0]:
                    return WorkflowFormat.XYFLOW_V2
            return WorkflowFormat.XYFLOW
    
    # Lite format: has 'nodes' dict with 'type' field
    if "nodes" in workflow and "version" in workflow:
        nodes = workflow.get("nodes")
        if isinstance(nodes, dict):
            for node_data in nodes.values():
                if isinstance(node_data, dict) and "type" in node_data:
                    return WorkflowFormat.LITE
    
    # Standard (ComfyUI) format: has 'links' array
    if "links" in workflow and isinstance(workflow["links"], list):
        return WorkflowFormat.STANDARD
    
    return WorkflowFormat.UNKNOWN


# ==================== V2 xyFlow Conversions ====================

def to_xyflow_v2(
    workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> XyflowWorkflowDTOV2:
    """
    Convert any workflow format to xyFlow V2.
    
    Args:
        workflow: Source workflow dictionary
        node_info: Optional node definitions for enrichment
        
    Returns:
        XyflowWorkflowDTOV2 instance
        
    Raises:
        ValueError: If format is unknown or conversion fails
    """
    fmt = detect_format(workflow)
    
    if fmt == WorkflowFormat.XYFLOW_V2:
        return XyflowWorkflowDTOV2.from_dict(workflow)
    elif fmt == WorkflowFormat.XYFLOW:
        return _xyflow_legacy_to_v2(workflow, node_info)
    elif fmt == WorkflowFormat.LITE:
        return _lite_to_xyflow_v2(workflow, node_info)
    elif fmt == WorkflowFormat.STANDARD:
        return _standard_to_xyflow_v2(workflow, node_info)
    else:
        raise ValueError(f"Cannot convert unknown format to xyFlow V2")


def _xyflow_legacy_to_v2(
    xyflow_workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> XyflowWorkflowDTOV2:
    """Convert legacy xyFlow format to V2."""
    nodes = xyflow_workflow.get("nodes", [])
    edges = xyflow_workflow.get("edges", [])
    
    # Convert nodes
    v2_nodes = []
    for node_dict in nodes:
        data = node_dict.get("data", {})
        
        # Parse node definition
        node_def_dict = data.get("nodeDefinition", {})
        node_def = None
        if node_def_dict:
            if isinstance(node_def_dict, NodeDefinitionDTO):
                node_def = node_def_dict
            else:
                try:
                    node_def = NodeDefinitionDTO.model_validate(node_def_dict)
                except Exception:
                    node_def = NodeDefinitionDTO(
                        name=data.get("nodeType", ""),
                        display_name=data.get("label", ""),
                        description="",
                        input={}
                    )
        else:
            node_def = NodeDefinitionDTO(
                name=data.get("nodeType", ""),
                display_name=data.get("label", ""),
                description="",
                input={}
            )
        
        # Parse measured
        measured_dict = node_dict.get("measured")
        measured = None
        if measured_dict:
            try:
                measured = MeasuredDTO.model_validate(measured_dict)
            except Exception:
                pass
        
        node_v2 = XyflowNodeDTOV2(
            id=str(node_dict.get("id", "")),
            type=node_dict.get("type", "default"),
            position=PositionDTOV2(
                x=node_dict.get("position", {}).get("x", 0),
                y=node_dict.get("position", {}).get("y", 0)
            ),
            data=XyflowNodeDataDTOV2(
                label=data.get("label", ""),
                nodeType=data.get("nodeType", ""),
                nodeDefinition=node_def,
                config=data.get("config", {}),
                isReadOnly=data.get("isReadOnly", False)
            ),
            measured=measured,
            selected=node_dict.get("selected", False),
            dragging=node_dict.get("dragging", False),
            properties=node_dict.get("properties", {})
        )
        v2_nodes.append(node_v2)
    
    # Convert edges
    v2_edges = []
    for edge_dict in edges:
        style_dict = edge_dict.get("style")
        style = None
        if style_dict:
            try:
                style = EdgeStyleDTO.model_validate(style_dict)
            except Exception:
                pass
        
        edge_v2 = XyflowEdgeDTOV2(
            id=str(edge_dict.get("id", "")),
            source=str(edge_dict.get("source", "")),
            target=str(edge_dict.get("target", "")),
            sourceHandle=edge_dict.get("sourceHandle"),
            targetHandle=edge_dict.get("targetHandle"),
            type=edge_dict.get("type", "default"),
            animated=edge_dict.get("animated", False),
            style=style
        )
        v2_edges.append(edge_v2)
    
    return XyflowWorkflowDTOV2(
        id=xyflow_workflow.get("id"),
        name=xyflow_workflow.get("name", "Unsaved Workflow"),
        nodes=v2_nodes,
        edges=v2_edges,
        viewport=ViewportDTOV2.model_validate(xyflow_workflow.get("viewport", {})),
        timestamp=xyflow_workflow.get("timestamp", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    )


def _lite_to_xyflow_v2(
    lite_workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> XyflowWorkflowDTOV2:
    """Convert lite format to xyFlow V2."""
    from .builder import XyflowWorkflowBuilderV2
    
    builder = XyflowWorkflowBuilderV2(
        name=lite_workflow.get("name"),
        auto_layout=True
    )
    
    nodes = lite_workflow.get("nodes", {})
    
    # Track node indices
    node_indices = {}
    for node_name, node_data in nodes.items():
        node_indices[node_name] = node_data.get("index", len(node_indices) + 1)
    
    # Add nodes
    for node_name, node_data in nodes.items():
        node_type = node_data.get("type", "")
        config = {}
        
        # Separate config from connections
        inputs = node_data.get("inputs", {})
        for inp_name, inp_value in inputs.items():
            if not isinstance(inp_value, dict):
                config[inp_name] = inp_value
        
        # Get node definition
        node_def = None
        if node_info and node_type in node_info:
            node_def_dict = node_info[node_type]
            try:
                node_def = NodeDefinitionDTO.model_validate(node_def_dict)
            except Exception:
                node_def = NodeDefinitionDTO(
                    name=node_type,
                    display_name=node_type,
                    description="",
                    input={}
                )
        else:
            node_def = NodeDefinitionDTO(
                name=node_type,
                display_name=node_name,
                description="",
                input={}
            )
        
        builder.add_node(
            name=node_name,
            node_definition=node_def,
            config=config,
            label=node_data.get("label", node_name)
        )
    
    # Add edges
    for node_name, node_data in nodes.items():
        inputs = node_data.get("inputs", {})
        for inp_name, inp_value in inputs.items():
            if isinstance(inp_value, dict) and "node_id" in inp_value:
                source_id = inp_value["node_id"]
                output_name = inp_value.get("output_name")
                
                # Find source node name from index
                source_name = None
                for n_name, n_idx in node_indices.items():
                    if n_idx == source_id:
                        source_name = n_name
                        break
                
                if source_name and output_name:
                    builder.connect(source_name, output_name, node_name, inp_name)
    
    return builder.build(validate=False)


def _standard_to_xyflow_v2(
    standard_workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> XyflowWorkflowDTOV2:
    """Convert standard (ComfyUI) format to xyFlow V2."""
    nodes = standard_workflow.get("nodes", [])
    links = standard_workflow.get("links", [])
    
    # Build node map
    node_map = {node.get("id"): node for node in nodes}
    
    # Build link map for each node (to track which inputs/outputs are connected)
    incoming_links = {}  # target_id -> {slot: link_info}
    outgoing_links = {}  # source_id -> {slot: link_info}
    for link in links:
        if len(link) >= 6:
            link_id, source_id, source_slot, target_id, target_slot, link_type = link[:6]
            if target_id not in incoming_links:
                incoming_links[target_id] = {}
            incoming_links[target_id][target_slot] = link
            if source_id not in outgoing_links:
                outgoing_links[source_id] = {}
            outgoing_links[source_id][source_slot] = link
    
    # Convert nodes
    v2_nodes = []
    id_mapping = {}
    
    for idx, node in enumerate(nodes, 1):
        old_id = node.get("id")
        timestamp = int(time.time() * 1000)
        new_id = f"{node.get('type', 'Node')}-{timestamp + idx}"
        id_mapping[old_id] = new_id
        
        pos = node.get("pos", [0, 0])
        node_type = node.get("type", "")
        
        # Build config from widgets_values
        config = {}
        widgets_values = node.get("widgets_values", [])
        
        # Get inputs and outputs from original node
        node_inputs = node.get("inputs", [])
        node_outputs = node.get("outputs", [])
        
        # Build input definition from node's inputs
        input_required = {}
        input_optional = {}
        for inp in node_inputs:
            inp_name = inp.get("name", "")
            inp_type = inp.get("type", "ANY")
            # InputDefinitionDTO expects List[Any] format: [type, config_dict]
            if inp.get("shape") == 7:  # Optional input
                input_optional[inp_name] = [inp_type, {}]
            else:
                input_required[inp_name] = [inp_type, {}]
        
        # Build output info from node's outputs
        output_types = []
        output_names = []
        output_is_list = []
        for out in node_outputs:
            output_types.append(out.get("type", "ANY"))
            output_names.append(out.get("name", "output"))
            output_is_list.append(False)
        
        # Map widgets_values to config
        # widgets_values order corresponds to inputs order + additional widget params
        if widgets_values:
            if node_info and node_type in node_info:
                input_def = node_info[node_type].get("input", {})
                required = input_def.get("required", {})
                param_names = list(required.keys())
                for i, val in enumerate(widgets_values):
                    if i < len(param_names):
                        config[param_names[i]] = val
            else:
                # Try to map widgets_values to input names
                # First values correspond to inputs that don't have connections
                input_idx = 0
                for i, val in enumerate(widgets_values):
                    # Find next unconnected input
                    while input_idx < len(node_inputs):
                        inp = node_inputs[input_idx]
                        inp_name = inp.get("name", "")
                        # Check if this input has a connection
                        if inp.get("link") is None:
                            config[inp_name] = val
                            input_idx += 1
                            break
                        input_idx += 1
                    else:
                        # No more inputs, use param_N
                        config[f"param_{i}"] = val
        
        # Create node definition
        node_def = None
        if node_info and node_type in node_info:
            try:
                node_def = NodeDefinitionDTO.model_validate(node_info[node_type])
            except Exception:
                pass
        
        if not node_def:
            node_def = NodeDefinitionDTO(
                name=node_type,
                display_name=node.get("title") or node_type,
                description="",
                input={
                    "required": input_required,
                    "optional": input_optional
                },
                output=output_types,
                output_name=output_names,
                output_is_list=output_is_list
            )
        
        node_v2 = XyflowNodeDTOV2(
            id=new_id,
            type="default",
            position=PositionDTOV2(x=pos[0] if pos else 0, y=pos[1] if pos and len(pos) > 1 else 0),
            data=XyflowNodeDataDTOV2(
                label=node.get("title") or node_type,
                nodeType=node_type,
                config=config,
                nodeDefinition=node_def,
                isReadOnly=True
            )
        )
        v2_nodes.append(node_v2)
    
    # Convert edges
    v2_edges = []
    edge_idx = 1
    
    for link in links:
        if len(link) >= 6:
            link_id, source_id, source_slot, target_id, target_slot, link_type = link[:6]
            
            new_source = id_mapping.get(source_id)
            new_target = id_mapping.get(target_id)
            
            if new_source and new_target:
                source_handle = str(source_slot)
                target_handle = str(target_slot)
                
                # Get source handle from source node's outputs
                source_node = node_map.get(source_id)
                if source_node:
                    outputs = source_node.get("outputs", [])
                    if source_slot < len(outputs):
                        output = outputs[source_slot]
                        # Prefer output name, then widget.name for PrimitiveNode
                        if output.get("name"):
                            source_handle = output.get("name")
                        # Check for widget.name which indicates the actual parameter name
                        widget = output.get("widget", {})
                        if widget and widget.get("name"):
                            source_handle = widget.get("name")
                
                # Get target handle from target node's inputs
                target_node = node_map.get(target_id)
                if target_node:
                    inputs = target_node.get("inputs", [])
                    if target_slot < len(inputs):
                        inp = inputs[target_slot]
                        if inp.get("name"):
                            target_handle = inp.get("name")
                
                edge_v2 = XyflowEdgeDTOV2(
                    id=f"edge-{edge_idx}",
                    source=new_source,
                    target=new_target,
                    sourceHandle=source_handle,
                    targetHandle=target_handle,
                    type="default",
                    animated=True
                )
                v2_edges.append(edge_v2)
                edge_idx += 1
    
    return XyflowWorkflowDTOV2(
        id=standard_workflow.get("id"),
        name=standard_workflow.get("name", "Unsaved Workflow"),
        nodes=v2_nodes,
        edges=v2_edges,
        viewport=ViewportDTOV2()
    )


# ==================== Legacy xyFlow Conversions (Deprecated) ====================

def to_xyflow(
    workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> XyflowWorkflowDTO:
    """
    Convert any workflow format to xyFlow (Legacy - Deprecated).
    
    .. deprecated:: 0.2.0
        Use to_xyflow_v2 instead for full nodeDefinition support.
    
    Args:
        workflow: Source workflow dictionary
        node_info: Optional node definitions for enrichment
        
    Returns:
        XyflowWorkflowDTO instance
        
    Raises:
        ValueError: If format is unknown or conversion fails
    """
    warnings.warn(
        "to_xyflow is deprecated. Use to_xyflow_v2 instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    fmt = detect_format(workflow)
    
    if fmt in (WorkflowFormat.XYFLOW, WorkflowFormat.XYFLOW_V2):
        return XyflowWorkflowDTO.from_dict(workflow)
    elif fmt == WorkflowFormat.LITE:
        return _lite_to_xyflow(workflow, node_info)
    elif fmt == WorkflowFormat.STANDARD:
        return _standard_to_xyflow(workflow, node_info)
    else:
        raise ValueError(f"Cannot convert unknown format to xyFlow")


def _lite_to_xyflow(
    lite_workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> XyflowWorkflowDTO:
    """Convert lite format to xyFlow (legacy)."""
    from .builder import XyflowWorkflowBuilder
    
    builder = XyflowWorkflowBuilder(
        name=lite_workflow.get("name"),
        auto_layout=True
    )
    
    nodes = lite_workflow.get("nodes", {})
    
    node_indices = {}
    for node_name, node_data in nodes.items():
        node_indices[node_name] = node_data.get("index", len(node_indices) + 1)
    
    for node_name, node_data in nodes.items():
        node_type = node_data.get("type", "")
        config = {}
        
        inputs = node_data.get("inputs", {})
        for inp_name, inp_value in inputs.items():
            if not isinstance(inp_value, dict):
                config[inp_name] = inp_value
        
        node_def = node_info.get(node_type) if node_info else None
        
        builder.add_node(
            name=node_name,
            node_type=node_type,
            config=config,
            label=node_data.get("label", node_name),
            node_definition=node_def
        )
    
    for node_name, node_data in nodes.items():
        inputs = node_data.get("inputs", {})
        for inp_name, inp_value in inputs.items():
            if isinstance(inp_value, dict) and "node_id" in inp_value:
                source_id = inp_value["node_id"]
                output_name = inp_value.get("output_name")
                
                source_name = None
                for n_name, n_idx in node_indices.items():
                    if n_idx == source_id:
                        source_name = n_name
                        break
                
                if source_name and output_name:
                    builder.connect(source_name, output_name, node_name, inp_name)
    
    return builder.build(validate=False)


def _standard_to_xyflow(
    standard_workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> XyflowWorkflowDTO:
    """Convert standard (ComfyUI) format to xyFlow (legacy)."""
    nodes = standard_workflow.get("nodes", [])
    links = standard_workflow.get("links", [])
    
    node_map = {node.get("id"): node for node in nodes}
    
    xyflow_nodes = []
    id_mapping = {}
    
    for idx, node in enumerate(nodes, 1):
        old_id = node.get("id")
        new_id = str(idx)
        id_mapping[old_id] = new_id
        
        pos = node.get("pos", [0, 0])
        node_type = node.get("type", "")
        
        config = {}
        widgets_values = node.get("widgets_values", [])
        if widgets_values:
            if node_info and node_type in node_info:
                input_def = node_info[node_type].get("input", {})
                required = input_def.get("required", {})
                param_names = list(required.keys())
                for i, val in enumerate(widgets_values):
                    if i < len(param_names):
                        config[param_names[i]] = val
            else:
                for i, val in enumerate(widgets_values):
                    config[f"param_{i}"] = val
        
        node_dto = XyflowNodeDTO(
            id=new_id,
            type="default",
            position=PositionDTO(x=pos[0] if pos else 0, y=pos[1] if pos and len(pos) > 1 else 0),
            data=XyflowNodeDataDTO(
                label=node.get("title") or node_type,
                nodeType=node_type,
                config=config,
                nodeDefinition=node_info.get(node_type) if node_info else None
            )
        )
        xyflow_nodes.append(node_dto)
    
    xyflow_edges = []
    edge_idx = 1
    
    for link in links:
        if len(link) >= 6:
            link_id, source_id, source_slot, target_id, target_slot, link_type = link[:6]
            
            new_source = id_mapping.get(source_id)
            new_target = id_mapping.get(target_id)
            
            if new_source and new_target:
                source_handle = str(source_slot)
                target_handle = str(target_slot)
                
                if node_info:
                    source_node = node_map.get(source_id)
                    if source_node:
                        source_type = source_node.get("type", "")
                        if source_type in node_info:
                            output_names = node_info[source_type].get("output_name", [])
                            if source_slot < len(output_names):
                                source_handle = output_names[source_slot]
                
                edge_dto = XyflowEdgeDTO(
                    id=f"edge-{edge_idx}",
                    source=new_source,
                    target=new_target,
                    sourceHandle=source_handle,
                    targetHandle=target_handle,
                    type="default"
                )
                xyflow_edges.append(edge_dto)
                edge_idx += 1
    
    return XyflowWorkflowDTO(
        id=standard_workflow.get("id"),
        name=standard_workflow.get("name"),
        nodes=xyflow_nodes,
        edges=xyflow_edges,
        viewport=ViewportDTO()
    )


# ==================== Lite Conversions ====================

def to_lite(
    workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convert any workflow format to lite.
    
    Args:
        workflow: Source workflow dictionary
        node_info: Optional node definitions
        
    Returns:
        Lite format dictionary
    """
    fmt = detect_format(workflow)
    
    if fmt == WorkflowFormat.LITE:
        return workflow
    elif fmt in (WorkflowFormat.XYFLOW, WorkflowFormat.XYFLOW_V2):
        return _xyflow_to_lite(workflow, node_info)
    elif fmt == WorkflowFormat.STANDARD:
        xyflow = _standard_to_xyflow(workflow, node_info)
        return _xyflow_to_lite(xyflow.model_dump(), node_info)
    else:
        raise ValueError(f"Cannot convert unknown format to lite")


def _xyflow_to_lite(
    xyflow_workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Convert xyFlow format to lite."""
    nodes = xyflow_workflow.get("nodes", [])
    edges = xyflow_workflow.get("edges", [])
    
    # Build edge map
    edge_map = {}
    for edge in edges:
        target = str(edge.get("target", ""))
        target_handle = edge.get("targetHandle", "")
        source = str(edge.get("source", ""))
        source_handle = edge.get("sourceHandle", "")
        
        if target not in edge_map:
            edge_map[target] = {}
        edge_map[target][target_handle] = (source, source_handle)
    
    # Build output name mapping
    output_names = {}
    for node in nodes:
        node_id = str(node.get("id", ""))
        data = node.get("data", {})
        node_def = data.get("nodeDefinition", {})
        names = node_def.get("output_name", []) if isinstance(node_def, dict) else []
        output_names[node_id] = names
    
    # Convert nodes
    lite_nodes = {}
    
    for node in nodes:
        node_id = str(node.get("id", ""))
        data = node.get("data", {})
        node_type = data.get("nodeType", "")
        config = data.get("config", {})
        label = data.get("label", node_id)
        
        inputs = dict(config)
        
        for target_handle, (source_id, source_handle) in edge_map.get(node_id, {}).items():
            inputs[target_handle] = {
                "node_id": int(source_id) if source_id.isdigit() else source_id,
                "output_name": source_handle
            }
        
        node_def = data.get("nodeDefinition", {})
        outputs = node_def.get("output_name", []) if isinstance(node_def, dict) else []
        
        lite_nodes[label] = {
            "type": node_type,
            "index": int(node_id) if node_id.isdigit() else node_id,
            "inputs": inputs,
            "outputs": outputs
        }
    
    return {
        "version": "1.0",
        "name": xyflow_workflow.get("name"),
        "nodes": lite_nodes
    }


# ==================== Standard Conversions ====================

def to_standard(
    workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convert any workflow format to standard (ComfyUI).
    
    Args:
        workflow: Source workflow dictionary
        node_info: Optional node definitions
        
    Returns:
        Standard format dictionary
    """
    fmt = detect_format(workflow)
    
    if fmt == WorkflowFormat.STANDARD:
        return workflow
    elif fmt in (WorkflowFormat.XYFLOW, WorkflowFormat.XYFLOW_V2):
        return _xyflow_to_standard(workflow, node_info)
    elif fmt == WorkflowFormat.LITE:
        xyflow = _lite_to_xyflow(workflow, node_info)
        return _xyflow_to_standard(xyflow.model_dump(), node_info)
    else:
        raise ValueError(f"Cannot convert unknown format to standard")


def _xyflow_to_standard(
    xyflow_workflow: Dict[str, Any],
    node_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Convert xyFlow format to standard (ComfyUI)."""
    nodes = xyflow_workflow.get("nodes", [])
    edges = xyflow_workflow.get("edges", [])
    
    links = []
    link_idx = 1
    
    standard_nodes = []
    
    for node in nodes:
        try:
            node_id = int(node.get("id", "1"))
        except ValueError:
            node_id = hash(node.get("id", "")) % 10000
        
        data = node.get("data", {})
        node_type = data.get("nodeType", "")
        config = data.get("config", {})
        pos = node.get("position", {})
        
        inputs = []
        outputs = []
        
        if node_info and node_type in node_info:
            node_def = node_info[node_type]
            input_def = node_def.get("input", {})
            required = input_def.get("required", {})
            optional = input_def.get("optional", {})
            
            for inp_name in list(required.keys()) + list(optional.keys()):
                inputs.append({"name": inp_name, "type": "ANY", "link": None})
            
            output_types = node_def.get("output", [])
            output_names = node_def.get("output_name", [])
            for i, out_type in enumerate(output_types):
                outputs.append({
                    "name": output_names[i] if i < len(output_names) else f"output_{i}",
                    "type": out_type,
                    "links": []
                })
        
        widgets_values = []
        if node_info and node_type in node_info:
            input_def = node_info[node_type].get("input", {})
            required = input_def.get("required", {})
            for param_name in required.keys():
                if param_name in config:
                    widgets_values.append(config[param_name])
        
        standard_node = {
            "id": node_id,
            "type": node_type,
            "pos": [pos.get("x", 0), pos.get("y", 0)],
            "size": {"width": 270, "height": 82},
            "flags": {},
            "order": node_id,
            "mode": 0,
            "inputs": inputs,
            "outputs": outputs,
            "properties": {},
            "widgets_values": widgets_values
        }
        standard_nodes.append(standard_node)
    
    for edge in edges:
        try:
            source_id = int(edge.get("source", "1"))
            target_id = int(edge.get("target", "1"))
        except ValueError:
            continue
        
        source_handle = edge.get("sourceHandle", "0")
        target_handle = edge.get("targetHandle", "0")
        
        try:
            source_slot = int(source_handle)
        except ValueError:
            source_slot = 0
        
        try:
            target_slot = int(target_handle)
        except ValueError:
            target_slot = 0
        
        link_type = "ANY"
        if node_info:
            source_node = next((n for n in nodes if str(n.get("id")) == str(source_id)), None)
            if source_node:
                source_type = source_node.get("data", {}).get("nodeType", "")
                if source_type in node_info:
                    output_types = node_info[source_type].get("output", [])
                    if source_slot < len(output_types):
                        link_type = output_types[source_slot]
        
        links.append([link_idx, source_id, source_slot, target_id, target_slot, link_type])
        link_idx += 1
    
    return {
        "id": xyflow_workflow.get("id", "workflow"),
        "name": xyflow_workflow.get("name", "Workflow"),
        "nodes": standard_nodes,
        "links": links,
        "extra": {
            "ds": {
                "scale": 1,
                "offset": [0, 0]
            }
        }
    }


# ==================== Convenience Functions ====================

def convert(
    workflow: Dict[str, Any],
    target_format: Literal["xyflow", "lite", "standard"],
    node_info: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Convert workflow to target format (Legacy).
    
    .. deprecated:: 0.2.0
        Use convert_v2 instead for V2 support.
    
    Args:
        workflow: Source workflow
        target_format: Target format name
        node_info: Optional node definitions
        
    Returns:
        Converted workflow
    """
    if target_format == "xyflow":
        return to_xyflow(workflow, node_info)
    elif target_format == "lite":
        return to_lite(workflow, node_info)
    elif target_format == "standard":
        return to_standard(workflow, node_info)
    else:
        raise ValueError(f"Unknown target format: {target_format}")


def convert_v2(
    workflow: Dict[str, Any],
    target_format: Literal["xyflow_v2", "xyflow", "lite", "standard"],
    node_info: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Convert workflow to target format (V2 - Recommended).
    
    Args:
        workflow: Source workflow
        target_format: Target format name
        node_info: Optional node definitions
        
    Returns:
        Converted workflow
    """
    if target_format == "xyflow_v2":
        return to_xyflow_v2(workflow, node_info)
    elif target_format == "xyflow":
        return to_xyflow(workflow, node_info)
    elif target_format == "lite":
        return to_lite(workflow, node_info)
    elif target_format == "standard":
        return to_standard(workflow, node_info)
    else:
        raise ValueError(f"Unknown target format: {target_format}")