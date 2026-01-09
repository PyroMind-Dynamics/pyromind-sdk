"""
Example calculator function

This function will be called by Python nodes.
Supports multiple inputs and outputs.
"""


def calculate(input0: float, input1: float) -> dict:
    """
    Perform arithmetic operations (multiple inputs and outputs example)
    
    Args:
        input0: First input
        input1: Second input
        
    Returns:
        Dictionary containing input0, input1, and output0
    """
    # Calculate output (e.g., sum of two inputs)
    output0 = input0 + input1
    
    # Return multiple outputs (convert to string, as YAML defines STRING type)
    return {
        "result_input0": input0,
        "result_input1": input1,
        "result_output0": output0,
    }

