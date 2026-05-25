"""Radial grid strategy with adaptive angular subdivision."""

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
    parse_kdir,
    segment_ijk,
)

logger = logging.getLogger(__name__)

# Maximum angular width (degrees) of a rendered wedge before it is subdivided,
# so radial cells render as smooth arcs rather than coarse polygons.
MAX_ANGLE_DEG = 5.0


@register_strategy("Radial")
class RadialGridStrategy(GridStrategy):
    """Build a radial grid, subdividing wide wedges for smooth visualization."""

    def build(self, data: Dict, time_step: int, grid_mode: str, include_inactive: bool):
        try:
            igntnc = data["IGNTNC"]
            igntid = data["IGNTID"]
            igntjd = data["IGNTJD"]
            igntkd = data["IGNTKD"]
            blocksize = data["BLOCKSIZE"]
            icstps = data["ICSTPS"]
            icstpb = data["ICSTPB"]
        except KeyError as exc:
            raise ValueError(f"Missing required Radial grid array: {exc}")
        wellradius = data.get("WELLRADIUS", np.zeros(len(igntid)))

        total_cells = len(icstps)
        level = infer_levels(icstpb, igntnc)
        i_full, j_full, k_full = segment_ijk(igntid, igntjd, igntkd, igntnc, total_cells)

        if blocksize.size != total_cells * 3:
            raise ValueError(f"Radial BLOCKSIZE shape {blocksize.shape} mismatch.")
        bs = blocksize.reshape(total_cells, 3)
        dr_all, arc_length_all, dz_all = bs[:, 0], bs[:, 1], bs[:, 2]

        is_kdir_up = parse_kdir(data, default="DOWN") == "UP"
        mode_keep = grid_mode_keep_mask(grid_mode, level, icstpb, igntnc)

        # Per-segment corner arrays and cell data, concatenated once at the end.
        corner_cols = [[] for _ in range(8)]
        data_cols: Dict[str, list] = {k: [] for k in ("gid", "prop", "level", "i", "j", "k")}

        num_segments = len(igntid)
        for seg_idx in range(num_segments):
            start = igntnc[seg_idx]
            end = igntnc[seg_idx + 1] if seg_idx < num_segments - 1 else total_cells
            if end - start == 0:
                continue

            ni, nj, nk = igntid[seg_idx], igntjd[seg_idx], igntkd[seg_idx]
            r0 = wellradius[seg_idx] if seg_idx < len(wellradius) else 0.0

            dr = dr_all[start:end].reshape((nk, nj, ni))
            arc_length = arc_length_all[start:end].reshape((nk, nj, ni))
            dz = dz_all[start:end].reshape((nk, nj, ni))

            r_outer = r0 + np.cumsum(dr, axis=2)
            r_inner = r_outer - dr
            r_center = r_inner + dr / 2.0

            with np.errstate(divide="ignore", invalid="ignore"):
                dtheta = arc_length / r_center
                dtheta[r_center == 0] = 0
            theta_end = np.cumsum(dtheta, axis=1)
            theta_start = theta_end - dtheta

            if is_kdir_up:
                total_thickness = np.sum(dz, axis=0)
                z_cum = np.cumsum(dz, axis=0)
                z_top = total_thickness - z_cum
                z_bottom = z_top + dz
            else:
                z_bottom = np.cumsum(dz, axis=0)
                z_top = z_bottom - dz

            r_in_flat = r_inner.flatten()
            r_out_flat = r_outer.flatten()
            t_start_flat = theta_start.flatten()
            t_width_flat = dtheta.flatten()
            z_t_flat = z_top.flatten()
            z_b_flat = z_bottom.flatten()

            seg_global_ids = np.arange(start, end)
            i_flat = i_full[start:end]
            j_flat = j_full[start:end]
            k_flat = k_full[start:end]

            # Geometry validity: in the first ring (I=0) all J columns coincide.
            geo_mask = ~((i_flat == 0) & (j_flat > 0))
            if not include_inactive:
                geo_mask &= active_cell_mask(icstps, data)[start:end]
            geo_mask &= mode_keep[seg_global_ids]

            keep = np.where(geo_mask)[0]
            if keep.size == 0:
                continue

            k_r_in = r_in_flat[keep]
            k_r_out = r_out_flat[keep]
            k_t_start = t_start_flat[keep]
            k_t_width = t_width_flat[keep]
            k_z_t = z_t_flat[keep]
            k_z_b = z_b_flat[keep]
            k_global_ids = seg_global_ids[keep]

            # Adaptive subdivision: split each wedge into <=MAX_ANGLE_DEG slices.
            n_sub = np.ceil(np.degrees(k_t_width) / MAX_ANGLE_DEG).astype(int)
            n_sub = np.maximum(n_sub, 1)
            counts = n_sub
            total_sub = int(np.sum(counts))

            e_r_in = np.repeat(k_r_in, counts)
            e_r_out = np.repeat(k_r_out, counts)
            e_z_t = np.repeat(k_z_t, counts)
            e_z_b = np.repeat(k_z_b, counts)

            ends = np.cumsum(counts)
            starts = np.concatenate(([0], ends[:-1]))
            e_starts = np.repeat(starts, counts)
            step_idx = np.arange(total_sub) - e_starts
            sub_width = np.repeat(k_t_width, counts) / np.repeat(counts, counts)
            e_t_start = np.repeat(k_t_start, counts) + step_idx * sub_width
            e_t_end = e_t_start + sub_width

            def pol2cart(r, t, z):
                return np.column_stack((r * np.cos(t), r * np.sin(t), z))

            corner_cols[0].append(pol2cart(e_r_in, e_t_start, e_z_t))
            corner_cols[1].append(pol2cart(e_r_out, e_t_start, e_z_t))
            corner_cols[2].append(pol2cart(e_r_out, e_t_end, e_z_t))
            corner_cols[3].append(pol2cart(e_r_in, e_t_end, e_z_t))
            corner_cols[4].append(pol2cart(e_r_in, e_t_start, e_z_b))
            corner_cols[5].append(pol2cart(e_r_out, e_t_start, e_z_b))
            corner_cols[6].append(pol2cart(e_r_out, e_t_end, e_z_b))
            corner_cols[7].append(pol2cart(e_r_in, e_t_end, e_z_b))

            data_cols["gid"].append(np.repeat(k_global_ids, counts))
            data_cols["prop"].append(np.repeat(icstps[k_global_ids] - 1, counts))
            data_cols["level"].append(np.repeat(level[k_global_ids], counts))
            data_cols["i"].append(np.repeat(i_flat[keep], counts))
            data_cols["j"].append(np.repeat(j_flat[keep], counts))
            data_cols["k"].append(np.repeat(k_flat[keep], counts))

        if not corner_cols[0]:
            return pv.UnstructuredGrid()

        corners = [np.concatenate(col) for col in corner_cols]
        cells, cell_types, points = hexahedra_from_corners(corners)
        grid = pv.UnstructuredGrid(cells, cell_types, points)

        global_ids = np.concatenate(data_cols["gid"])
        grid.cell_data["GlobalCellID"] = global_ids
        grid.cell_data["PropGlobalID"] = np.concatenate(data_cols["prop"])
        grid.cell_data["Level"] = np.concatenate(data_cols["level"])
        grid.cell_data["I"] = np.concatenate(data_cols["i"])
        grid.cell_data["J"] = np.concatenate(data_cols["j"])
        grid.cell_data["K"] = np.concatenate(data_cols["k"])

        parent_i, parent_j, parent_k = compute_parent_ijk(icstpb, level, i_full, j_full, k_full)
        grid.cell_data["ParentI"] = parent_i[global_ids]
        grid.cell_data["ParentJ"] = parent_j[global_ids]
        grid.cell_data["ParentK"] = parent_k[global_ids]
        return grid
