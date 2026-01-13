"""
Jupyter GPU executor

Executes Python code in Jupyter environment and checks GPU availability.
"""

import subprocess
import json
from typing import Dict, Any


def execute_jupyter_gpu_code(message: str) -> Dict[str, Any]:
    """
    Execute Python code in Jupyter environment and check GPU availability
    
    Args:
        message: Custom message
        
    Returns:
        Dictionary containing execution results:
        - gpu_info: GPU information
        - execution_result: Code execution result
        - message: Custom message
    """
    # Check GPU availability
    gpu_info = "No GPU detected"
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            gpu_info = result.stdout.strip()
        else:
            gpu_info = "GPU check failed (nvidia-smi returned non-zero)"
    except subprocess.TimeoutExpired:
        gpu_info = "GPU check timeout"
    except FileNotFoundError:
        gpu_info = "nvidia-smi not found"
    except Exception as e:
        gpu_info = f"GPU check error: {str(e)}"
    
    # Execute Python code
    execution_result = "Code executed successfully"
    execution_output = ""

    import torch
    if torch.cuda.is_available():
        print(f'CUDA available: {torch.cuda.is_available()}')
        print(f'GPU count: {torch.cuda.device_count()}')
        print(f'GPU name: {torch.cuda.get_device_name(0)}')
    
    message += f'CUDA available: {torch.cuda.is_available()}'
    message += f'GPU count: {torch.cuda.device_count()}'
    message += f'GPU name: {torch.cuda.get_device_name(0)}'
    # Build return result (key names must match output names defined in YAML)
    result = {
        "gpu_info": gpu_info,
        "execution_result": execution_result,
        "execution_output": execution_output,
        "message_output": message,  # Use message_output to match YAML output name
    }
    
    return result

