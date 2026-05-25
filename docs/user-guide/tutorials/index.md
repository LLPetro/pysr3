# Tutorials

Each tutorial follows the same shape — **goal → code → result → explanation** —
and runs against a real STARS SR3 file in `test/`. They're meant to be read in
order on a first pass.

<div class="gallery-grid" markdown>

<div class="gallery-card" markdown>
![Cartesian overview](../../assets/images/cartesian_overview.png)
<div markdown>
### [First SR3 case](first-sr3-case.md)
Read an SR3, build a grid, map `PRES`.
</div>
</div>

<div class="gallery-card" markdown>
![Tutorial HM overview](../../assets/images/tutorial_hm_overview.png)
<div markdown>
### [Grid visualization](grid-visualization.md)
Export VTU and renders, with vertical exaggeration.
</div>
</div>

<div class="gallery-card" markdown>
![Convert to corner overview](../../assets/images/convert_to_corner_overview.png)
<div markdown>
### [Corner-point grids](corner-grid.md)
`CornerPoint`, Z direction, and convert-to-corner + DFN.
</div>
</div>

<div class="gallery-card" markdown>
![Well BHP curve](../../assets/images/well_bhp_curve.png)
<div markdown>
### [Well time series](well-timeseries.md)
Read well BHP, export CSV, plot a curve.
</div>
</div>

<div class="gallery-card" markdown>
![HM model pressure](../../assets/images/guide_3d.png)
<div markdown>
### [In-depth: HM model](inspect-hm-model.md)
3D scenes, isosurfaces, filters, slices, contours, and time series.
</div>
</div>

</div>

## Regenerating the figures

The images come from real STARS SR3 cases under `test/`:

```bash
python tools/export_case_assets.py
python tools/export_timeseries_assets.py
```
