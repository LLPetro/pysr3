# Units & conversion

CMG SR3 files store every property in one of two unit systems CMG calls
**Output Unit** (what the bytes are written in — chosen by the user via
`*INUNIT`/`*OUTUNIT` in the DAT) and **Internal Unit** (CMG's solver
units — kPa, K, m, m², day, …). `pysr3` reads both and exposes a single
`to_unit=` argument that lets you request either, or any specific unit
the file's `UnitConversionTable` knows about.

## Where the unit of a variable comes from

Three HDF5 tables collaborate. None of them carries a single "this is the FIELD
system" flag — the system is encoded **per dimension**.

```
NameRecordTable[keyword].Dimensionality       e.g. "3|"  or  "11|-13|"
                       │
                       ▼
UnitsTable[idx].Output Unit  /  Internal Unit  e.g. "kPa", "F", "cm3"
                       │
                       ▼  (if a specific unit conversion is requested)
UnitConversionTable[(dim, unit)] -> (Gain, Offset)
   canonical = stored * Gain + Offset
```

For example, the `OILRATSC` (Oil Rate at surface conditions) keyword has
`Dimensionality = "11|-13|"`: dimension 11 (Well Liquid Volume) divided by
dimension 13 (Well Rate Time). If the SR3 records `Output Unit = cm3` for dim
11 and `Output Unit = min` for dim 13, then `OILRATSC` values are stored in
`cm³/min`. Switch the file to SI Output and they'd be in `m³/day`.

## The `to_unit` argument

Every value-returning method accepts the same vocabulary:

| `to_unit`         | Effect on values            | Effect on the `Unit` label              |
|-------------------|-----------------------------|-----------------------------------------|
| `"output"` *(default)* | None (stored bytes) | `UnitsTable.Output Unit`                |
| `"internal"`      | per-token UCT conversion    | `UnitsTable.Internal Unit`              |
| `"psi"` / `"MPa"` / `"md"` / … | UCT conversion (single positive-dim keywords only) | the requested unit string |

The label always matches the values — they move together.

```python
from pysr3 import SR3Indexer, GridBuilder
from pysr3.data_mapper import DataMapper

with SR3Indexer("model.sr3") as sr3:
    # Well bottom-hole pressure: stored in kPa, requested in psi
    df = sr3.get_well_data(variable_names=["BHP"], to_unit="psi")

    # Spatial map: stored TEMP in F (this file uses *INUNIT FIELD), shown in K
    grid = GridBuilder(sr3).build("Cartesian")
    df_int = DataMapper(sr3).map_prop(grid, "TEMP", 0, to_unit="internal")

    # Inspect what's available
    print(sr3.get_unit("OILRATSC"))               # 'cm3/min'   (Output)
    print(sr3.get_unit("OILRATSC", "internal"))   # 'm3/day'    (Internal)
```

## Looking under the hood

```python
sr3.units                     # {dim_idx: {output_unit, internal_unit, dimensionality}}
sr3.unit_conversions          # {dim_idx: {unit_name: (gain, offset)}}
sr3.get_unit(keyword)          # the unit string for any policy
sr3.convert(keyword, values, to_unit)  # the conversion math, vectorized over arrays
```

The conversion table is provided by CMG; `pysr3` only reads and composes —
no external `pint`-style library is needed.

## Two quiet exceptions

1. **`MasterTimeTable` time offsets** are stored in **days** regardless of the
   file's Output Time unit (the column header literally says `"Offset in days"`).
   `pysr3.get_time_offset()` returns those values as-is. Rate denominators
   (`OILRATSC = Volume / WellRateTime`) follow the Output Unit choice.

2. **Temperature canonical = `C`** in `UnitConversionTable`, while
   `UnitsTable.Internal Unit` for Temperature says `K`. `pysr3.convert` chains
   `stored → C → K` automatically; you don't need to know about it unless you
   read UCT yourself.
