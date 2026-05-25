---
hide:
  - navigation
  - toc
---

<section class="hero" markdown>

# pysr3

A third-party Python toolkit for reading **CMG SR3** result files: index the
HDF5 container, build PyVista grids from any SR3 grid family, and map spatial
and time-series results onto cells and DataFrames. STARS first.

<div class="hero-actions" markdown>
[Get started](user-guide/quickstart.md)
[User Guide](user-guide/index.md){ .secondary }
[API Reference](api/index.md){ .secondary }
</div>

</section>

## Why pysr3

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
### :material-file-tree: SR3 reading
A single source of truth (`SR3Indexer`) parses metadata, components, units,
time steps, spatial properties, and time series — handing out plain NumPy
arrays, never raw HDF5 handles.
</div>

<div class="feature-card" markdown>
### :material-grid: Grid building
One strategy per family — Cartesian/VARI, Radial, and Corner-point — plus LGR
levels and embedded DFN surfaces, all producing a PyVista `UnstructuredGrid`.
</div>

<div class="feature-card" markdown>
### :material-palette: Property mapping
Map `PRES`, `SO`, `SG`, `SW`, `TEMP`, … onto grid cells via stable cell IDs,
with optional bottom-up LGR aggregation, returned as tidy DataFrames.
</div>

<div class="feature-card" markdown>
### :material-chart-line: Wells & time series
Read `WELLS`, `LAYERS`, `GROUPS`, `SECTORS`, and `SPECIAL HISTORY` as long-form
DataFrames, validated against real STARS 2025.20 output.
</div>

</div>

## Quickstart

```python
from pysr3 import SR3Indexer, GridBuilder, DataMapper

with SR3Indexer("model.sr3") as sr3:
    grid = GridBuilder(sr3).build(grid_type="CornerPoint", grid_mode="mixed")
    pres = DataMapper(sr3).map_prop(grid, "PRES", time_step=0)
    grid.save("grid.vtu")
```

[Read the full quickstart →](user-guide/quickstart.md){ .md-button }

## Explore

<div class="gallery-grid" markdown>

<div class="gallery-card" markdown>
![Cartesian overview](assets/images/cartesian_overview.png)
<div markdown>
### [First SR3 case](user-guide/tutorials/first-sr3-case.md)
Open a file, build a grid, map `PRES`.
</div>
</div>

<div class="gallery-card" markdown>
![Tutorial HM overview](assets/images/tutorial_hm_overview.png)
<div markdown>
### [Grid visualization](user-guide/tutorials/grid-visualization.md)
Export VTU, overview/slice renders, vertical exaggeration.
</div>
</div>

<div class="gallery-card" markdown>
![Convert to corner overview](assets/images/convert_to_corner_overview.png)
<div markdown>
### [Corner-point & DFN](user-guide/tutorials/corner-grid.md)
Handle `CornerPoint`, `CONVERT-TO-CORNER-POINT`, and DFN surfaces.
</div>
</div>

<div class="gallery-card" markdown>
![HM model pressure](assets/images/guide_3d.png)
<div markdown>
### [In-depth: HM model](user-guide/tutorials/inspect-hm-model.md)
3D scenes, isosurfaces, filters, slices, contours, and time series.
</div>
</div>

</div>

## Where to go next

- **[User Guide](user-guide/index.md)** — install, build grids, map properties, read wells.
- **[Developer Guide](developer-guide/index.md)** — architecture, data model, and internals.
- **[API Reference](api/index.md)** — auto-generated from the source.
