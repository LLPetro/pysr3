# Quickstart

This page walks through the minimal **read → build → map** flow that most
workflows are built on.

## The whole flow

```python
from sr3kit import SR3Indexer, GridBuilder, DataMapper

sr3_path = "test/cartesian/cartesian.sr3"

with SR3Indexer(sr3_path, eager_list_steps=None) as sr3:
    # 1. Build a PyVista grid from the first grid time step.
    grid = GridBuilder(sr3).build(
        grid_type="Cartesian",
        grid_mode="mixed",
        time_step=0,
    )

    # 2. Map pressure onto the grid cells, for every time step that has it.
    pres = DataMapper(sr3).map_prop(
        grid=grid,
        keywords="PRES",
        time_steps=sr3.get_spatial_time_steps(),
    )

print(grid.n_cells)   # number of cells in the mesh
print(pres.head())    # labelled DataFrame, one column per (property, time)
```

## Step by step

1. **Open** the SR3 file with `SR3Indexer`. Always use it as a context manager
   (`with …`) so the HDF5 handle is closed for you.
2. **Build** a mesh with `GridBuilder` by passing the [grid type](#choosing-a-grid-type).
3. **Map** SR3 spatial properties onto the mesh cells with `DataMapper`.

!!! info "`eager_list_steps`"
    `SR3Indexer(path, eager_list_steps=None)` indexes the property list for every
    time step. The default (`0`) only indexes the first step, which is faster
    for large files; properties for other steps are then fetched on demand.

## Choosing a grid type { #choosing-a-grid-type }

`GridBuilder.build(grid_type=...)` currently supports:

| `grid_type` | CMG grid keyword |
|---|---|
| `"Cartesian"` | `*GRID *CART`, `*GRID *VARI`, and regular LGR |
| `"Radial"` | `*GRID *RADIAL` |
| `"CornerPoint"` | `*GRID *CORNER` (and `*CONVERT-TO-CORNER-POINT`) |

The list is also available at runtime via `sr3kit.available_grid_types()`.
See [Grid types](concepts/grid-types.md) for which SR3 arrays each one reads.

## Common `grid_mode` values

For models with local grid refinement (`*REFINE`):

| `grid_mode` | Shows |
|---|---|
| `"mixed"` (default) | unrefined level-0 cells **plus** all LGR leaf cells |
| `"refined"` | only refined cells (level > 0) |
| `"level0"`, `"level1"`, … | only cells at the given level |

See [Building grids](grid-building.md) for the complete reference.

## Save and visualize

A built grid is a standard PyVista mesh, so you can save it or plot it directly:

```python
grid.save("grid.vtu")                  # open in ParaView
grid.plot(scalars=None, show_edges=True)   # interactive window
```

To regenerate the VTU + PNG assets for every bundled case:

```bash
python tools/export_case_assets.py
python tools/export_case_assets.py --case tutorial_hm   # a single case
```

Each case writes to its own `artifacts/` directory. See
[Grid visualization](tutorials/grid-visualization.md) for display options.
