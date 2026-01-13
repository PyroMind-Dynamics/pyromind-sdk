"""
Pytest configuration to prevent test_yaml_nodes.py functions from being collected as tests.

The test_yaml_nodes.py file contains utility functions (test_yaml_file, test_directory)
that are used by pytest tests but are not pytest test functions themselves.
"""

def pytest_collection_modifyitems(config, items):
    """Remove test_yaml_file and test_directory from collected items"""
    items[:] = [item for item in items if item.name not in ("test_yaml_file", "test_directory")]
