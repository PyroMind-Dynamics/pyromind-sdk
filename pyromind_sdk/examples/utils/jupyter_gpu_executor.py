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
    python_code = """
import torch
if torch.cuda.is_available():
    print(f'CUDA available: {torch.cuda.is_available()}')
    print(f'GPU count: {torch.cuda.device_count()}')
    print(f'GPU name: {torch.cuda.get_device_name(0)}')
else:
    print('CUDA not available')
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
    try:
        # Create execution environment
        exec_globals = {
            '__builtins__': __builtins__,
        }
        exec_locals = {}
        
        # Execute code and capture output
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(python_code, exec_globals, exec_locals)
            
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            if stdout_output:
                execution_output = stdout_output
            if stderr_output:
                if execution_output:
                    execution_output += "\n" + stderr_output
                else:
                    execution_output = stderr_output
                    
        except Exception as e:
            execution_result = f"Execution error: {str(e)}"
            execution_output = str(e)
            
    except Exception as e:
        execution_result = f"Code execution failed: {str(e)}"
        execution_output = str(e)
    
    # Build return result (key names must match output names defined in YAML)
    result = {
        "gpu_info": gpu_info,
        "execution_result": execution_result,
        "execution_output": execution_output,
        "message_output": message,  # Use message_output to match YAML output name
    }
    
    return result

