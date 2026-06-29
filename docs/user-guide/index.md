# User Guide

This guide is for **users of sr3kit** — engineers and analysts who want to read
CMG SR3 results, build grids, map properties, and pull well/time-series data.

If you want to understand or extend the internals, see the
[Developer Guide](../developer-guide/index.md).

## Reading order

<div class="grid cards" markdown>

-   :material-download: **[Installation](installation.md)**

    Install sr3kit and its dependencies, including notes for headless rendering.

-   :material-rocket-launch: **[Quickstart](quickstart.md)**

    The full read → build → map flow in one short script.

-   :material-grid: **[Building grids](grid-building.md)**

    Grid types, LGR display modes, DFN surfaces, and the cell-data arrays you get.

-   :material-book-open-variant: **[Concepts](concepts/grid-types.md)**

    Background on grid types, coordinates, DFN vs LGR, and time series.

-   :material-school: **[Tutorials](tutorials/index.md)**

    Goal-oriented, illustrated walkthroughs against real STARS SR3 files.

-   :material-code-braces: **[Examples](examples/grid-cases.md)**

    Copy-paste snippets for every supported case.

</div>

## The three layers

sr3kit is organized as three small, composable layers. Most workflows use all
three in sequence:

```python
from sr3kit import SR3Indexer, GridBuilder, DataMapper
```

| Layer | Class | You use it to… |
|---|---|---|
| Access | `SR3Indexer` | open the file and ask what's inside (times, properties, wells). |
| Geometry | `GridBuilder` | turn a grid time step into a PyVista `UnstructuredGrid`. |
| Properties | `DataMapper` | attach `PRES`/`SO`/… values to the grid's cells. |

See the [API Reference](../api/index.md) for the full signatures.
