# Wells & time series

SR3 stores time-series results under `/TimeSeries`. pysr3 reads them generically
for these entities:

- `WELLS`
- `LAYERS`
- `GROUPS`
- `SECTORS`
- `SPECIAL HISTORY`

## Data axis order

In STARS SR3, `TimeSeries/<entity>/Data` is a 3D array ordered:

```text
(time, variable, origin)
```

where `time` ↔ `Timesteps`, `variable` ↔ `Variables`, and `origin` ↔ `Origins`
(well/layer/group/sector names). `WELLS` is just one such entity. pysr3 reads
this axis order for you and returns a long-form (tidy) DataFrame.

## Core API

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

The generic reader works for any entity:

```python
with SR3Indexer("test/convert_to_corner/convert_to_corner.sr3") as sr3:
    df = sr3.get_timeseries_data(entity="LAYERS", variables=["WATVOLSC"])
```

## Output columns

`get_timeseries_data` returns one row per (time, origin, variable):

| Column | Meaning |
|---|---|
| `Entity` | TimeSeries entity name |
| `Origin` | well / layer / group / sector name |
| `Variable` | variable keyword |
| `TimeIndex` | SR3 time-step number |
| `Time` | time offset |
| `Date` | date string, when provided by the SR3 |
| `Value` | the numeric value |
| `Unit` | unit inferred from `NameRecordTable` |

`get_well_data` is a convenience wrapper around the `WELLS` entity that adds a
`Well` column. See [`SR3Indexer`](../../api/indexer.md) for full signatures and
the [time-series examples](../examples/timeseries.md) for more recipes.
