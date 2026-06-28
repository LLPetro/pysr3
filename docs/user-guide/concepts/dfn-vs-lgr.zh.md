# DFN vs LGR

DFN 和 LGR 都会使网格关系变得复杂，但它们是**不同类型的对象**，pysr3 使用不同方法构建它们。

| | LGR | DFN |
|---|---|---|
| 来源关键字 | `*REFINE` | `*BEGIN_DFN` |
| 几何含义 | 将父单元细化为子六面体 | 嵌入式二维裂缝面 |
| SR3 数组 | `IGNTNC` 段 + `ICSTPB` 父指针 | `DFUCO*`, `SGCOR*`, `ISGT*` |
| 构建方法 | `GridBuilder.build(..., grid_mode=...)` | `build_dfn_units()`, `build_dfn_segments()` |

**LGR** 是体积细化。`mixed` 模式同时保留未细化的父单元和叶子子单元，避免重复绘制。

**DFN** 是一组嵌入基质网格中的二维裂缝面。它*不是*空层的六面体填充，也不出现在基质网格的层级体系中。

## 转换为角点的情形

`test/convert_to_corner/convert_to_corner.dat` 组合使用了：

```text
*GRID *CART
*CONVERT-TO-CORNER-POINT
*BEGIN_DFN
```

CMG Results 报告共 315 个基质块、294 个活跃块，以及 1 个含 2 个 DFU 的 DFN。pysr3 可复现此结果：

```python
from pysr3 import SR3Indexer, GridBuilder

with SR3Indexer("test/convert_to_corner/convert_to_corner.sr3", eager_list_steps=None) as sr3:
    builder = GridBuilder(sr3)
    matrix       = builder.build("CornerPoint")
    dfn_segments = builder.build_dfn_segments()
    dfn_units    = builder.build_dfn_units()

print(matrix.n_cells)        # 294
print(dfn_segments.n_cells)  # 6
print(dfn_units.n_cells)     # 2
```

中心切片显示裂缝（黑色）穿过中间空层——这是一个面，而非体积：

![转换为角点的切片](../../assets/images/convert_to_corner_slice.png)

## 多个 DFU

`test/dfn_multi/dfn_multi.dat` 将 DFU 数量增加至 4，并分别指定 `*PERM-DF`、`*APER-DF` 和 `*POR-DF`：

```text
*BEGIN_DFN 'dfn_multi' CMG 4
  *PERM-DF *ALL 800 1200 1600 2000
  *APER-DF *ALL 0.05 0.08 0.10 0.12
```

pysr3 读取到 4 个 DFU 和 12 个活跃段，`DFUAPT = 0.05/0.08/0.10/0.12`，`DFUPERM = 800/1200/1600/2000`。

## DFN_REFINE

`*DFN_REFINE` 自动在裂缝周围生成 LGR，但 DFN 段仍保持为独立面：

```text
*DFN_REFINE 'dfn_refine' *MINVOL 100000 *INTO 2 1 2 *MAXLVL 3
```

对于 `test/dfn_refine/dfn_refine.sr3`：基质 `mixed` 网格在 0/1/2 层级上共有 402 个单元；共有 4 个 DFU、36 个活跃段，以及 60 个总段（`include_inactive=True`）。该 SR3 不输出角点数组，因此 `CornerPoint` 会自动回退至笛卡尔/LGR 数组。

![DFN 细化总览](../../assets/images/dfn_refine_overview.png)

## 关键 SR3 数组

**基质网格**

- `XCORNCRCN/YCORNCRCN/ZCORNCRCN` — 角点坐标。
- `ICSTPS` — 将几何单元映射到其属性槽。
- `IPSTAC` — 每个属性槽的活跃标志。仅检查 `ICSTPS > 0` 会将空层宿主单元计为活跃；pysr3 同时检查 `IPSTAC`。

**DFN**

- `DFUCOX/Y/Z`, `DFUTNL`, `IUTDF` — 原始 DFU 四边形、节点范围、DFN 索引。
- `SGCORX/Y/Z`, `ISGTPS` — 嵌入段四边形及其属性槽。
- `ISGTDU` — 每个段所属的 DFU。
- `IPSTCS` — 每个段的宿主基质单元。

完整术语表详见[数据模型与类型](../../developer-guide/data-model.md)。

## 可视化建议

将基质网格与 DFN 段分别导出后叠加显示。对于 DFN 情形，`tools/export_case_assets.py` 会写入：

```text
grid.vtu  grid_display.vtu
dfn_segments.vtu  dfn_segments_display.vtu  dfn_units.vtu
overview.png  slice.png  summary.json
```
