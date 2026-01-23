# Test Data for Workflow Validation

This directory contains test workflow files used for validation testing.

## Files

### `invalid_lite_missing_required.json`
A lite format workflow that is intentionally invalid - it's missing required parameters for `GUISFTTrainingNode`.

**Purpose**: Test that the validator correctly detects missing required parameters when `node_info` is provided.

**Expected behavior**: 
- Without `node_info`: Basic schema validation passes (workflow structure is valid)
- With `node_info`: Validation fails with error about missing required parameter `dataset`

**Usage**: Used in `test_validate_test_data_workflows()` test case.
