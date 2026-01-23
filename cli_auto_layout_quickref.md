# CLI 自动布局快速参考

## 🚀 快速开始

### 基本命令

```bash
# 转换 lite 到标准（默认启用自动布局）
python workflow_cli.py convert --to-standard input.lite.json output.json

# 禁用自动布局
python workflow_cli.py convert --to-standard --no-auto-layout input.lite.json output.json

# 显式启用自动布局
python workflow_cli.py convert --to-standard --auto-layout input.lite.json output.json
```

## 📊 布局效果

### 线性 Workflow (A → B → C)

```
输入:  input.lite.json
输出:  output.json (带自动布局)

布局结果:
  A: pos=[  50,   50]  (第0层)
  B: pos=[ 670,   50]  (第1层)
  C: pos=[1290,   50]  (第2层)

可视化:
[A] → [B] → [C]
```

### 并行 Workflow (A → [B, C] → D)

```
输入:  parallel.lite.json
输出:  parallel.json (带自动布局)

布局结果:
  A: pos=[  50,   50]  (第0层)
  B: pos=[ 670,   50]  (第1层)
  C: pos=[ 670,  232]  (第1层)
  D: pos=[1290,   50]  (第2层)

可视化:
       [A]
      /   \
    [B]   [C]
      \   /
       [D]
```

## 🔧 选项对比

| 命令 | 自动布局 | 节点位置 |
|------|---------|---------|
| `--to-standard` | ✅ 启用（默认） | 自动计算 |
| `--to-standard --auto-layout` | ✅ 启用 | 自动计算 |
| `--to-standard --no-auto-layout` | ❌ 禁用 | 全部 [0,0] |

## 📐 布局参数

```python
节点宽度:   270px
节点高度:   82px
水平间距:   350px
垂直间距:   100px
页边距:     50px

列间距:     270 + 350 = 620px
行间距:     82 + 100 = 182px
```

## 💡 使用建议

### ✅ 使用自动布局（推荐）
- 新创建的 workflow
- 需要快速可视化
- 不关心手动调整位置

### ❌ 禁用自动布局
- 需要保留原有位置
- 已手动调整过布局
- 由其他工具生成位置

## 📝 实际示例

```bash
# 示例1: 转换并自动布局
python workflow_cli.py convert --to-standard workflow.lite.json output.json

# 输出:
# ✓ Automatic node layout enabled
# ✓ Converted workflow.lite.json -> output.json

# 示例2: 转换但不使用自动布局
python workflow_cli.py convert --to-standard --no-auto-layout workflow.lite.json output.json

# 输出:
# ⚠ Automatic node layout disabled (nodes will have pos=[0,0])
# ✓ Converted workflow.lite.json -> output.json

# 示例3: 结合 node info 使用
python workflow_cli.py convert --to-standard --with-node-info workflow.lite.json output.json
```

## 🎯 关键点

1. **默认启用** - lite → standard 转换时自动布局默认开启
2. **易于禁用** - 使用 `--no-auto-layout` 即可禁用
3. **拓扑排序** - 节点按依赖关系从左到右排列
4. **层级分组** - 相同层级的节点在同一列
5. **宽屏适配** - 间距参数适配 16:9 显示器

## 🔍 验证结果

```bash
# 快速查看节点位置
python << 'EOF'
import json
with open('output.json') as f:
    data = json.load(f)
for node in sorted(data["nodes"], key=lambda n: n['pos']):
    print(f"{node['type']}: pos={node['pos']}")
EOF
```

---

**提示**: 运行 `python workflow_cli.py --help` 查看完整选项列表。
