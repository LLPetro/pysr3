# 时序示例

## 单口井的 BHP

```python
from pysr3 import SR3Indexer

with SR3Indexer("test/cartesian/cartesian.sr3") as sr3:
    df = sr3.get_well_data(wells=["STEAM INJT"], variables=["BHP"])

print(df.head())
```

## 所有井的产油速率

```python
with SR3Indexer("test/50the_datafile/tutorial_hm.sr3") as sr3:
    df = sr3.get_well_data(variables=["OILRATSC"])
```

## 层时序

```python
with SR3Indexer("test/convert_to_corner/convert_to_corner.sr3") as sr3:
    df = sr3.get_timeseries_data(entity="LAYERS", variables=["WATVOLSC", "OILRATSC"])
```

## 查询可用内容

```python
with SR3Indexer("test/radial/radial.sr3") as sr3:
    print(sr3.get_timeseries_entities())       # which entities exist
    info = sr3.get_timeseries_info("WELLS")
    print(info["origins"])                     # well names
    print(info["variables"])                   # variable keywords
```

## 导出为 CSV

```bash
# all entities for all cases
python tools/export_timeseries_assets.py

# only wells
python tools/export_timeseries_assets.py --entity WELLS

# a single case
python tools/export_timeseries_assets.py --case tutorial_hm --entity WELLS
```

输出：

```text
test/<case>/timeseries/
  wells.csv
  layers.csv
  groups.csv
  summary.json
```
