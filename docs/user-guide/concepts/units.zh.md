# 单位与换算

CMG SR3 文件中的每个属性都以 CMG 所谓的两种单位之一存储:**Output Unit**（实际写入字节所用的单位 — 由用户在 DAT 中通过 `*INUNIT`/`*OUTUNIT` 选择）和 **Internal Unit**（CMG 求解器内部使用的单位 — kPa、K、m、m²、day……）。`pysr3` 同时读取两者，并通过统一的 `to_unit=` 参数让你按需获取任一种,或文件 `UnitConversionTable` 中已知的任意具体单位。

## 变量的单位从何而来

由三张 HDF5 表协作得到。**没有任何**单一标签表示"这是 FIELD 系统";单位系统按**每个量纲**分别编码。

```
NameRecordTable[keyword].Dimensionality       例如 "3|"  或  "11|-13|"
                       │
                       ▼
UnitsTable[idx].Output Unit  /  Internal Unit  例如 "kPa"、"F"、"cm3"
                       │
                       ▼  （当请求特定单位换算时）
UnitConversionTable[(dim, unit)] -> (Gain, Offset)
   canonical = stored * Gain + Offset
```

例如,`OILRATSC`（地表条件下的油相体积流率）的 `Dimensionality = "11|-13|"`:第 11 维度（Well Liquid Volume）除以第 13 维度（Well Rate Time）。如果 SR3 中第 11 维度的 `Output Unit = cm3`、第 13 维度的 `Output Unit = min`,则 `OILRATSC` 数据以 `cm³/min` 存储。换成 SI 输出,就变成 `m³/day`。

## `to_unit` 参数

每个返回数值的方法都接受相同的取值:

| `to_unit`         | 对数值的影响                | 对 `Unit` 标签的影响                       |
|-------------------|---------------------------|--------------------------------------------|
| `"output"`（默认）| 无（保留存储字节）          | `UnitsTable.Output Unit`                   |
| `"internal"`      | 逐 token 经 UCT 换算        | `UnitsTable.Internal Unit`                 |
| `"psi"`/`"MPa"`/`"md"`/… | 经 UCT 换算（仅单一正向维度 keyword） | 用户请求的单位字符串       |

**标签始终与数值保持一致** —— 它们是一起变化的。

```python
from pysr3 import SR3Indexer, GridBuilder
from pysr3.data_mapper import DataMapper

with SR3Indexer("model.sr3") as sr3:
    # 井底压力:存储为 kPa,以 psi 输出
    df = sr3.get_well_data(variable_names=["BHP"], to_unit="psi")

    # 空间映射:本文件 TEMP 存储为 F (*INUNIT FIELD),以 K 显示
    grid = GridBuilder(sr3).build("Cartesian")
    df_int = DataMapper(sr3).map_prop(grid, "TEMP", 0, to_unit="internal")

    # 查询可用信息
    print(sr3.get_unit("OILRATSC"))               # 'cm3/min'  (Output)
    print(sr3.get_unit("OILRATSC", "internal"))   # 'm3/day'   (Internal)
```

## 底层细节

```python
sr3.units                     # {dim_idx: {output_unit, internal_unit, dimensionality}}
sr3.unit_conversions          # {dim_idx: {unit_name: (gain, offset)}}
sr3.get_unit(keyword)          # 在任意策略下返回单位字符串
sr3.convert(keyword, values, to_unit)  # 实际换算函数,对数组矢量化处理
```

换算表由 CMG 提供;`pysr3` 仅读取并组合,**无需** `pint` 等外部单位库。

## 两个隐性例外

1. **`MasterTimeTable` 时间偏移**始终以 **days** 存储,与文件的 Output Time 单位无关（该列的表头确实就叫 `"Offset in days"`）。`pysr3.get_time_offset()` 直接按 days 返回。流率分母（`OILRATSC = Volume / WellRateTime`）则遵循 Output Unit 设定。

2. **温度规范化单位为 `C`** —— 在 `UnitConversionTable` 中,而 `UnitsTable.Internal Unit` 中温度记作 `K`。`pysr3.convert` 自动级联 `stored → C → K`;除非你直接读取 UCT,否则无需关心这件事。
