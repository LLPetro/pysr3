# Grid strategy internals

`GridBuilder` is a facade. The geometry lives in `pysr3/grid/`, organized so
each grid family is isolated and the shared math is reused.

## The strategy registry

`grid/base.py` defines an ABC and a registry:

```python
class GridStrategy(ABC):
    grid_type: str = ""
    def __init__(self, indexer): ...
    @abstractmethod
    def build(self, data, time_step, grid_mode, include_inactive) -> pv.UnstructuredGrid: ...
```

A `@register_strategy("Cartesian")` decorator records the class under its public
name. `GridBuilder.build()` resolves the strategy, fetches `get_grid_data` once,
calls `strategy.build(...)`, then merges coincident points:

```python
strategy = get_strategy(grid_type, self.indexer)
data = self.indexer.get_grid_data(time_step)
grid = strategy.build(data=data, time_step=time_step,
                      grid_mode=grid_mode, include_inactive=include_inactive)
# ... grid.clean(...) if merge_points
```

Strategies are pure transforms: they receive the already-read `data` dict and
never touch the file. Adding a family is therefore additive — see
[Contributing](contributing.md#adding-a-grid-type).

## Shared geometry helpers

`grid/geometry.py` holds the reusable, pure-NumPy building blocks. They take
plain arrays, so they unit-test in isolation (`test/test_grid_geometry.py`).

| Helper | Purpose |
|---|---|
| `infer_levels(icstpb, igntnc)` | LGR level per cell; raises on circular/invalid parents |
| `refined_parent_ids(icstpb, igntnc)` | parents replaced by LGR children |
| `grid_mode_keep_mask(mode, level, icstpb, igntnc)` | mixed/refined/levelN filter |
| `active_cell_mask(icstps, data)` | `ICSTPS > 0` **and** `IPSTAC != 0` |
| `parse_kdir(data, default)` | decode the `KDIR` attribute |
| `hexahedra_from_corners(corners)` | exploded-hex `(cells, types, points)` from 8 corner arrays |
| `polygon_cells(n, n_verts, type)` | VTK connectivity for consecutive-vertex polygons |
| `segment_ijk(igntid, jd, kd, nc, total)` | per-cell local I/J/K for all segments |
| `compute_parent_ijk(icstpb, level, i, j, k)` | parent I/J/K for refined cells |

`infer_levels` lives here precisely so `GridBuilder` and `DataMapper` share one
implementation. See the [API reference](../api/grid-geometry.md).

## Cartesian / VARI

Builds an **exploded hexahedron** grid: each cell becomes 8 explicit corners, so
variable block sizes and LGR refinement need no special casing; coincident
corners are merged afterward by the facade. `BLOCKDEPTH` (positive downward) is
mapped to Z-up (`Z = -depth`).

!!! warning "LGR origin assumption"
    For an LGR segment, child coordinates are anchored to the lower-left corner
    of the refined parents (`min` of parent `xmin`/`ymin`), then tiled by
    cumulative `BLOCKSIZE`. This assumes **one segment refines a single
    contiguous parent box**. Segments that group multiple disjoint parents are
    not handled. `test/test_basic_grid_types.py::test_lgr_children_tile_parent_footprint`
    pins the supported single-parent case.

## Radial

Reconstructs wedges from `BLOCKSIZE` (Δr, arc length, Δz) and `WELLRADIUS`:
`r` by cumulative Δr, `dθ = arc_length / r_center`, `θ` by cumulative `dθ`, and
Z by cumulative Δz with `KDIR` deciding the direction. Wide wedges are
**subdivided** so they render as smooth arcs (`MAX_ANGLE_DEG = 5°`), expanded
vectorially with `np.repeat`. The first ring (I=0) collapses all J columns, so
those duplicates are filtered out.

## Corner-point

Detects the encoding and produces `(nodes, blocks)`:

1. `NODES` + `BLOCKS` — used directly.
2. `XCORNCRCN/YCORNCRCN/ZCORNCRCN` — `_crcn_to_nodes_blocks` builds structured
   connectivity (vectorized per segment).
3. `COORD` + `ZCORN` — `_coord_zcorn_to_nodes_blocks` interpolates XY along each
   pillar from the corner Z (vectorized) and negates Z for display.
4. None of the above but Cartesian arrays present — **falls back** to
   `CartesianStrategy` (e.g. some `DFN_REFINE` convert-to-corner cases).

Block indices are shifted from 1-based to 0-based when no node 0 is referenced.

## DFN

`grid/dfn.py` builds QUAD surfaces (via `polygon_cells`), independent of the
matrix hierarchy:

- `build_dfn_units` — original DFU quads (`DFUCO*`), with `DFUAPT`/`DFUPERM` when
  present.
- `build_dfn_segments` — embedded segment quads (`SGCOR*`), filtered by `IPSTPS`
  and `IPSTAC`, carrying `PropGlobalID` and host back-references
  (`HostGlobalCellID`, `Host I/J/K` via `segment_ijk`).

Both return an empty `UnstructuredGrid` when the file has no DFN arrays.
