# 自动布局功能总结

## 🎯 功能概述

为 `WorkflowLiteConverter` 添加了自动节点布局功能，在将 lite 格式转换为标准格式时，自动计算节点的位置（pos）和布局。

## ✨ 主要特性

### 1. **拓扑排序布局**
- 使用拓扑排序算法分析节点依赖关系
- 从左到右按照数据流方向排列节点
- 输入节点（无依赖）在最左边
- 输出节点（无下游）在最右边

### 2. **层级分组**
- 相同依赖层级的节点排列在同一列
- 使用 BFS（广度优先搜索）算法计算层级
- 正确处理并行分支

### 3. **垂直排列**
- 同一层的多个节点从上到下垂直排列
- 避免节点重叠，保持清晰可读

### 4. **16:9 宽屏适配**
- 节点间距设计适配 16:9 的宽屏显示
- 水平间距：350px（列与列之间）
- 垂直间距：100px（行与行之间）
- 页边距：50px

### 5. **可配置**
- 默认启用自动布局（`auto_layout=True`）
- 可以通过 `auto_layout=False` 禁用
- 支持自定义布局参数

## 🏗️ 架构设计

### 新增类：LayoutGenerator

```python
class LayoutGenerator:
    """
    Automatic node layout generator for workflow visualization.

    Generates node positions using topological sorting with a 16:9 aspect ratio layout.
    Nodes are arranged left-to-right based on their dependency relationships.
    """
```

### 核心算法

1. **构建依赖图**
   ```python
   # 分析节点之间的连接关系
   in_edges: node -> set of nodes it depends on
   out_edges: node -> set of nodes that depend on it
   ```

2. **拓扑排序**
   ```python
   # 使用 BFS 按层级分组节点
   # 从入度为 0 的节点开始
   # 每一层包含所有依赖已满足的节点
   ```

3. **计算位置**
   ```python
   # 每层的 x 坐标
   x = margin + layer_idx * (node_width + horizontal_spacing)

   # 每行的 y 坐标
   y = margin + row_idx * (node_height + vertical_spacing)
   ```

## 📊 布局示例

### 示例1：线性workflow
```
A -> B -> C

布局结果：
  A: pos=[  50,   50]  (第0层)
  B: pos=[ 670,   50]  (第1层)
  C: pos=[1290,   50]  (第2层)
```

### 示例2：并行workflow
```
    A
   / \
  B   C
   \ /
    D

布局结果：
  A: pos=[  50,   50]  (第0层)
  B: pos=[ 670,   50]  (第1层)
  C: pos=[ 670,  232]  (第1层，垂直排列)
  D: pos=[1290,   50]  (第2层)
```

### 示例3：复杂workflow（5层）
```
A -> B -> C -> D -> E

布局结果：
  A: pos=[  50,   50]  (第0层)
  B: pos=[ 670,   50]  (第1层)
  C: pos=[1290,   50]  (第2层)
  D: pos=[1910,   50]  (第3层)
  E: pos=[2530,   50]  (第4层)
```

## 💻 使用方法

### 默认使用（启用自动布局）
```python
from pyromind_sdk import WorkflowLiteConverter

# 创建转换器（默认启用自动布局）
converter = WorkflowLiteConverter()

# 或显式启用
converter = WorkflowLiteConverter(auto_layout=True)

# 转换 lite -> standard
standard = converter.to_standard(lite_workflow)

# 节点位置已自动生成
for node in standard["nodes"]:
    print(f"{node['type']}: pos={node['pos']}")
```

### 禁用自动布局
```python
# 创建转换器（禁用自动布局）
converter = WorkflowLiteConverter(auto_layout=False)

standard = converter.to_standard(lite_workflow)

# 所有节点位置都是 [0, 0]
for node in standard["nodes"]:
    print(f"{node['type']}: pos={node['pos']}")  # [0, 0]
```

### 自定义布局参数
```python
from pyromind_sdk import LayoutGenerator, WorkflowLiteConverter

# 创建自定义布局生成器
layout_gen = LayoutGenerator(
    node_width=300,          # 节点宽度
    node_height=100,         # 节点高度
    horizontal_spacing=400,  # 水平间距
    vertical_spacing=150,    # 垂直间距
    margin=100               # 页边距
)

# 使用自定义布局
converter = WorkflowLiteConverter()
converter.layout_generator = layout_gen
```

## 📁 文件变更

### 修改的文件

1. **`pyromind_sdk/client/workflow/converter.py`**
   - 添加 `LayoutGenerator` 类（~160行代码）
   - 修改 `WorkflowLiteConverter.__init__()` 添加 `auto_layout` 参数
   - 修改 `WorkflowLiteConverter.to_standard()` 使用自动布局
   - 修改 `_convert_node_to_standard()` 接受 `pos` 参数

2. **`pyromind_sdk/client/workflow/__init__.py`**
   - 导出 `LayoutGenerator` 类

3. **`pyromind_sdk/__init__.py`**
   - 导出 `LayoutGenerator` 类到顶层

4. **`pyromind_sdk/tests/pytest/test_workflow_converter.py`**
   - 更新 `test_round_trip_conversion` 使用 `auto_layout=False`

## 🧪 测试结果

```bash
$ pytest pyromind_sdk/tests/pytest/test_workflow_converter.py -v
============================== 32 passed in 0.31s ==============================
```

所有32个测试全部通过！

## 🎨 布局参数说明

### 默认参数
```python
DEFAULT_NODE_WIDTH = 270      # 节点宽度（像素）
DEFAULT_NODE_HEIGHT = 82      # 节点高度（像素）
HORIZONTAL_SPACING = 350      # 水平间距（像素）
VERTICAL_SPACING = 100        # 垂直间距（像素）
MARGIN = 50                   # 页边距（像素）
```

### 布局计算
```python
# 第 i 列的 x 坐标
x = MARGIN + i * (NODE_WIDTH + HORIZONTAL_SPACING)
  = 50 + i * (270 + 350)
  = 50 + i * 620

# 第 j 行的 y 坐标
y = MARGIN + j * (NODE_HEIGHT + VERTICAL_SPACING)
  = 50 + j * (82 + 100)
  = 50 + j * 182
```

### 16:9 比例适配

布局参数设计考虑了 16:9 的宽屏显示器：
- 1920x1080 分辨率下可以显示约 3 列节点
- 2560x1440 分辨率下可以显示约 4 列节点
- 3840x2160 (4K) 分辨率下可以显示约 6 列节点

## 🚀 性能特点

- **时间复杂度**: O(V + E)，其中 V 是节点数，E 是连接数
- **空间复杂度**: O(V + E)
- **支持规模**: 可以处理数百个节点的workflow

## ✅ 优势

1. **自动化**: 无需手动设置节点位置
2. **可读性**: 清晰的层级结构，易于理解数据流
3. **一致性**: 所有workflow使用统一的布局规则
4. **可扩展**: 易于自定义布局参数
5. **向后兼容**: 可以禁用自动布局保持旧行为

## 🎯 使用场景

### 自动布局适用场景
- ✅ 从头创建新的 workflow
- ✅ 从 lite 格式转换为标准格式
- ✅ 需要快速可视化 workflow 结构
- ✅ 节点位置不重要或不关心

### 禁用自动布局适用场景
- ✅ 需要保留原有的节点位置
- ✅ 手动调整了节点布局
- ✅ 从标准格式转换为 lite 再转回标准格式
- ✅ 节点位置已经精心设计

## 📝 总结

自动布局功能为 workflow 转换器增添了强大的可视化能力，通过拓扑排序和层级分组算法，自动生成清晰、易读的节点布局。默认启用，可配置，向后兼容，大大提升了用户体验！

**关键指标**:
- ✅ 新增代码: ~200 行
- ✅ 新增类: 1 个 (LayoutGenerator)
- ✅ 测试通过: 32/32
- ✅ 性能: O(V + E)
- ✅ 功能完整性: 100%
