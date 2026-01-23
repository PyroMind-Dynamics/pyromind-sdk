#!/usr/bin/env python3
"""
Workflow Format Converter CLI

Command-line interface for converting between workflow formats.
Uses the pyromind_sdk.workflow module for conversion.

Usage:
    python workflow_cli.py convert workflow.json output.lite.json
    python workflow_cli.py convert --to-standard workflow.lite.json output.json
    python workflow_cli.py validate workflow.lite.json
    python workflow_cli.py convert --with-node-info workflow.json output.lite.json
"""

import json
import sys
from pathlib import Path
from argparse import ArgumentParser

# Add parent directory to path for imports when running as script
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import from SDK
from pyromind_sdk import PyroMindAPIClient, WorkflowLiteConverter


def main():
    """Main entry point for CLI."""
    parser = ArgumentParser(
        description="Convert between workflow and workflow_lite formats",
        epilog="""
Examples:
  # Convert to lite format
  python workflow_cli.py convert workflow.json output.lite.json

  # Convert back to standard format
  python workflow_cli.py convert --to-standard workflow.lite.json output.json

  # Validate a lite workflow
  python workflow_cli.py validate workflow.lite.json
        """
    )

    parser.add_argument(
        "command",
        choices=["convert", "validate"],
        help="Command to execute"
    )
    parser.add_argument(
        "input",
        help="Input JSON file"
    )
    parser.add_argument(
        "output",
        nargs="?",
        help="Output JSON file (for convert command)"
    )
    parser.add_argument(
        "--to-standard",
        action="store_true",
        help="Convert from lite to standard format (default: standard to lite)"
    )
    parser.add_argument(
        "--with-node-info",
        action="store_true",
        help="Fetch node info from API for accurate parameter mapping (requires API key)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Read input file
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Fetch node_info if requested
    # node_info is needed for both directions:
    # - standard -> lite: for accurate parameter name mapping
    # - lite -> standard: for restoring correct input/output types
    node_info = None
    if args.with_node_info:
        try:
            print("Fetching node info from API...")
            client = PyroMindAPIClient()
            node_info = client.training.get_node_info()
            print(f"✓ Loaded {len(node_info)} node definitions")
            client.close()
        except Exception as e:
            print(f"Warning: Failed to fetch node info: {e}")
            if args.to_standard:
                print("Continuing without node info - types will default to 'AUTO'")
            else:
                print("Continuing with generic parameter extraction...")

    converter = WorkflowLiteConverter(node_info=node_info)

    if args.command == "validate":
        # Validate lite format
        required_fields = ["name", "nodes", "connections"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            print(f"✗ Validation failed: Missing fields: {', '.join(missing)}")
            sys.exit(1)

        # Check connections reference valid nodes
        node_names = set(data.get("nodes", {}).keys())
        for conn in data.get("connections", []):
            if conn.get("from") not in node_names:
                print(f"✗ Validation failed: Unknown source node '{conn.get('from')}'")
                sys.exit(1)
            if conn.get("to") not in node_names:
                print(f"✗ Validation failed: Unknown target node '{conn.get('to')}'")
                sys.exit(1)

        print("✓ Validation passed")
        sys.exit(0)

    elif args.command == "convert":
        if not args.output:
            print("Error: Output file required for convert command")
            sys.exit(1)

        output_path = Path(args.output)

        # Convert
        if args.to_standard:
            result = converter.to_standard(data)
        else:
            result = converter.to_lite(data)

        # Write output
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"✓ Converted {input_path} -> {output_path}")
        sys.exit(0)


if __name__ == "__main__":
    main()
