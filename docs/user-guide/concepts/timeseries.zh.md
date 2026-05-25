# 井与时序

SR3 将时序结果存储于 `/TimeSeries` 下。pysr3 针对以下实体进行通用读取：

- `WELLS`
- `LAYERS`
- `GROUPS`
- `SECTORS`
- `SPECIAL HISTORY`

## 数据轴顺序

在 STARS SR3 中，`TimeSeries/<entity>/Data` 是一个按以下顺序排列的三维数组：

```text
(time, variable, origin)
```

其中 `time` ↔ `Timesteps`，`variable` ↔ `Variables`，`origin` ↔ `Origins`（井/层/组/扇区名称）。`WELLS` 只是其中一种实体。pysr3 自动处理此轴顺序，并返回长格式（整洁）DataFrame。

## 核心 API

```python
from pysr3 import SR3Indexer

with SR3Indexer("test/cartesian/cartesian.sr3") as sr3:
    print(sr3.get_timeseries_entities())          # ['GROUPS', 'LAYERS', 'WELLS', ...]
    info = sr3.get_timeseries_info("WELLS")        # origins, variables, timesteps, shape

    df = sr3.get_well_data(
        well_names=["STEAM INJT"],
        variable_names=["BHP"],
        timesteps=info["timesteps"][:3],
    )
```

通用读取器适用于任意实体：

```python
with SR3Indexer("test/convert_to_corner/convert_to_corner.sr3") as sr3:
    df = sr3.get_timeseries_data(entity="LAYERS", variables=["WATVOLSC"])
```

## 输出列

`get_timeseries_data` 返回每个（时间、来源、变量）组合对应一行：

| 列名 | 含义 |
|---|---|
| `Entity` | TimeSeries 实体名称 |
| `Origin` | 井/层/组/扇区名称 |
| `Variable` | 变量关键字 |
| `TimeIndex` | SR3 时间步编号 |
| `Time` | 时间偏移量 |
| `Date` | 日期字符串（由 SR3 提供时） |
| `Value` | 数值 |
| `Unit` | 从 `NameRecordTable` 推断的单位 |

`get_well_data` 是 `WELLS` 实体的便捷封装，额外增加 `Well` 列。完整签名详见 [`SR3Indexer`](../../api/indexer.md)，更多用法示例详见[时序示例](../examples/timeseries.md)。
