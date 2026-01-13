# PyroMind API Client SDK 使用示例

本目录包含了 PyroMind API Client SDK 的完整使用示例。

## 示例文件列表

### 1. `api_client_basic.py` - 基础使用示例
展示如何初始化客户端并列出所有资源（Sandboxes、Jupyter Instances、Inference Jobs、Training Jobs）。

**运行方式：**
```bash
python pyromind_sdk/examples/api_client_basic.py
```

### 2. `sandbox_example.py` - Sandbox 管理示例
展示如何创建、列出、获取、执行操作、获取 VNC 信息和删除 Sandbox。

**运行方式：**
```bash
python pyromind_sdk/examples/sandbox_example.py
```

**主要功能：**
- 创建 Sandbox
- 列出所有 Sandbox
- 获取 Sandbox 详情
- 在 Sandbox 中执行命令
- 获取 VNC 连接信息
- 删除 Sandbox

### 3. `jupyter_instance_example.py` - Jupyter 实例管理示例
展示如何创建、管理、暂停/恢复和删除 Jupyter 实例。

**运行方式：**
```bash
python pyromind_sdk/examples/jupyter_instance_example.py
```

**主要功能：**
- 创建 Jupyter 实例
- 列出所有 Jupyter 实例
- 获取实例详情
- 更新实例配置
- 暂停/恢复实例
- 删除实例

### 4. `inference_example.py` - 推理任务管理示例
展示如何创建、管理和删除推理任务。

**运行方式：**
```bash
python pyromind_sdk/examples/inference_example.py
```

**主要功能：**
- 创建推理任务
- 列出所有推理任务
- 获取任务详情
- 删除任务

### 5. `training_example.py` - 训练任务管理示例
展示如何创建、管理、暂停/恢复和删除训练任务。

**运行方式：**
```bash
python pyromind_sdk/examples/training_example.py
```

**主要功能：**
- 创建训练任务
- 列出所有训练任务
- 获取任务详情
- 暂停/恢复任务
- 删除任务

### 6. `complete_workflow_example.py` - 完整工作流示例
展示一个完整的机器学习工作流，包括：
1. 创建 Sandbox 进行数据准备
2. 创建 Jupyter 实例进行实验
3. 创建训练任务
4. 创建推理任务
5. 监控所有资源

**运行方式：**
```bash
python pyromind_sdk/examples/complete_workflow_example.py
```

## API Key 配置

所有示例都从环境变量 `PYROMIND_API_KEY` 读取 API Key。

**设置环境变量：**

在运行示例之前，请设置环境变量：

```bash
export PYROMIND_API_KEY="your-api-key-here"
```

或者在运行命令时直接设置：

```bash
PYROMIND_API_KEY="your-api-key-here" python pyromind_sdk/examples/api_client_basic.py
```

**注意：** 如果环境变量未设置，客户端会抛出 `ValueError` 错误，提示需要提供 API Key。

## 使用前准备

1. **安装依赖：**
```bash
pip install pyromind-sdk
```

2. **确保 API Key 有效：**
示例中使用的 API Key 应该具有访问所有资源的权限。

## 注意事项

1. **资源清理：** 示例中创建的资源可能需要手动清理，避免产生不必要的费用。

2. **错误处理：** 所有示例都包含了错误处理，如果 API 调用失败会显示相应的错误信息。

3. **资源状态：** 某些操作（如创建资源）可能需要等待资源就绪，示例中包含了适当的等待时间。

4. **暂停/恢复操作：** 为了避免干扰正在运行的实例，某些示例中的暂停/恢复操作被注释掉了。如果需要测试这些功能，可以取消注释。

## 更多信息

- API 文档：https://pyromind.ai/api/v1/docs
- SDK 文档：查看 `pyromind_sdk/client/README.md`
