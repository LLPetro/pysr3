# Naming & glossary

This page is the single source of truth for the vocabulary used in pysr3 — in
identifiers, parameter names, dict keys, docstrings, log messages, and prose.

Drift hurts readers fast: the same concept under three names sends grep on
wild-goose chases and forces every reviewer to keep a mental translation
table. When in doubt, prefer the canonical name on this page over a synonym,
even when the synonym is shorter or "reads nicer."

## Time-step terminology

CMG SR3 files contain three related-but-distinct flavors of "step":

| Concept | Canonical singular | Canonical plural | Notes |
|---|---|---|---|
| Integer step index (one value) | `time_step` | — | Used as a parameter on every value-returning method. Never `ts`, `timestep` (one word), `step_idx`. |
| Float offset since simulation start (days) | `time_offset` (`get_time_offset`) | — | The numeric column in DataFrames is labeled `Time`. |
| Date string at a step | `step_date` (`get_step_date`) | — | DataFrame column stays `Date`. |
| Every step at which `/SpatialProperties/<step>` exists | — | `spatial_time_steps` | Method: `get_spatial_time_steps()`. |
| Subset of those at which `/GRID` is written | `grid_time_step` (`get_nearest_grid_time_step`) | `grid_time_steps` (`get_grid_time_steps`) | Geometry is usually only written at a handful of steps. |
| Time axis of one TimeSeries entity (well/group/sector/...) | — | `time_steps` (parameter on `get_timeseries_data` / `get_well_data`) | Stored as `info['time_steps']` on `get_timeseries_info()`. |
| Zero-padded step **string** (`"000000"`, used to construct HDF5 paths) | `step_key` | `spatial_step_keys` | Internal-only; not exposed to user code. |
| DataFrame column for the SR3 step int | `TimeIndex` | — | Already stable; do not rename. |

**Conventions in code:**
- Parameter and local variable: `time_step` (singular int), `time_steps` (list of ints).
- Loop variable for level descent in aggregation: `level_idx` (not `lvl`).
- Per-call snapped grid step: `grid_time_step`.
- Float snapping intermediate: `best_step` (not `best_ts`).

## Property and variable identifiers

CMG calls the columns of `/General/NameRecordTable` "keywords." pysr3
distinguishes two flavors:

| Concept | Canonical name | Where it appears |
|---|---|---|
| Spatial property keyword (`PRES`, `SO`, `MODBVOL`, `BLOCKPVOL`, …) | `keyword` | `get_property_data(keyword, ...)`, `get_property_info(keyword, ...)`, `map_prop(keywords=...)`, `get_unit(keyword, ...)`, `convert(keyword, ...)`. DataFrame column: `Keyword`. |
| TimeSeries variable keyword (`BHP`, `OILRATSC`, …) | `variable` | `get_timeseries_data(variables=[...])`, `get_well_data(variables=[...])`. DataFrame column: `Variable`. |
| TimeSeries origin (well name, group name, …) | `origin` (abstract) / `well` (concrete) | `get_timeseries_data(origins=[...])`, `get_well_data(wells=[...])`. Columns: `Origin` / `Well`. |

Never use `name`, `prop_name`, `var_name`, or `kw` as identifier names for
these. They are too generic and clash with Python builtins or local context.

## Reservoir-cell terminology

| Concept | Canonical in pysr3 prose | CMG / SR3 convention |
|---|---|---|
| Discretised reservoir volume | **cell** (`n_cells`, `GlobalCellID`, `active_cell_mask`, `total_cells`) | "block" (`BLOCKSIZE`, `BLOCKDEPTH`, `BLOCKPVOL`, `MODBVOL` = "Modified Block Volume") |

**Rule:** in pysr3 docstrings, comments, and prose, say **cell**. PyVista and
VTK use "cell" too, so this matches the downstream representation.
**Exception:** when literally quoting a CMG keyword or NRT Long Name, preserve
its original wording (e.g. `MODBVOL` is called "Modified Block Volume", not
"Modified Cell Volume" — that's CMG's name and shouldn't be rewritten).

A glossary entry in `concepts/volumes.md` and `concepts/dfn-vs-lgr.md` makes
this equivalence explicit.

## Sub-grid vs DFN segment

The word "segment" had three meanings until a recent cleanup:

1. **Matrix sub-grid** — one entry in `IGNTGT` / `IGNTID/JD/KD` (the top-level
   matrix plus every LGR refinement). Canonical name: **subgrid**.
   Identifiers: `subgrid_ijk()`, `subgrid_idx`, `n_subgrids`.
2. **DFN planar quad** — one fracture face in a discrete fracture network.
   Canonical name: **segment** (kept). Identifiers: `build_dfn_segments`,
   `DFNSegmentID`.
3. CornerPoint connectivity block — referred to inline as "connectivity
   block"; no dedicated identifier needed.

Outside of `grid/dfn.py`, "segment" should never appear as a Python
identifier; "subgrid" is the safe pick.

## LGR-related identifiers

| Concept | Canonical |
|---|---|
| LGR refinement depth (per-cell `int`) | `level` (array), `max_level` (scalar), `level_idx` (loop var) |
| Display-mode strings (`grid_mode=`) | `"mixed"`, `"refined"`, `"level0"`, `"level1"`, … |
| 0-based CS indices of cells that LGR children replaced | `refined_parents` (never `rp`) |
| Boolean keep-mask helper for `grid_mode` | `grid_mode_keep_mask(...)` (not `display_mode_keep_mask`) |
| `keep_refined_parents=True` flag on `GridBuilder.build` | unchanged |
| Per-cell child sub-grid pointer (ICSTCG) | `icstcg` parameter; readable noun "child sub-grid" |

## Property-slot identifiers

| Concept | Canonical |
|---|---|
| `ICSTPS - 1` (0-based index into property arrays) | `prop_slots` (plural), `prop_slot` (singular) |
| In-bounds subset of the above | `valid_prop_slots` |
| Public cell-data array name on built grids | `PropGlobalID` (unchanged — already stable on disk) |

## Unit subsystem

| Concept | Canonical |
|---|---|
| `to_unit=` parameter on every value-returning method | `to_unit` |
| Per-dim default-output unit (`UnitsTable.Output Unit`) | `output_unit` (dict key on `name_records[k]`, `units[i]`) |
| Per-dim CMG internal unit | `internal_unit` |
| DataFrame column label | `Unit` |
| `agg_method` weighted variants | `'bulk_volume_mean'` (MODBVOL-weighted) and `'pore_volume_mean'` (BLOCKPVOL-weighted) |

## Public-method prefix convention

`get_X` is the dominant pattern on `SR3Indexer`. Apply it to every
**value-returning accessor**. Reserve verb-first names for **actions** that
perform work (build, convert, detect, register, close).

| Style | Examples |
|---|---|
| `get_X` (accessor) | `get_grid_data`, `get_grid_array`, `get_property_data`, `get_property_info`, `get_available_properties`, `get_grid_time_steps`, `get_spatial_time_steps`, `get_nearest_grid_time_step`, `get_time_offset`, `get_step_date`, `get_unit`, `get_well_data`, `get_timeseries_data`, `get_timeseries_info`, `get_timeseries_entities` |
| Verb-first (action) | `build`, `build_dfn_segments`, `build_dfn_units`, `convert`, `detect_grid_type`, `register_strategy`, `close` |
| Module-level pure function | `available_grid_types()` (no `get_` because it's not a method on an indexer/mapper/builder) |

## Prose conventions

| Concept | Canonical in `.md` | Avoid |
|---|---|---|
| Time-step (noun) | "time step" | one-word "timestep", "Time Step" |
| Time-step (adjective) | "time-step" (hyphenated) | unhyphenated "time step" used as a modifier |
| Time-series (noun) | "time series" | "time-series" (hyphenated), "timeseries" (one word) |
| Time-series (adjective) | "time-series" (hyphenated) | unhyphenated "time series" used as a modifier |
| HDF5 group name | `` `TimeSeries` `` (literal `/TimeSeries`) | "Time Series" rendered in monospace |
| File-path component | `timeseries` (one word, lowercase) — keeps existing on-disk paths | renaming the directory |
| Grid families in headings & tables | `Cartesian`, `CornerPoint`, `Radial` | "Corner-point", "corner-point", "RADIAL" |
| Grid families in narrative prose | "corner-point grid", "the radial grid" | inconsistent capitalisation |
| LGR | `LGR` (all caps); spell out as "local grid refinement" on first use per page | "lgr" |
| DFN | `DFN` (all caps); spell out as "discrete fracture network" on first use per page | "dfn" |

For Chinese (`*.zh.md`) translations, keep the same English technical
identifiers; translate only natural-language prose. The Chinese term for
"time step" is 时间步; for "time series" 时间序列.

## When unsure

- If the canonical name on this page doesn't fit a new concept, **extend
  this page** rather than introducing a one-off variant.
- If renaming an existing identifier looks valuable, raise it in a PR first —
  consistency across files is more important than any single name being
  "best."
- The names here intentionally favor explicit over short. `time_step` over
  `ts` because `ts` collides with too many other meanings (TypeScript,
  tablespoon, time series, …) and is harder to grep for.
