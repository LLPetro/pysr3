# 体积与加权聚合

当 `DataMapper.map_prop(..., aggregate=True)` 将 LGR 子单元向父单元聚合时，**采用哪种加权方法**至关重要。简单的 `'mean'` 对所有子单元等权处理 —— 在子单元体积或孔隙含量不同时，几乎都不正确。CMG SR3 为此专门提供了两个逐单元体积数组，pysr3 通过两个 `agg_method` 取值进行暴露。

## 两个体积数组

| 数组 | NRT Long Name | 含义 | 存储路径 |
|---|---|---|---|
| `MODBVOL` | "Modified Block Volume" | 每个单元的 **总块体积**（完整块 × 体积修正系数；与流体/孔隙度无关） | `/SpatialProperties/<step>/MODBVOL` |
| `BLOCKPVOL` | "Block pore volume" | **孔隙体积** = bulk × 孔隙度 × NTG。实际能容纳流体的岩石体积 | `/SpatialProperties/<step>/GRID/BLOCKPVOL` |

两者都是静态量 —— 仅在 GRID 时间步写入 —— 并通过 `PropGlobalID = ICSTPS - 1` 按单元索引。

对 multibranch 文件的健全性比值：`BLOCKPVOL / MODBVOL ≈ 0.34–0.37`，即有效孔隙度。两数组同形状，比例由孔隙度 × NTG 决定。

## 该用哪种加权？

| `agg_method` | 权重来源 | 适用于…… |
|---|---|---|
| `'mean'` | （无） | 仅用于快速查看；假设子单元一致。LGR 或非均匀网格通常会产生误导。 |
| `'bulk_volume_mean'` | `MODBVOL` | 几何/强度量（温度、深度加权标量）。块体积加权平均。 |
| `'pore_volume_mean'` | `BLOCKPVOL` | **流体属性** —— 单相压力、饱和度、摩尔分数、STOIIP 计算等。容纳流体的岩石体积是天然权重。 |

## 工作示例

```python
from pysr3 import SR3Indexer, GridBuilder
from pysr3.data_mapper import DataMapper

with SR3Indexer("test/lgr_nested/lgr_nested.sr3") as sr3:
    grid = GridBuilder(sr3).build(grid_mode="level0")  # 默认保留父单元
    mapper = DataMapper(sr3)

    p_pore = mapper.map_prop(grid, "PRES", 0, aggregate=True, agg_method="pore_volume_mean")
    p_bulk = mapper.map_prop(grid, "PRES", 0, aggregate=True, agg_method="bulk_volume_mean")
    p_arith = mapper.map_prop(grid, "PRES", 0, aggregate=True, agg_method="mean")
```

聚合流体压力时，请优先使用 `'pore_volume_mean'`。

## 直接读取体积数组

两者都可通过同一个 `get_property_data` API 获取：

```python
sr3.get_property_data("MODBVOL",   0)   # 每个活跃单元的块体积
sr3.get_property_data("BLOCKPVOL", 0)   # 每个活跃单元的孔隙体积
sr3.get_grid_array("BLOCKPVOL",   0)    # 等价，不依赖 /GRID/ 回退逻辑
```

`pysr3` 先在 `/SpatialProperties/<step>/<name>` 中查找，找不到则回退到 `/SpatialProperties/<step>/GRID/<name>` —— 因此同一个调用对两种存储路径都有效。

## 边界情况

- **`BLOCKPVOL == 0` 的单元**（例如零孔隙度层、DFN 文件中的纯裂缝单元）：视为"无权重"，避免它们主导父单元。聚合器过滤 `w > 0` 并跳过这些单元。
- **某父单元的所有子单元孔隙体积为零**：父单元保留为 `NaN` —— pysr3 不会悄悄替换为块体积。
- **缺少 `BLOCKPVOL` 的文件**（极旧的 SR3 版本；pysr3 的 12 个内置 fixture 都不存在此情况）：`agg_method='pore_volume_mean'` 会发出包含缺失关键字的警告，并降级到 `'mean'` —— 与现有 MODBVOL 缺失时的体验保持一致。
