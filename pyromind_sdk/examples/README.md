# PyroMind SDK Examples

本目录包含了 PyroMind SDK 的使用示例，按功能分为两个子目录：

## 目录结构

### `nodes/` - YAML Node 配置示例

包含各种 YAML node 配置文件的示例，用于演示如何定义和执行不同类型的节点。

**文件列表：**
- `hello_world_node.yaml` - 基础 Hello World 节点
- `echo_node.yaml` - Echo 命令节点
- `python_calculator_node.yaml` - Python 计算器节点
- `multi_input_node.yaml` - 多输入节点示例
- `customer_inputs_node.yaml` - 自定义输入节点
- `multiline_text_node.yaml` - 多行文本处理节点
- `simple_gpu_node.yaml` - 简单 GPU 节点
- `jupyter_gpu_node.yaml` - Jupyter GPU 节点

**工具文件：**
- `utils/` - 节点执行相关的工具函数
  - `calculator.py` - 计算器工具
  - `jupyter_gpu_executor.py` - Jupyter GPU 执行器
  - `multiline_processor.py` - 多行文本处理器

### `openapi/` - OpenAPI Client 使用示例

包含使用 PyroMind API Client SDK 的完整示例，展示如何通过 Python SDK 与 PyroMind API 交互。

**文件列表：**
- `api_client_basic.py` - 基础客户端使用示例
- `sandbox_example.py` - Sandbox 管理示例
- `jupyter_instance_example.py` - Jupyter 实例管理示例
- `inference_example.py` - 推理任务管理示例
- `training_example.py` - 训练任务管理示例
- `complete_workflow_example.py` - 完整工作流示例
- `API_CLIENT_EXAMPLES.md` - API Client 示例文档

## 使用说明

### 运行 YAML Node 示例

YAML node 示例主要用于测试和验证节点配置。可以通过测试框架运行：

```bash
# 运行所有 YAML node 测试
pytest pyromind_sdk/tests/pytest/test_yaml_nodes_pytest.py
```

### 运行 OpenAPI Client 示例

所有 OpenAPI Client 示例都需要设置 `PYROMIND_API_KEY` 环境变量：

```bash
# 设置 API Key
export PYROMIND_API_KEY="your-api-key-here"

# 运行基础示例
python pyromind_sdk/examples/openapi/api_client_basic.py

# 运行其他示例
python pyromind_sdk/examples/openapi/sandbox_example.py
python pyromind_sdk/examples/openapi/jupyter_instance_example.py
python pyromind_sdk/examples/openapi/inference_example.py
python pyromind_sdk/examples/openapi/training_example.py
python pyromind_sdk/examples/openapi/complete_workflow_example.py
```

更多详细信息请参考 `openapi/API_CLIENT_EXAMPLES.md`。
