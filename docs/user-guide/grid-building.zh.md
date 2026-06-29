# 构建网格

`GridBuilder` 将一个 SR3 网格时间步的原始数组转换为 PyVista
`UnstructuredGrid`，并为每个单元打上 `DataMapper` 后续附加属性值所需的 ID。

```python
from sr3kit import SR3Indexer, GridBuilder

with SR3Indexer("test/lgr_nested/lgr_nested.sr3", eager_list_steps=None) as sr3:
    grid = GridBuilder(sr3).build(grid_mode="mixed")  # 类型自动从 IGNTGT 检测
```

## `build()` 参数

| 参数 | 默认值 | 含义 |
|---|---|---|
| `grid_type` | `None`（自动检测） | `"Cartesian"`、`"CornerPoint"` 或 `"Radial"`。当为 `None` 时，从文件 `IGNTGT[0]` 推断（`1=Cartesian`、`2=Radial`、`12=CornerPoint`）。显式传入会覆盖自动检测；如与文件冲突会记录警告。 |
| `grid_mode` | `"mixed"` | LGR 显示模式（见下文）。 |
| `include_inactive` | `False` | 保留无属性槽（`ICSTPS<=0`）或被 `IPSTAC` 标记为非活跃的单元。 |
| `keep_refined_parents` | `True` | 即使 `include_inactive=False`，仍在网格中保留 LGR 细化父单元。这些单元只是因为被子单元替换而显示为"非活跃"，但它们是 `DataMapper.map_prop(aggregate=True)` 的聚合落点；缺失会导致聚合在 level-N 网格上悄无声息地变成空操作。设为 `False` 可恢复旧行为。 |
| `time_step` | `0` | 读取几何体所用的网格时间步。 |
| `merge_points` | `True` | 构建后合并重合角点（网格更小、更快）。 |
| `merge_tolerance` | `1e-10` | 两点被视为相同的距离阈值。 |

!!! note "几何时间步与结果时间步"
    几何体通常仅在少数时间步写出。`build(time_step=t)` 读取 `t` 处的 GRID 定义；
    `DataMapper` 在映射任意结果时间步的属性时会独立解析最近的网格时间步。

## LGR 显示模式

局部网格细化（`*REFINE`）在同一文件中同时保存父单元和子单元。`grid_mode`
控制哪些单元被显示：

=== "mixed（默认）"

    未细化的 0 级单元**以及**所有 LGR 叶节点单元。已被子单元完全替代的父单元
    将被丢弃，从而避免重复绘制。这是可视化的推荐选项。

=== "refined"

    仅细化单元（`Level > 0`）。

=== "levelN"

    仅指定层级的单元：`"level0"`、`"level1"`、`"level2"`……

```python
builder = GridBuilder(sr3)
mixed    = builder.build("Cartesian", grid_mode="mixed")
refined  = builder.build("Cartesian", grid_mode="refined")
level0   = builder.build("Cartesian", grid_mode="level0")
```

底层模型详见[网格类型](concepts/grid-types.md)和 [DFN 与 LGR](concepts/dfn-vs-lgr.md)。

## 单元数据数组

每个构建好的矩阵网格均携带以下逐单元数组：

| 数组 | 类型 | 含义 |
|---|---|---|
| `PropGlobalID` | int32 | `ICSTPS - 1`；属性数组中的索引。`-1` 表示非活跃。 |
| `GlobalCellID` | int | SR3 文件中以 0 为基的线性单元索引。 |
| `Level` | int16 | LGR 层级（0 = 基础网格）。 |
| `I`、`J`、`K` | int32 | 单元所在分段内的局部结构化索引。 |
| `ParentI/J/K` | int32 | 细化单元的父单元 I/J/K；0 级处为 `-1`。 |

`PropGlobalID` 和 `GlobalCellID` 是属性映射得以实现的两个关键字段——详见
[数据模型与类型](../developer-guide/data-model.md)。

## 嵌入式 DFN 曲面

离散裂缝网络**不是** LGR。它单独存储，并通过专用方法构建，返回二维四边形曲面：

```python
builder = GridBuilder(sr3)
matrix       = builder.build("CornerPoint")     # the matrix grid
dfn_units    = builder.build_dfn_units()        # original DFU quads
dfn_segments = builder.build_dfn_segments()     # embedded segment quads
```

`build_dfn_segments()` 会打上 `PropGlobalID`（以便将 `PRES`/`SO`/…映射到裂缝段），
并附上 `HostGlobalCellID` 和 `Host I/J/K`，将每个段链接到其宿主矩阵单元。
当文件不含 DFN 时，两个方法均返回空网格。详见 [DFN 与 LGR](concepts/dfn-vs-lgr.md)。

## 映射属性

构建好网格后，使用 `DataMapper` 附加结果：

```python
from sr3kit import DataMapper

df = DataMapper(sr3).map_prop(grid, keywords=["PRES", "SO"], time_steps=[0])
```

对于包含父单元的网格（例如 `grid_mode="level0"`），可启用自底向上聚合，
使父单元显示其子单元的均值/求和/最小值/最大值：

```python
agg = DataMapper(sr3).map_prop(level0, "PRES", 0, aggregate=True, agg_method="mean")
```

结果为具有 6 级列索引的 DataFrame：
`(Keyword, LongName, Unit, Time, TimeIndex, TimeUnit)`；
详见 [`DataMapper.map_prop`](../api/data-mapper.md)。
