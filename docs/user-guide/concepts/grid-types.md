# Grid types

pysr3 targets CMG **STARS** first. The base `*GRID` types in the manual are
`*CART`, `*VARI`, `*RADIAL`, and `*CORNER`. `*REFINE` is local grid refinement
(LGR) — a modifier, not a base type.

| CMG keyword | `grid_type` | Key SR3 arrays |
|---|---|---|
| `*GRID *CART` | `Cartesian` | `IGNTID/JD/KD`, `IGNTNC`, `BLOCKSIZE`, `BLOCKDEPTH`, `ICSTPB`, `ICSTPS` |
| `*GRID *VARI` | `Cartesian` | same as CART (variable sizes via `BLOCKSIZE`/`BLOCKDEPTH`) |
| `*GRID *RADIAL` | `Radial` | `BLOCKSIZE`, `WELLRADIUS`, `IGNTID/JD/KD`, `ICSTPB`, `ICSTPS` |
| `*GRID *CORNER` | `CornerPoint` | one of three corner encodings (below) |

## CART and VARI

`*GRID *CART` is a regular Cartesian grid; `*GRID *VARI` allows variable cell
sizes and depths. Both are expressed through `BLOCKSIZE` and `BLOCKDEPTH`, so
pysr3 builds them with the same strategy:

```python
grid = GridBuilder(sr3).build(grid_type="Cartesian")
```

## RADIAL

`*GRID *RADIAL` is a radial/cylindrical grid. pysr3 reconstructs the wedge
geometry from `BLOCKSIZE` (Δr, arc length, Δz) and `WELLRADIUS`, and subdivides
wide wedges so they render as smooth arcs.

```python
grid = GridBuilder(sr3).build(grid_type="Radial")
```

## CORNER

`*GRID *CORNER` is a corner-point grid. STARS can write the corner geometry in
three different ways; pysr3 detects and handles all of them:

- `NODES` + `BLOCKS` — explicit nodes and cell connectivity (precomputed by CMG).
- `XCORNCRCN` + `YCORNCRCN` + `ZCORNCRCN` — compressed structured corners.
- `COORD` + `ZCORN` — Eclipse-style pillar grid.

```python
grid = GridBuilder(sr3).build(grid_type="CornerPoint")
```

### Convert-to-corner-point

`*CONVERT-TO-CORNER-POINT` converts a Cartesian-type grid to corner-point at
run time — typically to handle non-matching corners in a `*VARI` grid. The
resulting SR3 uses corner geometry arrays and is built as `CornerPoint`.

!!! warning "Limitations of the conversion"
    It is a run-time conversion (the DAT file is not rewritten), is not meant to
    preserve hand-built fault geometry, and cannot be combined with some
    grid-modifying keywords such as `*PINCHOUTARRAY`.

## LGR

LGR comes from `*REFINE`. pysr3 infers each cell's level from the parent
pointers (`ICSTPB`) and segment offsets (`IGNTNC`), and you choose what to show
with `grid_mode` (`mixed`, `refined`, `levelN`). Nested (multi-level) refinement
is supported and validated with `test/lgr_nested/lgr_nested.sr3`, whose `mixed`
grid keeps 36 leaf cells across levels 0/1/2.

![Nested LGR overview](../../assets/images/lgr_nested_overview.png)

See [Building grids](../grid-building.md) for the display modes and
[DFN vs LGR](dfn-vs-lgr.md) for why DFN is handled separately.

??? quote "Manual references (STARS)"
    `CONVERT-TO-CORNER-POINT_ConvertCartesianGridToCornerPoint.htm`,
    `REFINE_LocalRefinedGrid.htm`.
