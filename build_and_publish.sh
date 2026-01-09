#!/bin/bash
# Build and publish yaml-nodes package to PyPI

set -e

echo "Building yaml-nodes package..."

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build package
python -m build

echo ""
echo "Build complete! Distribution files:"
ls -lh dist/

echo ""
echo "To publish to PyPI, run:"
echo "  twine upload dist/*"
echo ""
echo "To test on TestPyPI first, run:"
echo "  twine upload --repository testpypi dist/*"

