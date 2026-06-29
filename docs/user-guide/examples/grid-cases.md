# Grid cases

Copy-paste snippets for every supported grid family, using the real STARS
SR3 files bundled under `test/`.

## Cartesian

```python
from sr3kit import SR3Indexer, GridBuilder

with SR3Indexer("test/cartesian/cartesian.sr3") as sr3:
    grid = GridBuilder(sr3).build("Cartesian")

print(grid.n_cells)
```

## VARI

`VARI` is built with the `Cartesian` strategy.

```python
with SR3Indexer("test/vari/vari.sr3") as sr3:
    grid = GridBuilder(sr3).build("Cartesian")
```

## Radial

```python
with SR3Indexer("test/radial/radial.sr3") as sr3:
    grid = GridBuilder(sr3).build("Radial")
```

## LGR

```python
with SR3Indexer("test/lgr/lgr.sr3") as sr3:
    builder = GridBuilder(sr3)
    mixed   = builder.build("Cartesian", grid_mode="mixed")
    refined = builder.build("Cartesian", grid_mode="refined")
    level0  = builder.build("Cartesian", grid_mode="level0")
```

Nested (multi-level) LGR:

```python
with SR3Indexer("test/lgr_nested/lgr_nested.sr3", eager_list_steps=None) as sr3:
    builder = GridBuilder(sr3)
    mixed  = builder.build("Cartesian", grid_mode="mixed")
    level2 = builder.build("Cartesian", grid_mode="level2")
```

## CornerPoint

```python
with SR3Indexer("test/corner_coord/corner_coord.sr3") as sr3:
    grid = GridBuilder(sr3).build("CornerPoint")
```

A larger, more realistic corner-point model:

```python
with SR3Indexer("test/50the_datafile/tutorial_hm.sr3") as sr3:
    grid = GridBuilder(sr3).build("CornerPoint")
```

## Convert-to-corner + DFN

```python
with SR3Indexer("test/convert_to_corner/convert_to_corner.sr3", eager_list_steps=None) as sr3:
    builder = GridBuilder(sr3)
    matrix       = builder.build("CornerPoint")
    dfn_segments = builder.build_dfn_segments()
    dfn_units    = builder.build_dfn_units()
```

Multiple DFUs and `DFN_REFINE`:

```python
with SR3Indexer("test/dfn_multi/dfn_multi.sr3", eager_list_steps=None) as sr3:
    builder = GridBuilder(sr3)
    dfn_segments = builder.build_dfn_segments()
    dfn_units    = builder.build_dfn_units()

with SR3Indexer("test/dfn_refine/dfn_refine.sr3", eager_list_steps=None) as sr3:
    builder = GridBuilder(sr3)
    matrix         = builder.build("CornerPoint")           # falls back to Cartesian arrays
    active_segs    = builder.build_dfn_segments()
    all_segs       = builder.build_dfn_segments(include_inactive=True)
```

## Map properties

```python
from sr3kit import SR3Indexer, GridBuilder, DataMapper

with SR3Indexer("test/cartesian/cartesian.sr3", eager_list_steps=None) as sr3:
    grid = GridBuilder(sr3).build("Cartesian")
    df = DataMapper(sr3).map_prop(grid, ["PRES", "SO"], [0])

print(df.columns)
print(df.head())
```

## Export assets

```bash
python tools/export_case_assets.py
python tools/export_case_assets.py --case tutorial_hm --scale-z 10
```

Each case produces (DFN files only when present):

```text
artifacts/grid.vtu
artifacts/grid_display.vtu
artifacts/dfn_segments.vtu
artifacts/dfn_units.vtu
artifacts/overview.png
artifacts/slice.png
artifacts/summary.json
```
