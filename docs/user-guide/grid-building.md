# Building grids

`GridBuilder` turns the raw arrays of one SR3 grid time step into a PyVista
`UnstructuredGrid`, stamping each cell with the IDs that `DataMapper` later uses
to attach property values.

```python
from pysr3 import SR3Indexer, GridBuilder

with SR3Indexer("test/lgr_nested/lgr_nested.sr3", eager_list_steps=None) as sr3:
    grid = GridBuilder(sr3).build(grid_mode="mixed")  # grid_type auto-detected from IGNTGT
```

## `build()` parameters

| Parameter | Default | Meaning |
|---|---|---|
| `grid_type` | `None` (auto-detect) | `"Cartesian"`, `"CornerPoint"`, or `"Radial"`. When `None`, the type is read from the file's `IGNTGT[0]` (`1=Cartesian`, `2=Radial`, `12=CornerPoint`). Pass explicitly to override; a warning is logged if the override contradicts the file. |
| `grid_mode` | `"mixed"` | LGR display mode (see below). |
| `include_inactive` | `False` | Keep cells with no property slot (`ICSTPS<=0`) or flagged inactive by `IPSTAC`. |
| `keep_refined_parents` | `True` | Keep LGR refined parents in the grid even when `include_inactive=False`. They appear "inactive" only because their children replace them, and are needed as landing sites for `DataMapper.map_prop(aggregate=True)`. Set `False` for the legacy behavior (drops them; aggregation becomes a silent no-op on level-N grids). |
| `time_step` | `0` | Which grid time step to read geometry from. |
| `merge_points` | `True` | Merge coincident corners after building (smaller, faster meshes). |
| `merge_tolerance` | `1e-10` | Distance below which two points are considered identical. |

!!! note "Geometry vs. results time steps"
    Geometry is usually written only at a few steps. `build(time_step=t)` reads
    the GRID definition at `t`; `DataMapper` independently resolves the nearest
    grid step when mapping a property at any results step.

## LGR display modes

Local grid refinement (`*REFINE`) produces a parent cell and its child cells in
the same file. `grid_mode` controls which cells appear:

=== "mixed (default)"

    Unrefined level-0 cells **and** all LGR leaf cells. Parents that were fully
    replaced by children are dropped, so nothing is drawn twice. This is the
    right choice for visualization.

=== "refined"

    Only refined cells (`Level > 0`).

=== "levelN"

    Only cells at a specific level: `"level0"`, `"level1"`, `"level2"`, …

```python
builder = GridBuilder(sr3)
mixed    = builder.build("Cartesian", grid_mode="mixed")
refined  = builder.build("Cartesian", grid_mode="refined")
level0   = builder.build("Cartesian", grid_mode="level0")
```

See [Grid types](concepts/grid-types.md) and [DFN vs LGR](concepts/dfn-vs-lgr.md)
for the underlying model.

## Cell-data arrays

Every built matrix grid carries these per-cell arrays:

| Array | Type | Meaning |
|---|---|---|
| `PropGlobalID` | int32 | `ICSTPS - 1`; index into a property array. `-1` ⇒ inactive. |
| `GlobalCellID` | int | 0-based linear cell index within the SR3 file. |
| `Level` | int16 | LGR level (0 = base grid). |
| `I`, `J`, `K` | int32 | Local structured indices within the cell's segment. |
| `ParentI/J/K` | int32 | Parent cell's I/J/K for refined cells; `-1` at level 0. |

`PropGlobalID` and `GlobalCellID` are the two keys that make property mapping
work — see [Data model & types](../developer-guide/data-model.md) for details.

## Embedded DFN surfaces

A discrete fracture network is **not** an LGR. It is stored separately and built
with dedicated methods that return 2D quad surfaces:

```python
builder = GridBuilder(sr3)
matrix       = builder.build("CornerPoint")     # the matrix grid
dfn_units    = builder.build_dfn_units()        # original DFU quads
dfn_segments = builder.build_dfn_segments()     # embedded segment quads
```

`build_dfn_segments()` stamps `PropGlobalID` (so you can map `PRES`/`SO`/… onto
fracture segments) plus `HostGlobalCellID` and `Host I/J/K` linking each segment
to its host matrix cell. Both methods return an empty grid when the file has no
DFN. See [DFN vs LGR](concepts/dfn-vs-lgr.md).

## Mapping properties

Once you have a grid, attach results with `DataMapper`:

```python
from pysr3 import DataMapper

df = DataMapper(sr3).map_prop(grid, keywords=["PRES", "SO"], time_steps=[0])
```

For grids that contain parent cells (e.g. `grid_mode="level0"`), enable
bottom-up aggregation so a parent shows the mean/sum/min/max of its children:

```python
agg = DataMapper(sr3).map_prop(level0, "PRES", 0, aggregate=True, agg_method="mean")
```

The result is a DataFrame with a 6-level column index
`(Keyword, LongName, Unit, Time, TimeIndex, TimeUnit)`; see
[`DataMapper.map_prop`](../api/data-mapper.md).
