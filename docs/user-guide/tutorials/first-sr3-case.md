# First SR3 case

## Goal

Read a STARS SR3 file, build a grid, and map pressure (`PRES`) onto its cells.

## Input

```text
test/cartesian/cartesian.sr3
```

## Code

```python
from pysr3 import SR3Indexer, GridBuilder, DataMapper

with SR3Indexer("test/cartesian/cartesian.sr3", eager_list_steps=None) as sr3:
    grid = GridBuilder(sr3).build(
        grid_type="Cartesian",
        grid_mode="mixed",
        time_step=0,
    )

    df = DataMapper(sr3).map_prop(grid=grid, keywords="PRES", time_steps=[0])

print(grid.n_cells)
print(df.head())
```

## Result

![Cartesian overview](../../assets/images/cartesian_overview.png)

## How it works

- `SR3Indexer` opens the file and indexes its contents.
- `GridBuilder` converts the grid arrays into a PyVista `UnstructuredGrid`,
  stamping `PropGlobalID` and `GlobalCellID` onto each cell.
- `DataMapper` reads the `PRES` array and uses `PropGlobalID` to place each value
  on the right cell, returning a labelled DataFrame.

Next: [build display assets](grid-visualization.md) or learn the
[read → build → map flow](../quickstart.md) in full.
