# Coordinate system & display scale

In CMG SR3, **Z usually means depth** and increases downward. Most 3D
visualization tools use a **Z-up** convention (up is positive). A corner-point
grid displayed with raw SR3 depths can therefore appear vertically flipped.

## Build coordinates vs. display coordinates

pysr3 keeps the two separate:

| File | Purpose |
|---|---|
| `grid.vtu` | Core **build** coordinates — the authoritative geometry. |
| `grid_display.vtu` | **Display** copy — may flip Z and apply scale exaggeration. |
| `overview.png`, `slice.png` | Rendered from the display copy. |

!!! warning
    Never feed display-scaled coordinates back into numerical calculations.
    Use `grid.vtu` (build coordinates) for any quantitative work.

## What each grid family outputs

| Grid source | Core Z | Notes |
|---|---|---|
| `Cartesian` / `VARI` | usually Z-up | positive `BLOCKDEPTH` is converted to negative Z |
| `Radial` | local thickness | built from local thickness, not absolute burial depth |
| `CornerPoint` `NODES/BLOCKS` | usually depth | Z increases downward |
| `CornerPoint` `XCORNCRCN/...` | usually depth | includes convert-to-corner cases |

Because most corner-point SR3 files store depth, the exporter defaults to
`depth-up` display for corner cases.

## Display Z modes

| Mode | Meaning | Use when |
|---|---|---|
| `keep` | keep current Z, only translate/scale | the grid is already Z-up |
| `depth-up` | convert positive-downward depth to Z-up | most `CornerPoint` SR3 |
| `flip` | flip the current Z direction | a manual check shows it upside down |

Defaults: `Cartesian`, `VARI`, `Radial`, and LGR use `keep`; corner-point cases
use `depth-up`.

## Vertical exaggeration

Reservoir models are usually wide and thin, so the exporter exaggerates Z by 10×
by default. Control it from the command line:

```bash
# vertical exaggeration of 20×
python tools/export_case_assets.py --case tutorial_hm --scale-z 20

# per-axis scale
python tools/export_case_assets.py --case tutorial_hm --scale-x 1 --scale-y 1 --scale-z 20

# no exaggeration
python tools/export_case_assets.py --scale-z 1

# force a specific Z mode for all cases
python tools/export_case_assets.py --z-mode keep
python tools/export_case_assets.py --z-mode flip
```
