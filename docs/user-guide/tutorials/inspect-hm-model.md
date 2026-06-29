# In-depth: exploring a history-match model

This is a complete, practical walkthrough built around one real STARS model,
`test/50the_datafile/tutorial_hm.sr3` — a corner-point history-match case. We'll
go from opening the file to 3D scenes, isosurfaces, filters, cross-sections,
contour lines, and time-series plots, with every snippet runnable as-is.

!!! info "About this dataset"
    A `CornerPoint` grid of **2616 cells** (I 2–24, J 1–33, K 0–3) over **8
    output times** (0–~300 days). Spatial properties include `PRES`, `TEMP`,
    `SO`, `SG`, `SW`; ten wells (`Well 1` … `Well 10`) report `OILRATSC`,
    `BHP`, and more.

All 3D rendering uses [PyVista](https://docs.pyvista.org/); the time-series
plots use Matplotlib. On a headless machine, set `pyvista.OFF_SCREEN = True`
first (see [Installation](../installation.md#headless--server-rendering)).

## 1. Open the file and see what's inside

```python
from pysr3 import SR3Indexer, GridBuilder, DataMapper

SR3 = "test/50the_datafile/tutorial_hm.sr3"

with SR3Indexer(SR3, eager_list_steps=None) as sr3:
    time_steps = sr3.get_spatial_time_steps()                 # [0, 9, 26, 30, 34, 37, 40, 43]
    print("times (days):", [round(sr3.get_time_offset(t), 1) for t in time_steps])
    print("grid steps:", sr3.get_grid_time_steps())   # [0]
    print("properties @ t0:", sr3.get_available_properties(0))
    print("time-series entities:", sr3.get_timeseries_entities())
    print("wells:", [o for o in sr3.get_timeseries_info("WELLS")["origins"] if o])
```

Example output (note `Well 5` is simply absent from this dataset):

```text
times (days): [0.0, 1.0, 60.0, 91.0, 121.0, 152.0, 182.0, 213.0]
grid steps: [0]
properties @ t0: ['MODBVOL', 'PERMI', 'PERMJ', 'PERMK', 'POROS', 'PRES', 'SG', 'SO', 'SW', 'TEMP']
time-series entities: ['GROUPS', 'LAYERS', 'SECTORS', 'WELLS']
wells: ['Well 1', 'Well 10', 'Well 2', 'Well 3', 'Well 4', 'Well 6', 'Well 7', 'Well 8', 'Well 9']
```

`get_spatial_time_steps()` returns SR3 step indices; `get_time_offset()` converts a
step to elapsed days. Geometry is written only at step 0 here — that's normal,
and mapping at any later step reuses it automatically.

## 2. Build the grid and attach an attribute

`GridBuilder` makes the mesh; `DataMapper` maps a property onto its cells. A
mapped column drops straight into `grid.cell_data`:

```python
import numpy as np

with SR3Indexer(SR3, eager_list_steps=None) as sr3:
    grid = GridBuilder(sr3).build(grid_type="CornerPoint")
    mapper = DataMapper(sr3)

    last = sr3.get_spatial_time_steps()[-1]
    grid.cell_data["PRES"] = mapper.map_prop(grid, "PRES", last).iloc[:, 0].to_numpy()

    print(grid.n_cells, "cells")
    print("PRES range:", np.nanmin(grid.cell_data["PRES"]), np.nanmax(grid.cell_data["PRES"]))
```

```text
2616 cells
PRES range: 21073.6 28643.4
```

!!! tip "`.iloc[:, 0]`"
    `map_prop` returns a labelled DataFrame (one column per keyword × time). For
    a single keyword/time, `.iloc[:, 0].to_numpy()` is the cell array.

## 3. Vertical exaggeration and depth-up display

This model stores Z as **depth** (positive, ~3000 m over a ~4 km footprint that
is only ~180 m thick) — at true scale it looks like a flat sheet, so 3D scenes
usually exaggerate the vertical and flip depth so shallow is up.

The simplest, native way is **`Plotter.set_scale`**, which scales only the
*view*. Your data stays in true coordinates, so slicing, mapping and export are
unaffected — no copy, no point-array edits:

```python
plotter.add_mesh(grid, scalars="PRES", cmap="turbo")
plotter.set_scale(zscale=8)                      # 8x vertical exaggeration (display only)

# each axis scales independently; a negative value flips that axis,
# so a negative zscale turns positive-down depth into "up":
plotter.set_scale(xscale=1, yscale=1, zscale=-8)
```

The same field at true scale (flat) → moderate → strong exaggeration:

![Vertical exaggeration](../../assets/images/guide_exaggeration.png)

When you only want to *look* at the grid, `set_scale` is all you need. A few
sections below also **slice and contour** the geometry, so they build a display
copy once — again with PyVista's native scaling (`scale` + `flip_z`), not manual
point math:

```python
def display_grid(grid, exaggerate=6.0):
    """Depth-up, vertically exaggerated copy — for display only, not for math."""
    return grid.scale((1, 1, exaggerate), inplace=False).flip_z(inplace=False)

disp = display_grid(grid)
```

See [Coordinate system & display scale](../concepts/coordinate-system.md) for
the rationale.

## 4. 3D plotting

```python
import pyvista as pv
# pv.OFF_SCREEN = True   # uncomment on a headless server

plotter = pv.Plotter(window_size=(1200, 820))
plotter.set_background("white")
plotter.add_mesh(
    grid,
    scalars="PRES",
    cmap="turbo",
    scalar_bar_args={"title": "PRES (kPa)", "vertical": True},
)
plotter.set_scale(zscale=-8)       # depth-up + 8x exaggeration (display only)
plotter.add_axes()
plotter.camera_position = "iso"
plotter.show()                     # or: plotter.screenshot("pres_3d.png")
```

![3D pressure](../../assets/images/guide_3d.png)

The anticline (domed) structure is clear, with a fault offset down the middle.

## 5. Attribute and time selection

Pick *which* property and *which* time. Use the discovery calls to drive it:

```python
with SR3Indexer(SR3, eager_list_steps=None) as sr3:
    grid = GridBuilder(sr3).build(grid_type="CornerPoint")
    mapper = DataMapper(sr3)

    # one property at several times -> a multi-column DataFrame
    df = mapper.map_prop(grid, "SO", sr3.get_spatial_time_steps())
    print(df.columns.names)        # ['Keyword','LongName','Unit','Time','TimeIndex','TimeUnit']
    print(df.columns.get_level_values("Time"))   # elapsed days per column

    # several properties at one time
    df2 = mapper.map_prop(grid, ["PRES", "TEMP", "SW"], sr3.get_spatial_time_steps()[-1])
```

```text
['Keyword', 'LongName', 'Unit', 'Time', 'TimeIndex', 'TimeUnit']
[0.0, 1.0, 60.0, 91.0, 121.0, 152.0, 182.0, 213.0]
```

To select by *elapsed time* rather than a step index, find the nearest step:

```python
def step_nearest_days(sr3, target_days):
    steps = sr3.get_spatial_time_steps()
    return min(steps, key=lambda s: abs(sr3.get_time_offset(s) - target_days))

step = step_nearest_days(sr3, 150)     # closest step to day 150
```

The DataFrame columns carry the unit too — handy for axis labels:

```python
unit = df.columns.get_level_values("Unit")[0]
```

## 6. Color palette selection

`cmap` accepts any Matplotlib colormap. Pick by data type:

| Data | Good colormaps |
|---|---|
| Sequential (PRES, SO, TEMP) | `viridis`, `turbo`, `inferno`, `magma`, `cividis` |
| Diverging (change, residual) | `coolwarm`, `RdBu_r`, `Spectral_r` |
| Categorical (`Level`, `K`) | `Set2`, `tab10` (with `n_colors`) |

The same `PRES` field under three colormaps — `viridis`, `coolwarm`, `cividis`
(just change `cmap=`):

![Colormap comparison](../../assets/images/guide_palette.png)

Fix the range and style out-of-range / missing values:

```python
plotter.add_mesh(
    disp,
    scalars="PRES",
    cmap="cividis",
    clim=(21000, 28700),       # fixed color range (consistent across times)
    below_color="navy",         # values < clim[0]
    above_color="red",          # values > clim[1]
    nan_color="#dddddd",        # inactive / unmapped cells
    n_colors=12,                # discrete bands instead of a smooth ramp
)
```

!!! tip
    When comparing several time steps, set the same `clim` on every frame so
    colors mean the same thing.

## 7. Isosurfaces

Isosurfaces need *point* data, so convert cell data first, then contour:

```python
point_grid = disp.cell_data_to_point_data()
iso = point_grid.contour(isosurfaces=6, scalars="PRES")   # 6 evenly spaced levels
# explicit levels: point_grid.contour(isosurfaces=[22000, 25000, 28000], scalars="PRES")

plotter = pv.Plotter()
plotter.add_mesh(disp, color="#cccccc", opacity=0.12)     # faint shell for context
plotter.add_mesh(iso, scalars="PRES", cmap="turbo")
plotter.show()
```

![Isosurfaces](../../assets/images/guide_isosurface.png)

### Choosing the number of levels

`isosurfaces=N` places N evenly spaced levels (or pass an explicit list of
values). More levels reveal more structure but clutter the view sooner — 3, 6
and 12 levels of the same field:

```python
for n in (3, 6, 12):
    iso_n = point_grid.contour(isosurfaces=n, scalars="PRES")
    # ... render each into its own subplot or figure
```

![Isosurface level counts](../../assets/images/guide_iso_counts.png)

### Transparency

A low `opacity` lets you see the nested shells and the structure behind them.
Compare `opacity` of 0.3, 0.6 and 1.0:

```python
iso = point_grid.contour(isosurfaces=6, scalars="PRES")
plotter.add_mesh(iso, scalars="PRES", cmap="turbo", opacity=0.3)   # try 0.3 / 0.6 / 1.0
```

![Isosurface transparency](../../assets/images/guide_iso_opacity.png)

## 8. Attribute filtering

`threshold` keeps cells whose scalar is in a range — e.g. the oil-rich cells:

```python
disp.cell_data["SO"] = mapper.map_prop(grid, "SO", last).iloc[:, 0].to_numpy()

so_q = np.nanpercentile(disp.cell_data["SO"], 75)
oil_rich = disp.threshold(value=so_q, scalars="SO")        # SO >= 75th percentile
# a window instead: disp.threshold(value=(0.69, 0.72), scalars="SO")

plotter = pv.Plotter(shape=(1, 3))                 # three viewpoints
for col, view in enumerate(["iso", "xy", "yz"]):
    plotter.subplot(0, col)
    plotter.add_mesh(disp, color="#e2e2e2", opacity=0.07)   # faint context
    plotter.add_mesh(oil_rich, color="#ea580c")             # solid highlight
    plotter.camera_position = view
plotter.show()
```

`SO` spans only ~0.67–0.72 here, so a solid highlight reads better than a
colormap; to color *by* value instead, pass `scalars="SO", clim=(0.67, 0.72)`.
The high-`SO` region is shown from three viewpoints — iso, map (top) and side —
because a single angle hides whether it sits on the crest or the flanks:

![Attribute threshold from three angles](../../assets/images/guide_threshold.png)

## 9. Coordinate and index filtering

Filter by **structured index** (the `I`/`J`/`K` cell arrays) or by **spatial
extent**:

```python
# top layer only (K == 0)
top_layer = disp.threshold(value=(0, 0), scalars="K")

# a spatial sub-box (xmin,xmax, ymin,ymax, zmin,zmax) — here the western half
xmin, xmax, ymin, ymax, zmin, zmax = disp.bounds
west = disp.clip_box((xmin, (xmin + xmax) / 2, ymin, ymax, zmin, zmax), invert=False)

# cut with an arbitrary plane (keep the +Y side)
north = disp.clip(normal="y", origin=disp.center, invert=False)

plotter = pv.Plotter(shape=(1, 3))                  # the top layer, three views
for col, view in enumerate(["iso", "xy", "xz"]):
    plotter.subplot(0, col)
    plotter.add_mesh(top_layer, scalars="PRES", cmap="turbo", show_edges=True)
    plotter.camera_position = view
plotter.show()
```

The extracted top layer (K=0) from three viewpoints — iso, map (top) and front:

![Top layer from three angles](../../assets/images/guide_coordfilter.png)

!!! note
    `threshold` on `I`/`J`/`K` selects logical slabs; `clip_box`/`clip` cut on
    real coordinates. Combine them freely (e.g. threshold a layer, then clip a
    region of it).

## 10. 2D cross-sections

`slice` cuts the grid with a plane:

```python
sx = disp.slice(normal="x", origin=disp.center)   # a YZ cross-section
sy = disp.slice(normal="y", origin=disp.center)   # an XZ cross-section
three = disp.slice_orthogonal()                    # X, Y and Z planes at once

plotter = pv.Plotter()
plotter.add_mesh(sx, scalars="PRES", cmap="turbo", show_edges=True)
plotter.camera_position = "yz"
plotter.show()
```

![Cross-section](../../assets/images/guide_slice.png)

## 11. Contour lines

Contour the **slice's** point data to draw iso-pressure lines on the section:

```python
section = disp.slice(normal="x", origin=disp.center)
lines = section.cell_data_to_point_data().contour(isosurfaces=14, scalars="PRES")

plotter = pv.Plotter()
plotter.add_mesh(section, color="#efeae0")                  # neutral backdrop
plotter.add_mesh(lines, scalars="PRES", cmap="turbo", line_width=3)
plotter.camera_position = "yz"
plotter.show()
```

![Contour lines](../../assets/images/guide_contour.png)

For a classic contour map, overlay the same isolines on a **filled** colormap of
the section instead of a neutral backdrop:

```python
plotter = pv.Plotter()
plotter.add_mesh(section, scalars="PRES", cmap="viridis")   # filled background
plotter.add_mesh(lines, color="black", line_width=1.5)      # isolines on top
plotter.camera_position = "yz"
plotter.show()
```

![Filled contour with isolines](../../assets/images/guide_contour_filled.png)

## 12. Time variation at a coordinate point

Find the cell nearest a target `(x, y, z)`, then read one property across all
times. Because `map_prop` returns time as columns, **one DataFrame row is the
time series**:

```python
import matplotlib.pyplot as plt

with SR3Indexer(SR3, eager_list_steps=None) as sr3:
    grid = GridBuilder(sr3).build(grid_type="CornerPoint")
    mapper = DataMapper(sr3)

    centers = grid.cell_centers().points
    target = np.array([1500.0, 2000.0, grid.bounds[4]])      # x, y, near-top
    cell = int(np.argmin(np.linalg.norm(centers - target, axis=1)))
    ijk = (grid.cell_data["I"][cell], grid.cell_data["J"][cell], grid.cell_data["K"][cell])

    df = mapper.map_prop(grid, "PRES", sr3.get_spatial_time_steps())
    series = df.iloc[cell]
    days = df.columns.get_level_values("Time").astype(float).to_numpy()
    order = np.argsort(days)

    plt.plot(days[order], series.to_numpy()[order], marker="o")
    plt.xlabel("Time (days)"); plt.ylabel("PRES (kPa)")
    plt.title(f"PRES at cell I/J/K = {tuple(int(x) for x in ijk)}")
    plt.show()
```

![Point time series](../../assets/images/guide_point_ts.png)

A **vertical profile** (a property down a column at fixed I, J) is the same idea
on the cell axis instead of the time axis:

```python
last = sr3.get_spatial_time_steps()[-1]
col = mapper.map_prop(grid, "PRES", last)        # one time
ij = (grid.cell_data["I"] == 13) & (grid.cell_data["J"] == 16)
order = np.argsort(grid.cell_data["K"][ij])
plt.plot(col.iloc[:, 0].to_numpy()[ij][order], grid.cell_data["K"][ij][order], marker="o")
plt.gca().invert_yaxis(); plt.xlabel("PRES (kPa)"); plt.ylabel("layer K")
```

![Vertical profile](../../assets/images/guide_profile.png)

## 13. Well and other time series

`get_well_data` returns a tidy DataFrame; loop over wells to compare them:

```python
import matplotlib.pyplot as plt

with SR3Indexer(SR3) as sr3:
    for well in ["Well 1", "Well 2", "Well 3"]:
        d = sr3.get_well_data(wells=[well], variables=["OILRATSC"])
        plt.plot(d["Time"], d["Value"], marker="o", label=well)
    plt.xlabel("Time (days)"); plt.ylabel("Oil rate (OILRATSC)")
    plt.legend(); plt.show()
```

![Well rates](../../assets/images/guide_well_ts.png)

Swap the variable to plot anything the wells report — e.g. bottomhole pressure:

```python
with SR3Indexer(SR3) as sr3:
    for well in ["Well 1", "Well 2", "Well 3"]:
        d = sr3.get_well_data(wells=[well], variables=["BHP"])
        plt.plot(d["Time"], d["Value"], marker="o", label=well)
    plt.xlabel("Time (days)"); plt.ylabel("BHP"); plt.legend(); plt.show()
```

![Well BHP](../../assets/images/guide_bhp_ts.png)

The same `get_timeseries_data` works for other entities and variables:

```python
with SR3Indexer(SR3) as sr3:
    bhp   = sr3.get_well_data(variables=["BHP"])                 # all wells, BHP
    layer = sr3.get_timeseries_data(entity="LAYERS", variables=["OILVOLSC"])
    field = sr3.get_timeseries_data(entity="GROUPS")                 # field/group totals

# cumulative oil for one well
w1 = sr3.get_well_data(wells=["Well 1"], variables=["OILVOLSC"])
```

See [Wells & time series](../concepts/timeseries.md) for the entity model and
output columns.

## 14. Save your results

Everything is standard PyVista / pandas, so exporting is one call:

```python
disp.save("hm_display.vtu")               # open in ParaView
grid.save("hm_build.vtu")                 # build coordinates (for math)
df.to_csv("pres_timeseries.csv")          # the mapped DataFrame
plotter.screenshot("scene.png")           # any rendered scene
```

To regenerate the standard asset bundle (overview, slice, summary) for this
case:

```bash
python tools/export_case_assets.py --case tutorial_hm --scale-z 10
```

## 15. Advanced recipes

These reuse the `sr3`, `grid`, `mapper`, `disp`, and `time_steps` objects from the
sections above.

### Difference map between two times

Subtract two mapped snapshots to see *change*, and show it with a **diverging**
colormap centered on zero — here the pressure drawdown from first to last step:

```python
pres0 = mapper.map_prop(grid, "PRES", time_steps[0]).iloc[:, 0].to_numpy()
presL = mapper.map_prop(grid, "PRES", time_steps[-1]).iloc[:, 0].to_numpy()
disp.cell_data["dPRES"] = presL - pres0

m = np.nanmax(np.abs(disp.cell_data["dPRES"]))      # symmetric range about 0
plotter = pv.Plotter()
plotter.add_mesh(disp, scalars="dPRES", cmap="RdBu_r", clim=(-m, m),
                 scalar_bar_args={"title": "dPRES (last - first)", "vertical": True})
plotter.camera_position = "iso"
plotter.show()
```

![Difference map](../../assets/images/guide_diffmap.png)

The reservoir barely moves overall, but the cells around the wells draw down
sharply (deep blue) — exactly what a diverging map is for.

### Animate a property over time

Write one GIF frame per time step. Fix `clim` across frames so colors are
comparable, and mutate the scalar buffer **in place** so the same actor updates:

```python
lo = min(mapper.map_prop(grid, "PRES", t).iloc[:, 0].min() for t in time_steps)
hi = max(mapper.map_prop(grid, "PRES", t).iloc[:, 0].max() for t in time_steps)

disp.cell_data["PRES"] = mapper.map_prop(grid, "PRES", time_steps[0]).iloc[:, 0].to_numpy()
pres = disp.cell_data["PRES"]                       # mutate this buffer in place

plotter = pv.Plotter(off_screen=True)               # off-screen for GIF capture
plotter.add_mesh(disp, scalars="PRES", cmap="turbo", clim=(lo, hi))
plotter.camera_position = "iso"
plotter.open_gif("pres_over_time.gif", fps=2)
for t in time_steps:
    pres[:] = mapper.map_prop(grid, "PRES", t).iloc[:, 0].to_numpy()
    plotter.add_text(f"day {sr3.get_time_offset(t):.0f}", name="day")
    plotter.write_frame()
plotter.close()
```

![Pressure animation](../../assets/images/guide_anim.gif)

### Property distribution

A histogram of the mapped values is one line — useful for spotting ranges and
outliers before you pick a `clim`:

```python
import matplotlib.pyplot as plt
plt.hist(presL[np.isfinite(presL)], bins=30)
plt.xlabel("PRES (kPa)"); plt.ylabel("cell count"); plt.show()
```

![PRES histogram](../../assets/images/guide_hist.png)

### Volume-weighted field average

A proper field-average pressure weights each cell by its bulk volume. `MODBVOL`
is static (written only at step 0), so read the weights once and reuse them:

```python
bv = mapper.map_prop(grid, "MODBVOL", time_steps[0]).iloc[:, 0].to_numpy()   # static weights

days, avg = [], []
for t in time_steps:
    p = mapper.map_prop(grid, "PRES", t).iloc[:, 0].to_numpy()
    ok = np.isfinite(p) & np.isfinite(bv)
    days.append(sr3.get_time_offset(t))
    avg.append(np.sum(p[ok] * bv[ok]) / np.sum(bv[ok]))

plt.plot(days, avg, marker="o")
plt.xlabel("Time (days)"); plt.ylabel("Volume-weighted mean PRES (kPa)"); plt.show()
```

![Field-average pressure](../../assets/images/guide_field_avg.png)

## Recap

| Task | Key call |
|---|---|
| Read & discover | `SR3Indexer`, `get_spatial_time_steps/properties`, `get_timeseries_*` |
| Build & map | `GridBuilder.build`, `DataMapper.map_prop` |
| 3D scene | `pv.Plotter().add_mesh(scalars=..., cmap=...)` |
| Isosurface | `cell_data_to_point_data().contour(isosurfaces=...)` |
| Attribute filter | `grid.threshold(value=..., scalars=...)` |
| Coordinate filter | `grid.clip_box(...)`, `grid.clip(...)`, threshold on `I/J/K` |
| Cross-section | `grid.slice(normal=..., origin=...)` |
| Contour lines | `slice(...).cell_data_to_point_data().contour(...)` |
| Point time series | `map_prop(grid, kw, all_time_steps).iloc[cell]` |
| Well time series | `get_well_data(...)`, `get_timeseries_data(...)` |
| Difference map | map at two times, subtract, diverging `cmap` + symmetric `clim` |
| Animate over time | `Plotter.open_gif(...)` + `write_frame()` per step |
| Distribution | `plt.hist(map_prop(...))` |
| Field average | volume-weighted mean using static `MODBVOL` |
