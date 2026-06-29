# pysr3

Third-party reader and visualizer for **CMG SR3** files.

The codebase follows a three-layer architecture (read → build geometry → map
properties), so callers depend only on a small public surface:

| Layer | Class | Responsibility |
|---|---|---|
| Access | `SR3Indexer` | Open HDF5, index metadata/time-series, hand out raw numpy arrays. |
| Geometry | `GridBuilder` | Convert SR3 grid arrays into a PyVista `UnstructuredGrid`. |
| Properties | `DataMapper` | Map SR3 property arrays onto grid cells / DataFrames. |

Grid construction is split into one strategy per family under
[`pysr3/grid/`](pysr3/grid) (`Cartesian`, `CornerPoint`, `Radial`) plus embedded
DFN surface builders, all sharing the reusable helpers in
`pysr3/grid/geometry.py`.

## Install

```bash
pip install -e .          # or: pip install -r requirements.txt
```

## Quick start

```python
from pysr3 import SR3Indexer, GridBuilder, DataMapper

with SR3Indexer("model.sr3") as ix:
    # grid_type is auto-detected from /SpatialProperties/<step>/GRID/IGNTGT[0]
    grid = GridBuilder(ix).build(grid_mode="mixed")
    df = DataMapper(ix).map_prop(grid, "PRES", time_steps=0)
    grid.save("grid.vtu")
```

Highlights:

- **Auto-detected grid type.** Omit `grid_type` and the builder picks
  `Cartesian` / `CornerPoint` / `Radial` from `IGNTGT[0]`. Pass it explicitly
  to override (a warning is logged on mismatch).
- **Unit conversion.** Every value-returning method accepts `to_unit=` —
  e.g. `mapper.map_prop(grid, "PRES", 0, to_unit="psi")` or
  `ix.get_well_data(["WELL 1"], ["BHP"], to_unit="internal")`. Powered by the
  file's own `/General/UnitConversionTable`; no external library required.
- **Pore-volume-weighted aggregation.** `agg_method="pore_volume_mean"`
  weights LGR child-to-parent rollup by `BLOCKPVOL` — the right average for
  fluid properties (pressure, saturations, STOIIP). The bulk-volume
  variant `agg_method="bulk_volume_mean"` (MODBVOL-weighted) is also supported.

`GridBuilder.build` accepts `grid_type` in `available_grid_types()`
(`"Cartesian"`, `"CornerPoint"`, `"Radial"`) when you need to override
auto-detection.

## Validation / examples

`tools/export_case_assets.py` rebuilds VTU + PNG assets for every registered
SR3 case; `tools/export_timeseries_assets.py` exports well/time-series CSVs. Run
the test suite with `pytest`.

Full documentation (architecture, concepts, tutorials) is published at
**<https://llpetro.github.io/pysr3/>** and lives in [`docs/`](docs) (builds with
`mkdocs`).

## License

Released under the [MIT License](LICENSE).

## Citation

If you use pysr3 in your work, please cite it:

```bibtex
@software{pysr3,
  title  = {{pysr3: a third-party reader, grid builder, and property mapper for CMG SR3 files}},
  author = {{LLPetro}},
  year   = {2026},
  url    = {https://github.com/LLPetro/pysr3}
}
```

A machine-readable [`CITATION.cff`](CITATION.cff) is also provided, so GitHub
shows a "Cite this repository" button.
