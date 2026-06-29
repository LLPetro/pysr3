# Grid visualization

## Goal

Export a VTU mesh, an overview render, and a center slice for a case — and
exaggerate Z for a thin reservoir model.

## Export assets

```bash
python tools/export_case_assets.py --case tutorial_hm --scale-z 10
```

Output directory:

```text
test/50the_datafile/artifacts/
  grid.vtu
  grid_display.vtu
  overview.png
  slice.png
  summary.json
```

## Overview

![Tutorial HM overview](../../assets/images/tutorial_hm_overview.png)

## Center slice

![Tutorial HM slice](../../assets/images/tutorial_hm_slice.png)

## How it works

`grid.vtu` holds the core build coordinates; `grid_display.vtu` is the display
copy, which may flip Z and apply scale exaggeration. Thin reservoirs usually
need Z exaggeration to be readable — see
[Coordinate system & display scale](../concepts/coordinate-system.md).

To do the same thing programmatically with PyVista:

```python
from sr3kit import SR3Indexer, GridBuilder

with SR3Indexer("test/50the_datafile/tutorial_hm.sr3", eager_list_steps=None) as sr3:
    grid = GridBuilder(sr3).build(grid_type="CornerPoint")

grid.save("grid.vtu")
grid.plot(show_edges=True)   # set pyvista.OFF_SCREEN = True on a headless host
```
