"""Cartesian (and VARI) grid strategy with LGR support."""

from __future__ import annotations

import logging
from typing import Dict

import numpy as np
import pyvista as pv

from .base import GridStrategy, register_strategy
from .geometry import (
    active_cell_mask,
    compute_parent_ijk,
    grid_mode_keep_mask,
    hexahedra_from_corners,
    infer_levels,
    segment_ijk,
)

logger = logging.getLogger(__name__)


@register_strategy("Cartesian")
class CartesianGridStrategy(GridStrategy):
    """Build a Cartesian/VARI grid using the exploded-hexahedron approach.

    Every cell becomes 8 explicit corners, which naturally handles variable
    block sizes and LGR refinement; coincident corners are merged later by the
    facade's ``clean`` pass.
    """

    def build(self, data: Dict, time_step: int, grid_mode: str, include_inactive: bool):
        try:
            igntnc = data["IGNTNC"]
            igntid = data["IGNTID"]
            igntjd = data["IGNTJD"]
            igntkd = data["IGNTKD"]
            blocksize = data["BLOCKSIZE"]
            blockdepth = data["BLOCKDEPTH"]
            icstpb = data["ICSTPB"]
            icstps = data["ICSTPS"]
        except KeyError as exc:
            raise ValueError(f"Missing required Cartesian grid array: {exc}")

        total_cells = len(icstps)
        level = infer_levels(icstpb, igntnc)

        # BLOCKDEPTH is absolute cell-centre depth (positive downward). We map it
        # to a Z-up coordinate (Z = -depth). KDIR only governs layer ordering,
        # which BLOCKDEPTH already encodes, so it does not change the sign here.
        z_sign = -1.0

        if blocksize.size != total_cells * 3:
            raise ValueError(
                f"BLOCKSIZE shape {blocksize.shape} mismatch with TotalCells {total_cells}"
            )
        bs = blocksize.reshape(total_cells, 3)
        dx_all, dy_all, dz_all = bs[:, 0], bs[:, 1], bs[:, 2]

        x_min = np.zeros(total_cells, dtype=float)
        x_max = np.zeros(total_cells, dtype=float)
        y_min = np.zeros(total_cells, dtype=float)
        y_max = np.zeros(total_cells, dtype=float)
        z_min = np.zeros(total_cells, dtype=float)
        z_max = np.zeros(total_cells, dtype=float)

        # Parent bounds, used to anchor LGR child coordinates to their parent.
        pb_xmin = np.full(total_cells, np.nan, dtype=float)
        pb_ymin = np.full(total_cells, np.nan, dtype=float)

        num_segments = len(igntid)
        for seg_idx in range(num_segments):
            start = igntnc[seg_idx]
            end = igntnc[seg_idx + 1] if seg_idx < num_segments - 1 else total_cells
            if end - start == 0:
                continue

            ni, nj, nk = igntid[seg_idx], igntjd[seg_idx], igntkd[seg_idx]
            dx = dx_all[start:end]
            dy = dy_all[start:end]
            dz = dz_all[start:end]
            z_center = blockdepth[start:end]

            try:
                dx_3d = dx.reshape((nk, nj, ni))
                dy_3d = dy.reshape((nk, nj, ni))
            except ValueError:
                logger.error(
                    f"Segment {seg_idx} reshape failed: count={end - start}, dims=({nk},{nj},{ni})"
                )
                raise

            z_center_coord = z_sign * z_center
            z_half = dz / 2.0
            z_min[start:end] = z_center_coord - z_half
            z_max[start:end] = z_center_coord + z_half

            if seg_idx == 0:
                # Level 0: absolute coordinates anchored at the origin.
                origin_x = 0.0
                origin_y = 0.0
            else:
                # LGR: anchor to the lower-left corner of the refined parents.
                # NOTE: assumes one segment refines a single contiguous parent
                # box. Segments that group multiple parents are not handled.
                parents = icstpb[start:end] - 1
                p_xmin = pb_xmin[parents]
                p_ymin = pb_ymin[parents]
                if np.any(np.isnan(p_xmin)):
                    raise RuntimeError(f"Segment {seg_idx}: Parent bounds not ready.")
                origin_x = float(np.min(p_xmin))
                origin_y = float(np.min(p_ymin))

            x_r = origin_x + np.cumsum(dx_3d, axis=2)
            x_l = x_r - dx_3d
            y_r = origin_y + np.cumsum(dy_3d, axis=1)
            y_l = y_r - dy_3d

            x_min[start:end] = x_l.flatten()
            x_max[start:end] = x_r.flatten()
            y_min[start:end] = y_l.flatten()
            y_max[start:end] = y_r.flatten()

            pb_xmin[start:end] = x_min[start:end]
            pb_ymin[start:end] = y_min[start:end]

        # --- Filter ---
        keep_mask = np.ones(total_cells, dtype=bool)
        if not include_inactive:
            keep_mask &= active_cell_mask(icstps, data)
        keep_mask &= grid_mode_keep_mask(grid_mode, level, icstpb, igntnc)

        indices = np.where(keep_mask)[0]
        if indices.size == 0:
            logger.warning("No cells to build (all filtered out).")
            return pv.UnstructuredGrid()

        xmin, xmax = x_min[indices], x_max[indices]
        ymin, ymax = y_min[indices], y_max[indices]
        zmin, zmax = z_min[indices], z_max[indices]

        corners = [
            np.column_stack([xmin, ymin, zmin]),
            np.column_stack([xmax, ymin, zmin]),
            np.column_stack([xmax, ymax, zmin]),
            np.column_stack([xmin, ymax, zmin]),
            np.column_stack([xmin, ymin, zmax]),
            np.column_stack([xmax, ymin, zmax]),
            np.column_stack([xmax, ymax, zmax]),
            np.column_stack([xmin, ymax, zmax]),
        ]
        cells, cell_types, points = hexahedra_from_corners(corners)
        grid = pv.UnstructuredGrid(cells, cell_types, points)

        i_arr, j_arr, k_arr = segment_ijk(igntid, igntjd, igntkd, igntnc, total_cells)
        parent_i, parent_j, parent_k = compute_parent_ijk(icstpb, level, i_arr, j_arr, k_arr)

        grid.cell_data["PropGlobalID"] = icstps[indices].astype(np.int32) - 1
        grid.cell_data["GlobalCellID"] = indices
        grid.cell_data["Level"] = level[indices]
        grid.cell_data["I"] = i_arr[indices]
        grid.cell_data["J"] = j_arr[indices]
        grid.cell_data["K"] = k_arr[indices]
        grid.cell_data["ParentI"] = parent_i[indices]
        grid.cell_data["ParentJ"] = parent_j[indices]
        grid.cell_data["ParentK"] = parent_k[indices]
        return grid
