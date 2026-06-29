# 坐标系与显示比例

在 CMG SR3 中，**Z 通常表示深度**，且向下递增。大多数三维可视化工具采用 **Z-up** 惯例（向上为正）。因此，以原始 SR3 深度显示的角点网格可能呈现为垂直翻转的状态。

## 核心构建坐标与显示坐标

sr3kit 将两者分开处理：

| 文件 | 用途 |
|---|---|
| `grid.vtu` | 核心**构建**坐标——权威几何数据。 |
| `grid_display.vtu` | **显示**副本——可翻转 Z 轴并应用垂向夸张比例。 |
| `overview.png`, `slice.png` | 从显示副本渲染而来。 |

!!! warning
    切勿将显示比例坐标反馈到数值计算中。任何定量工作请使用 `grid.vtu`（核心构建坐标）。

## 各网格族的输出

| 网格来源 | 核心 Z | 说明 |
|---|---|---|
| `Cartesian` / `VARI` | 通常 Z-up | 正值 `BLOCKDEPTH` 被转换为负 Z |
| `Radial` | 局部厚度 | 从局部厚度构建，而非绝对埋深 |
| `CornerPoint` `NODES/BLOCKS` | 通常为深度 | Z 向下递增 |
| `CornerPoint` `XCORNCRCN/...` | 通常为深度 | 包含转换为角点的情形 |

由于大多数角点网格 SR3 文件存储深度，导出器对角点情形默认使用 `depth-up` 显示模式。

## 显示 Z 模式

| 模式 | 含义 | 适用场景 |
|---|---|---|
| `keep` | 保持当前 Z，仅进行平移/缩放 | 网格已为 Z-up |
| `depth-up` | 将正值向下深度转换为 Z-up | 大多数 `CornerPoint` SR3 |
| `flip` | 翻转当前 Z 方向 | 手动检查发现网格上下颠倒 |

默认值：`Cartesian`、`VARI`、`Radial` 和 LGR 使用 `keep`；角点情形使用 `depth-up`。

## 垂向夸张

储层模型通常宽而薄，因此导出器默认将 Z 夸张 10 倍。可通过命令行控制：

```bash
# vertical exaggeration of 20×
python tools/export_case_assets.py --case tutorial_hm --scale-z 20

# per-axis scale
python tools/export_case_assets.py --case tutorial_hm --scale-x 1 --scale-y 1 --scale-z 20

# no exaggeration
python tools/export_case_assets.py --scale-z 1

# force a specific Z mode for all cases
python tools/export_case_assets.py --z-mode keep
python tools/export_case_assets.py --z-mode flip
```
