# 角点网格

## 目标

了解 `CornerPoint` 网格、Z 方向显示坐标，以及同时包含 DFN 的
`*CONVERT-TO-CORNER-POINT` 案例。

## 读取角点网格

```python
from pysr3 import SR3Indexer, GridBuilder

with SR3Indexer("test/convert_to_corner/convert_to_corner.sr3") as sr3:
    grid = GridBuilder(sr3).build(grid_type="CornerPoint")

print(grid.n_cells)
```

## 转换为角点的案例

此案例来源于 STARS 模板，其 DAT 文件包含：

```text
*GRID *CART
*CONVERT-TO-CORNER-POINT
*BEGIN_DFN
```

SR3 为基质网格输出角点几何（以 `CornerPoint` 方式构建）。
DFN 是一组独立的嵌入式裂缝面 —— 而非局部网格细化(LGR)。

![Convert to corner overview](../../assets/images/convert_to_corner_overview.png)

## 中心切片

![Convert to corner slice](../../assets/images/convert_to_corner_slice.png)

图中垂直黑色面为一个 DFN 片段。它穿过中间的空层，但**并非**对该层的体积填充。

## 读取 DFN

```python
from pysr3 import SR3Indexer, GridBuilder, DataMapper

with SR3Indexer("test/convert_to_corner/convert_to_corner.sr3", eager_list_steps=None) as sr3:
    builder = GridBuilder(sr3)
    matrix       = builder.build("CornerPoint")
    dfn_segments = builder.build_dfn_segments()
    dfn_units    = builder.build_dfn_units()
    pressure     = DataMapper(sr3).map_prop(dfn_segments, "PRES", 0)

print(matrix.n_cells)        # 294
print(dfn_segments.n_cells)  # 6
print(dfn_units.n_cells)     # 2
```

## 关于 Z 方向的说明

大多数角点 SR3 文件以深度形式存储 Z（向下递增），因此导出器对角点案例
默认采用 `depth-up` 显示方式。参见
[DFN 与 LGR](../concepts/dfn-vs-lgr.md) 及
[坐标系](../concepts/coordinate-system.md)。
