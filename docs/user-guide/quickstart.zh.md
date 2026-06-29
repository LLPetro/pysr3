# 快速开始

本页演示大多数工作流的基础：最简 **读取 → 构建 → 映射** 流程。

## 完整流程

```python
from sr3kit import SR3Indexer, GridBuilder, DataMapper

sr3_path = "test/cartesian/cartesian.sr3"

with SR3Indexer(sr3_path, eager_list_steps=None) as sr3:
    # 1. Build a PyVista grid from the first grid time step.
    grid = GridBuilder(sr3).build(
        grid_type="Cartesian",
        grid_mode="mixed",
        time_step=0,
    )

    # 2. Map pressure onto the grid cells, for every time step that has it.
    pres = DataMapper(sr3).map_prop(
        grid=grid,
        keywords="PRES",
        time_steps=sr3.get_spatial_time_steps(),
    )

print(grid.n_cells)   # number of cells in the mesh
print(pres.head())    # labelled DataFrame, one column per (property, time)
```

## 逐步说明

1. **打开** SR3 文件，使用 `SR3Indexer`。始终以上下文管理器方式（`with …`）使用，
   以确保 HDF5 句柄被自动关闭。
2. **构建** 网格，使用 `GridBuilder` 并传入[网格类型](#choosing-a-grid-type)。
3. **映射** SR3 空间属性到网格单元，使用 `DataMapper`。

!!! info "`eager_list_steps`"
    `SR3Indexer(path, eager_list_steps=None)` 为每个时间步索引属性列表。
    默认值（`0`）仅索引第一个时间步，对于大文件速度更快；其他时间步的属性随后按需获取。

## 选择网格类型 { #choosing-a-grid-type }

`GridBuilder.build(grid_type=...)` 当前支持：

| `grid_type` | CMG 网格关键字 |
|---|---|
| `"Cartesian"` | `*GRID *CART`、`*GRID *VARI` 及常规 LGR |
| `"Radial"` | `*GRID *RADIAL` |
| `"CornerPoint"` | `*GRID *CORNER`（及 `*CONVERT-TO-CORNER-POINT`） |

也可在运行时通过 `sr3kit.available_grid_types()` 获取列表。
各类型读取的 SR3 数组详见[网格类型](concepts/grid-types.md)。

## 常用 `grid_mode` 值

对于含局部网格细化（`*REFINE`）的模型：

| `grid_mode` | 显示内容 |
|---|---|
| `"mixed"`（默认） | 未细化的 0 级单元**加上**所有 LGR 叶节点单元 |
| `"refined"` | 仅细化单元（level > 0） |
| `"level0"`、`"level1"`、… | 仅指定层级的单元 |

完整参考请参阅[构建网格](grid-building.md)。

## 保存与可视化

构建好的网格是标准的 PyVista 网格，可直接保存或绘图：

```python
grid.save("grid.vtu")                  # open in ParaView
grid.plot(scalars=None, show_edges=True)   # interactive window
```

为所有内置案例重新生成 VTU 和 PNG 资产：

```bash
python tools/export_case_assets.py
python tools/export_case_assets.py --case tutorial_hm   # a single case
```

每个案例将输出写入各自的 `artifacts/` 目录。显示选项详见
[网格可视化](tutorials/grid-visualization.md)。
