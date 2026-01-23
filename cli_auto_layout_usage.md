# Workflow CLI 自动布局使用指南

## 📋 概述

`workflow_cli.py` 现在支持自动节点布局功能。在将 lite 格式转换为标准格式时，可以自动计算节点的位置（pos），按照拓扑顺序从左到右排列。

## 🎯 基本使用

### 1. 默认启用自动布局

```bash
# 转换 lite 到标准格式（自动布局默认启用）
python workflow_cli.py convert --to-standard workflow.lite.json output.json
```

输出：
```
✓ Automatic node layout enabled
✓ Converted workflow.lite.json -> output.json
```

### 2. 禁用自动布局

```bash
# 转换时禁用自动布局（所有节点 pos=[0,0]）
python workflow_cli.py convert --to-standard --no-auto-layout workflow.lite.json output.json
```

输出：
```
⚠ Automatic node layout disabled (nodes will have pos=[0,0])
✓ Converted workflow.lite.json -> output.json
```

### 3. 显式启用自动布局

```bash
# 显式启用（与默认行为相同）
python workflow_cli.py convert --to-standard --auto-layout workflow.lite.json output.json
```

## 📊 布局示例

### 测试 Workflow

```json
{
  "version": "1.0",
  "nodes": {
    "input": {
      "type": "InputNode",
      "index": 1,
      "inputs": {},
      "outputs": ["data"]
    },
    "process1": {
      "type": "Process1Node",
      "index": 2,
      "inputs": {"input": {"node_id": 1, "output_name": "data"}},
      "outputs": ["result1"]
    },
    "process2": {
      "type": "Process2Node",
      "index": 3,
      "inputs": {"input": {"node_id": 1, "output_name": "data"}},
      "outputs": ["result2"]
    },
    "merge": {
      "type": "MergeNode",
      "index": 4,
      "inputs": {
        "in1": {"node_id": 2, "output_name": "result1"},
        "in2": {"node_id": 3, "output_name": "result2"}
      },
      "outputs": ["final"]
    }
  }
}
```

### 布局结果（启用自动布局）

```
节点 1 (InputNode     ): pos=[  50,   50]  (第0层 - 输入)
节点 2 (Process1Node  ): pos=[ 670,  232]  (第1层 - 并行分支)
节点 3 (Process2Node  ): pos=[ 670,   50]  (第1层 - 并行分支)
节点 4 (MergeNode     ): pos=[1290,   50]  (第2层 - 合并)
```

**可视化布局：**
```
        [InputNode]
           /     \
    [Process1]  [Process2]
           \     /
         [MergeNode]
```

### 布局结果（禁用自动布局）

```
节点 1 (InputNode     ): pos=[0, 0]
节点 2 (Process1Node  ): pos=[0, 0]
节点 3 (Process2Node  ): pos=[0, 0]
节点 4 (MergeNode     ): pos=[0, 0]
```

所有节点都在原点 (0, 0)。

## 🔧 命令行选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--auto-layout` | flag | True | 启用自动节点布局 |
| `--no-auto-layout` | flag | False | 禁用自动节点布局 |

## 💡 使用场景

### 启用自动布局（推荐）

**适用场景：**
- ✅ 从头创建新的 workflow
- ✅ 需要快速可视化 workflow 结构
- ✅ 不关心手动调整节点位置
- ✅ 希望获得清晰、一致的布局

**优势：**
- 自动按拓扑顺序排列
- 清晰的层级结构
- 适配 16:9 宽屏显示
- 易于理解数据流

### 禁用自动布局

**适用场景：**
- ✅ 需要保留原有的节点位置
- ✅ 已经手动调整过布局
- ✅ 节点位置由其他工具生成
- ✅ 需要所有节点从 (0,0) 开始

**注意：**
- 所有节点位置都是 [0, 0]
- 需要手动调整或使用其他工具布局

## 🎨 布局规则

### 层级分配规则

1. **第0层**：没有输入的节点（输入节点、独立节点）
2. **第1层**：依赖第0层节点的节点
3. **第2层**：依赖第1层节点的节点
4. **...依此类推**

### 位置计算规则

```python
# X 坐标（水平位置）
x = margin + layer_index * (node_width + horizontal_spacing)
x = 50 + layer_index * (270 + 350)
x = 50 + layer_index * 620

# Y 坐标（垂直位置）
y = margin + row_index * (node_height + vertical_spacing)
y = 50 + row_index * (82 + 100)
y = 50 + row_index * 182
```

### 示例计算

**第0层，第0行：**
- x = 50 + 0 × 620 = 50
- y = 50 + 0 × 182 = 50
- pos = [50, 50]

**第1层，第0行：**
- x = 50 + 1 × 620 = 670
- y = 50 + 0 × 182 = 50
- pos = [670, 50]

**第1层，第1行：**
- x = 50 + 1 × 620 = 670
- y = 50 + 1 × 182 = 232
- pos = [670, 232]

## 📝 完整示例

### 示例1：简单线性 workflow

```bash
# 创建 lite workflow
cat > linear.lite.json << 'EOF'
{
  "version": "1.0",
  "nodes": {
    "a": {"type": "A", "index": 1, "inputs": {}, "outputs": ["out"]},
    "b": {"type": "B", "index": 2, "inputs": {"in": {"node_id": 1, "output_name": "out"}}, "outputs": ["out"]},
    "c": {"type": "C", "index": 3, "inputs": {"in": {"node_id": 2, "output_name": "out"}}, "outputs": ["out"]}
  }
}
EOF

# 转换（启用自动布局）
python workflow_cli.py convert --to-standard linear.lite.json linear_auto.json

# 转换（禁用自动布局）
python workflow_cli.py convert --to-standard --no-auto-layout linear.lite.json linear_manual.json
```

**结果对比：**

| 节点 | 自动布局 pos | 禁用布局 pos |
|------|-------------|-------------|
| A    | [50, 50]    | [0, 0]      |
| B    | [670, 50]   | [0, 0]      |
| C    | [1290, 50]  | [0, 0]      |

### 示例2：并行 workflow

```bash
# 转换并行 workflow
python workflow_cli.py convert --to-standard parallel.lite.json parallel.json

# 查看节点布局
cat << 'EOF' | python3
import json
with open('parallel.json', 'r') as f:
    data = json.load(f)
for node in sorted(data["nodes"], key=lambda n: n['pos']):
    print(f"{node['type']}: pos={node['pos']}")
EOF
```

## 🔍 验证布局

转换后，可以验证节点位置是否正确：

```bash
# 查看输出文件的节点位置
cat << 'EOF' | python3
import json
import sys

if len(sys.argv) < 2:
    print("Usage: python check_layout.py <workflow.json>")
    sys.exit(1)

with open(sys.argv[1], 'r') as f:
    data = json.load(f)

print("节点布局:")
print("-" * 60)
for node in sorted(data["nodes"], key=lambda n: n['pos']):
    pos = node['pos']
    print(f"  {node['type']:20s}: pos=[{pos[0]:4d}, {pos[1]:4d}]")
EOF

python check_layout.py output.json
```

## 🚀 高级用法

### 结合其他选项

```bash
# 转换时同时使用 node info 和自动布局
python workflow_cli.py convert \
  --to-standard \
  --with-node-info \
  --auto-layout \
  workflow.lite.json output.json
```

### 批量转换

```bash
# 批量转换多个 lite 文件（都启用自动布局）
for file in *.lite.json; do
  output="${file%.lite.json}.json"
  python workflow_cli.py convert --to-standard "$file" "$output"
done
```

### 条件转换

```bash
# 只对包含特定节点的 workflow 启用自动布局
if grep -q "InputNode" workflow.lite.json; then
  python workflow_cli.py convert --to-standard --auto-layout workflow.lite.json output.json
else
  python workflow_cli.py convert --to-standard --no-auto-layout workflow.lite.json output.json
fi
```

## 🎯 总结

- **默认行为**：自动布局已启用（`--auto-layout`）
- **禁用方式**：使用 `--no-auto-layout` 标志
- **适用格式**：仅对 lite → standard 转换有效
- **布局规则**：拓扑排序 + 层级分组 + 16:9 适配

自动布局功能让 workflow 可视化变得轻松，无需手动调整节点位置！🎉
