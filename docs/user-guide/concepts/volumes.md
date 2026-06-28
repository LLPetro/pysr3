# Volumes & weighted aggregation

When `DataMapper.map_prop(..., aggregate=True)` rolls LGR child cells up into
their parent, **how** it averages matters. A simple `'mean'` weights every
child equally — almost never right when children have different volumes or
different pore content. CMG SR3 exposes two per-cell volume arrays for exactly
this purpose, and pysr3 surfaces them via two `agg_method` values.

## The two volume arrays

| Array | NRT Long Name | What it represents | Storage path |
|---|---|---|---|
| `MODBVOL` | "Modified Block Volume" | **Bulk volume** of each cell (full block × volume modifier; independent of fluids/porosity). | `/SpatialProperties/<step>/MODBVOL` |
| `BLOCKPVOL` | "Block pore volume" | **Pore volume** = bulk × porosity × NTG. The rock volume that actually holds fluids. | `/SpatialProperties/<step>/GRID/BLOCKPVOL` |

Both are static — written only at the grid time step — and indexed per cell
via `PropGlobalID = ICSTPS - 1`.

A sanity ratio on the multibranch fixture: `BLOCKPVOL / MODBVOL ≈ 0.34–0.37`,
i.e. effective porosity. Same shape, related by porosity × NTG.

## Which weight should I use?

| `agg_method` | Source | Right for… |
|---|---|---|
| `'mean'` | (none) | Quick look only; assumes uniform child cells. With LGR or graded grids this is usually misleading. |
| `'volume_mean'` | `MODBVOL` | Geometric/intensive quantities (temperature, depth-weighted scalars). Bulk-volume average. |
| `'pore_volume_mean'` | `BLOCKPVOL` | **Fluid properties** — pressure within a phase, saturations, mole fractions, STOIIP-style aggregation. The rock volume holding the fluid is the natural weight. |

## Worked example

```python
from pysr3 import SR3Indexer, GridBuilder
from pysr3.data_mapper import DataMapper

with SR3Indexer("test/lgr_nested/lgr_nested.sr3") as sr3:
    grid = GridBuilder(sr3).build(grid_mode="level0")     # parents kept by default
    mapper = DataMapper(sr3)

    p_pore = mapper.map_prop(grid, "PRES", 0, aggregate=True, agg_method="pore_volume_mean")
    p_bulk = mapper.map_prop(grid, "PRES", 0, aggregate=True, agg_method="volume_mean")
    p_arith = mapper.map_prop(grid, "PRES", 0, aggregate=True, agg_method="mean")
```

For fluid-pressure aggregation, prefer `'pore_volume_mean'`.

## Reading the volume arrays directly

Both are reachable through the same `get_property_data` API:

```python
sr3.get_property_data("MODBVOL",   0)   # bulk volume per active cell
sr3.get_property_data("BLOCKPVOL", 0)   # pore volume per active cell
sr3.get_grid_array("BLOCKPVOL",   0)    # equivalent, no /GRID/ fallback magic
```

`pysr3` looks under `/SpatialProperties/<step>/<name>` first, then falls back
to `/SpatialProperties/<step>/GRID/<name>` — so the same call works for both.

## Edge cases

- **Cells with `BLOCKPVOL == 0`** (e.g. null-porosity layers, fracture-only
  cells in DFN files): treated as "no weight" so they don't dominate the
  parent. The aggregator filters `w > 0` and skips them.
- **All children have zero pore volume**: the parent stays `NaN` — pysr3 does
  not silently substitute bulk volume.
- **Files without `BLOCKPVOL`** (very old SR3 versions; none of pysr3's 12
  bundled fixtures): `agg_method='pore_volume_mean'` logs a warning naming the
  missing keyword and degrades to `'mean'` — same UX as the existing MODBVOL
  fallback.
