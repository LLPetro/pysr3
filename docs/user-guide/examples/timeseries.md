# Time-series examples

## One well's BHP

```python
from pysr3 import SR3Indexer

with SR3Indexer("test/cartesian/cartesian.sr3") as sr3:
    df = sr3.get_well_data(well_names=["STEAM INJT"], variable_names=["BHP"])

print(df.head())
```

## Oil rate for all wells

```python
with SR3Indexer("test/50the_datafile/tutorial_hm.sr3") as sr3:
    df = sr3.get_well_data(variable_names=["OILRATSC"])
```

## Layer time series

```python
with SR3Indexer("test/convert_to_corner/convert_to_corner.sr3") as sr3:
    df = sr3.get_timeseries_data(entity="LAYERS", variables=["WATVOLSC", "OILRATSC"])
```

## Discover what's available

```python
with SR3Indexer("test/radial/radial.sr3") as sr3:
    print(sr3.get_timeseries_entities())       # which entities exist
    info = sr3.get_timeseries_info("WELLS")
    print(info["origins"])                     # well names
    print(info["variables"])                   # variable keywords
```

## Export to CSV

```bash
# all entities for all cases
python tools/export_timeseries_assets.py

# only wells
python tools/export_timeseries_assets.py --entity WELLS

# a single case
python tools/export_timeseries_assets.py --case tutorial_hm --entity WELLS
```

Output:

```text
test/<case>/timeseries/
  wells.csv
  layers.csv
  groups.csv
  summary.json
```
