#!/usr/bin/env python3
"""Export validation assets for SR3 grid cases.

Outputs per case:
- artifacts/grid.vtu
- artifacts/grid_display.vtu
- artifacts/overview.png
- artifacts/slice.png
- artifacts/summary.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pyvista as pv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pysr3.data_mapper import DataMapper
from pysr3.grid_builder import GridBuilder
from pysr3.sr3_indexer import SR3Indexer


@dataclass(frozen=True)
class CaseSpec:
    name: str
    sr3_path: Path
    grid_type: str
    grid_mode: str = "mixed"
    preferred_scalar: str = "PRES"
    display_z_mode: str = "keep"
    description: str = ""


CASES: tuple[CaseSpec, ...] = (
    CaseSpec("cartesian", ROOT / "test/cartesian/cartesian.sr3", "Cartesian", description="GRID CART"),
    CaseSpec("vari", ROOT / "test/vari/vari.sr3", "Cartesian", description="GRID VARI via Cartesian builder"),
    CaseSpec("radial", ROOT / "test/radial/radial.sr3", "Radial", description="GRID RADIAL"),
    CaseSpec("lgr", ROOT / "test/lgr/lgr.sr3", "Cartesian", description="CART with REFINE/LGR"),
    CaseSpec(
        "lgr_nested",
        ROOT / "test/lgr_nested/lgr_nested.sr3",
        "Cartesian",
        preferred_scalar="Level",
        description="CART with two-level REFINE/LGR",
    ),
    CaseSpec(
        "corner",
        ROOT / "test/corner/corner.sr3",
        "CornerPoint",
        display_z_mode="depth-up",
        description="CORNER DI/DJ/ZCORN",
    ),
    CaseSpec(
        "corner_coord",
        ROOT / "test/corner_coord/corner_coord.sr3",
        "CornerPoint",
        display_z_mode="depth-up",
        description="CORNER COORD/ZCORN",
    ),
    CaseSpec(
        "tutorial_hm",
        ROOT / "test/50the_datafile/tutorial_hm.sr3",
        "CornerPoint",
        display_z_mode="depth-up",
        description="larger non-blocky CORNER model",
    ),
    CaseSpec(
        "convert_to_corner",
        ROOT / "test/convert_to_corner/convert_to_corner.sr3",
        "CornerPoint",
        display_z_mode="depth-up",
        description="CART converted by CONVERT-TO-CORNER-POINT",
    ),
    CaseSpec(
        "dfn_multi",
        ROOT / "test/dfn_multi/dfn_multi.sr3",
        "CornerPoint",
        display_z_mode="depth-up",
        description="CONVERT-TO-CORNER-POINT with four DFUs",
    ),
    CaseSpec(
        "dfn_refine",
        ROOT / "test/dfn_refine/dfn_refine.sr3",
        "CornerPoint",
        preferred_scalar="Level",
        display_z_mode="keep",
        description="DFN_REFINE automatic LGR around four DFUs",
    ),
)


def _case_dir(case: CaseSpec) -> Path:
    return case.sr3_path.parent


def _first_property_time(indexer: SR3Indexer, keyword: str) -> int | None:
    for time_step in indexer.get_spatial_time_steps():
        if keyword in indexer.get_available_properties(time_step):
            return time_step
    return None


def _attach_scalar(indexer: SR3Indexer, grid: pv.UnstructuredGrid, keyword: str) -> tuple[str, int | None, int]:
    time_step = _first_property_time(indexer, keyword)
    if time_step is None:
        grid.cell_data["Level"] = grid.cell_data.get("Level", np.zeros(grid.n_cells, dtype=np.int16))
        return "Level", None, grid.n_cells

    values = DataMapper(indexer).map_prop(grid, keyword, time_step).iloc[:, 0].to_numpy()
    scalar_name = f"{keyword}_t{time_step}"
    grid.cell_data[scalar_name] = values
    return scalar_name, time_step, int(np.isfinite(values).sum())


def _display_grid(
    grid: pv.UnstructuredGrid,
    z_mode: str,
    scale: tuple[float, float, float],
    reference_bounds: tuple[float, float, float, float, float, float] | None = None,
) -> pv.UnstructuredGrid:
    """Create a translated/scaled grid for visual inspection only."""
    if z_mode not in {"keep", "flip", "depth-up"}:
        raise ValueError(f"Unsupported z_mode: {z_mode}")

    display = grid.copy(deep=True)
    points = np.asarray(display.points).copy()
    bounds = reference_bounds or grid.bounds

    if reference_bounds is not None and points.size > 0:
        ref_z_negative = reference_bounds[5] <= 0.0
        ref_z_positive = reference_bounds[4] >= 0.0
        src_z_positive = float(np.nanmin(points[:, 2])) >= 0.0
        src_z_negative = float(np.nanmax(points[:, 2])) <= 0.0
        if (ref_z_negative and src_z_positive) or (ref_z_positive and src_z_negative):
            points[:, 2] *= -1.0

    points[:, 0] = (points[:, 0] - bounds[0]) * scale[0]
    points[:, 1] = (points[:, 1] - bounds[2]) * scale[1]

    if z_mode == "keep":
        points[:, 2] = (points[:, 2] - bounds[4]) * scale[2]
    else:
        points[:, 2] = (bounds[5] - points[:, 2]) * scale[2]

    display.points = points
    return display


def _set_camera(plotter: pv.Plotter, grid: pv.UnstructuredGrid) -> None:
    plotter.camera_position = "iso"
    plotter.camera.zoom(1.15)
    plotter.reset_camera()
    bounds = grid.bounds
    z_span = max(bounds[5] - bounds[4], 1.0)
    plotter.camera.elevation += 12 if z_span > 0 else 0


def _render_overview(
    grid: pv.UnstructuredGrid,
    scalar: str,
    path: Path,
    title: str,
    dfn_grid: pv.UnstructuredGrid | None = None,
) -> None:
    plotter = pv.Plotter(off_screen=True, window_size=(1500, 1000))
    plotter.set_background("white")
    show_edges = grid.n_cells <= 5000
    plotter.add_mesh(
        grid,
        scalars=scalar,
        cmap="viridis",
        show_edges=show_edges,
        edge_color="#3a3a3a",
        line_width=0.25,
        nan_color="#d9d9d9",
        scalar_bar_args={"title": scalar, "vertical": True},
    )
    if dfn_grid is not None and dfn_grid.n_cells > 0:
        plotter.add_mesh(
            dfn_grid,
            color="#111111",
            show_edges=True,
            edge_color="#111111",
            line_width=3.0,
            opacity=1.0,
        )
    plotter.add_text(title, font_size=12, color="black")
    plotter.add_axes()
    _set_camera(plotter, grid)
    plotter.screenshot(str(path))
    plotter.close()


def _render_slice(
    grid: pv.UnstructuredGrid,
    scalar: str,
    path: Path,
    title: str,
    dfn_grid: pv.UnstructuredGrid | None = None,
) -> None:
    bounds = grid.bounds
    spans = np.array([bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]], dtype=float)
    axis = int(np.argmax(spans[:2])) if np.any(spans[:2] > 0) else 0
    normal = ("x", "y", "z")[axis]
    origin = grid.center
    sliced = grid.slice(normal=normal, origin=origin)
    if sliced.n_cells == 0:
        sliced = grid.extract_surface()

    plotter = pv.Plotter(off_screen=True, window_size=(1500, 1000))
    plotter.set_background("white")
    plotter.add_mesh(
        sliced,
        scalars=scalar if scalar in sliced.cell_data or scalar in sliced.point_data else None,
        cmap="viridis",
        show_edges=True,
        edge_color="#262626",
        line_width=0.4,
        nan_color="#d9d9d9",
        scalar_bar_args={"title": scalar, "vertical": True},
    )
    if dfn_grid is not None and dfn_grid.n_cells > 0:
        dfn_sliced = dfn_grid.slice(normal=normal, origin=origin)
        if dfn_sliced.n_points == 0:
            dfn_sliced = dfn_grid.extract_surface()
        plotter.add_mesh(
            dfn_sliced,
            color="#111111",
            show_edges=True,
            edge_color="#111111",
            line_width=3.0,
            opacity=1.0,
        )
    plotter.add_text(f"{title} | center {normal.upper()} slice", font_size=12, color="black")
    plotter.add_axes()
    _set_camera(plotter, grid)
    plotter.screenshot(str(path))
    plotter.close()


def export_case(
    case: CaseSpec,
    z_mode_override: str | None = None,
    display_scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> dict:
    if not case.sr3_path.exists():
        raise FileNotFoundError(f"SR3 not found: {case.sr3_path}")

    artifact_dir = _case_dir(case) / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    with SR3Indexer(str(case.sr3_path), eager_list_steps=None) as indexer:
        builder = GridBuilder(indexer)
        grid = builder.build(
            grid_type=case.grid_type,
            grid_mode=case.grid_mode,
            time_step=0,
        )
        if grid.n_cells == 0:
            raise RuntimeError(f"Empty grid for case {case.name}")

        scalar, scalar_time, finite_count = _attach_scalar(indexer, grid, case.preferred_scalar)

        z_mode = z_mode_override or case.display_z_mode
        display = _display_grid(grid, z_mode=z_mode, scale=display_scale)
        dfn_segments = builder.build_dfn_segments(time_step=0)
        dfn_units = builder.build_dfn_units(time_step=0)
        dfn_display = (
            _display_grid(dfn_segments, z_mode=z_mode, scale=display_scale, reference_bounds=grid.bounds)
            if dfn_segments.n_cells > 0
            else dfn_segments
        )

        vtu_path = artifact_dir / "grid.vtu"
        display_vtu_path = artifact_dir / "grid_display.vtu"
        dfn_segments_path = artifact_dir / "dfn_segments.vtu"
        dfn_segments_display_path = artifact_dir / "dfn_segments_display.vtu"
        dfn_units_path = artifact_dir / "dfn_units.vtu"
        overview_path = artifact_dir / "overview.png"
        slice_path = artifact_dir / "slice.png"
        summary_path = artifact_dir / "summary.json"

        grid.save(vtu_path)
        display.save(display_vtu_path)
        if dfn_segments.n_cells > 0:
            dfn_scalar, _, _ = _attach_scalar(indexer, dfn_segments, case.preferred_scalar)
            if dfn_scalar in dfn_segments.cell_data:
                dfn_display.cell_data[dfn_scalar] = dfn_segments.cell_data[dfn_scalar]
            dfn_segments.save(dfn_segments_path)
            dfn_display.save(dfn_segments_display_path)
        if dfn_units.n_cells > 0:
            dfn_units.save(dfn_units_path)
        _render_overview(display, scalar, overview_path, case.name, dfn_grid=dfn_display)
        _render_slice(display, scalar, slice_path, case.name, dfn_grid=dfn_display)

        summary = {
            "case": case.name,
            "description": case.description,
            "sr3": str(case.sr3_path.relative_to(ROOT)),
            "grid_type": case.grid_type,
            "grid_mode": case.grid_mode,
            "cells": int(grid.n_cells),
            "points": int(grid.n_points),
            "dfn_segment_cells": int(dfn_segments.n_cells),
            "dfn_unit_cells": int(dfn_units.n_cells),
            "bounds": [float(x) for x in grid.bounds],
            "display_bounds": [float(x) for x in display.bounds],
            "display_z_mode": z_mode,
            "display_scale": [float(x) for x in display_scale],
            "levels": sorted(int(x) for x in np.unique(grid.cell_data.get("Level", np.array([0])))),
            "times": [int(x) for x in indexer.get_spatial_time_steps()],
            "grid_steps": [int(x) for x in indexer.get_grid_time_steps()],
            "properties_t0": indexer.get_available_properties(0),
            "scalar": scalar,
            "scalar_time": scalar_time,
            "finite_scalar_cells": finite_count,
            "outputs": {
                "vtu": str(vtu_path.relative_to(ROOT)),
                "display_vtu": str(display_vtu_path.relative_to(ROOT)),
                "overview": str(overview_path.relative_to(ROOT)),
                "slice": str(slice_path.relative_to(ROOT)),
            },
        }
        if dfn_segments.n_cells > 0:
            summary["outputs"]["dfn_segments_vtu"] = str(dfn_segments_path.relative_to(ROOT))
            summary["outputs"]["dfn_segments_display_vtu"] = str(dfn_segments_display_path.relative_to(ROOT))
        if dfn_units.n_cells > 0:
            summary["outputs"]["dfn_units_vtu"] = str(dfn_units_path.relative_to(ROOT))
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary


def _select_cases(names: Iterable[str] | None) -> list[CaseSpec]:
    if not names:
        return list(CASES)
    requested = set(names)
    cases_by_name = {case.name: case for case in CASES}
    missing = sorted(requested - set(cases_by_name))
    if missing:
        raise ValueError(f"Unknown case(s): {', '.join(missing)}")
    return [cases_by_name[name] for name in names]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export VTU and PNG assets for SR3 grid cases.")
    parser.add_argument("--case", action="append", dest="cases", help="Case name to export. Repeatable.")
    parser.add_argument(
        "--z-mode",
        choices=("case", "keep", "flip", "depth-up"),
        default="case",
        help="Display Z transform. 'case' uses each case default.",
    )
    parser.add_argument("--scale-x", type=float, default=1.0, help="Display X scale.")
    parser.add_argument("--scale-y", type=float, default=1.0, help="Display Y scale.")
    parser.add_argument("--scale-z", type=float, default=10.0, help="Display Z scale / vertical exaggeration.")
    args = parser.parse_args()

    pv.OFF_SCREEN = True
    summaries = []
    z_mode_override = None if args.z_mode == "case" else args.z_mode
    display_scale = (args.scale_x, args.scale_y, args.scale_z)
    for case in _select_cases(args.cases):
        summary = export_case(case, z_mode_override=z_mode_override, display_scale=display_scale)
        summaries.append(summary)
        print(
            f"{summary['case']}: cells={summary['cells']} points={summary['points']} "
            f"dfn_segments={summary['dfn_segment_cells']} "
            f"scalar={summary['scalar']} finite={summary['finite_scalar_cells']} "
            f"z_mode={summary['display_z_mode']} scale={summary['display_scale']}"
        )

    out_path = ROOT / "test/case_assets_summary.json"
    out_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"summary={out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
