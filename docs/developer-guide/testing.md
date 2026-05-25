# Testing & validation

pysr3 is validated at three levels: fast unit tests, integration against **real
STARS 2025.20 SR3 files**, and a golden behavior harness for refactors.

```mermaid
flowchart LR
    A[DAT] --> B[STARS 2025.20]
    B --> C[SR3]
    C --> D[SR3Indexer]
    D --> E[GridBuilder]
    E --> F[DataMapper]
```

## Running the suite

```bash
pip install -e ".[dev]"
pytest                       # 28 tests
```

The suite (`test/`) combines:

- **Unit tests** with mock indexers and tiny synthetic grids
  (`test_basic_grid_types.py`).
- **Geometry-helper tests** for the reusable functions
  (`test_grid_geometry.py`) — including the `infer_levels` deadlock guard.
- **`DataMapper` aggregation tests** for `mean`/`sum`/`min`/`max`
  (`test_data_mapper.py`).
- **Real-SR3 integration tests** asserting exact cell counts, levels, and
  property finiteness for LGR, DFN, and convert-to-corner cases.

## Real-SR3 fixtures

Eleven cases live under `test/<case>/` (DAT + SR3 + logs), registered in
`tools/export_case_assets.py`:

| Case | grid_type | Notes |
|---|---|---|
| `cartesian` | Cartesian | `*GRID *CART` |
| `vari` | Cartesian | `*GRID *VARI` |
| `radial` | Radial | `*GRID *RADIAL` |
| `lgr` | Cartesian | single-level `*REFINE` |
| `lgr_nested` | Cartesian | two-level `*REFINE` (levels 0/1/2) |
| `corner` | CornerPoint | `XCORNCRCN/...` compressed corners |
| `corner_coord` | CornerPoint | `COORD/ZCORN` pillar grid |
| `tutorial_hm` | CornerPoint | larger, realistic corner model |
| `convert_to_corner` | CornerPoint | `*CONVERT-TO-CORNER-POINT` + DFN |
| `dfn_multi` | CornerPoint | 4 DFUs |
| `dfn_refine` | CornerPoint | `*DFN_REFINE`; falls back to Cartesian arrays |

## The verification pipeline

`tools/export_case_assets.py` drives every registered case end to end — build,
map, and asset export — writing per-case `artifacts/` and a top-level
`test/case_assets_summary.json`:

```bash
python tools/export_case_assets.py                       # all cases
python tools/export_case_assets.py --case convert_to_corner
python tools/export_timeseries_assets.py                 # well/time-series CSVs
```

Reference results (cells / points):

| Case | Cells | Points |
|---|---:|---:|
| cartesian | 52 | 110 |
| vari | 110 | 768 |
| radial | 3752 | 6125 |
| lgr | 15 | 48 |
| lgr_nested | 36 | 98 |
| corner | 75 | 192 |
| corner_coord | 351 | 588 |
| tutorial_hm | 2616 | 3259 |
| convert_to_corner | 294 | 704 |
| dfn_multi | 294 | 704 |
| dfn_refine | 402 | 1012 |

## Golden behavior harness

For behavior-preserving refactors, fingerprint each case **before** the change
and diff afterward. The fingerprint captures `n_cells`, `n_points`, bounds, the
full cell-data arrays, and mapped `PRES` for all grid modes plus DFN, comparing
floats with `np.allclose` and integers with `array_equal`.

This is how the grid-strategy refactor and the `core → pysr3` rename were proven
to produce bit-identical output across all 11 cases.

!!! tip "Rule of thumb"
    Touching grid construction or property mapping? Validate against the real
    fixtures, not only the mock unit tests — the riskiest code (LGR origin,
    COORD/ZCORN, radial subdivision) is only meaningfully exercised by real files.
