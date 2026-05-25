# 井时序数据

## 目标

读取井的时序结果，将其导出为 CSV，并绘制 BHP 曲线。

## 读取单口井的 BHP

```python
from pysr3 import SR3Indexer

with SR3Indexer("test/cartesian/cartesian.sr3") as sr3:
    df = sr3.get_well_data(well_names=["STEAM INJT"], variable_names=["BHP"])

print(df.head())
```

## 导出为 CSV

```bash
python tools/export_timeseries_assets.py --case cartesian --entity WELLS
```

输出：

```text
test/cartesian/timeseries/wells.csv
```

## 绘制曲线

```python
import matplotlib.pyplot as plt
from pysr3 import SR3Indexer

with SR3Indexer("test/cartesian/cartesian.sr3") as sr3:
    df = sr3.get_well_data(well_names=["STEAM INJT"], variable_names=["BHP"])

plt.plot(df["Time"], df["Value"])
plt.xlabel("Time")
plt.ylabel(f"BHP [{df['Unit'].iloc[0]}]")
plt.tight_layout()
plt.savefig("well_bhp_curve.png", dpi=120)
```

![Well BHP curve](../../assets/images/well_bhp_curve.png)

## 原理说明

STARS SR3 以轴顺序 `(time, variable, origin)` 存储时序数据。
`get_well_data` 按该顺序读取并返回长格式 DataFrame，每行对应一个
（时间步、井、变量）组合。参见[井与时序](../concepts/timeseries.md)。
