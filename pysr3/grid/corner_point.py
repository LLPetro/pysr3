"""Corner-point grid strategy.

Recognises three SR3 geometry encodings and falls back to the Cartesian builder
when a CONVERT-TO-CORNER-POINT case lacks explicit corner geometry:

1. ``NODES`` + ``BLOCKS``                       (pre-computed by CMG)
2. ``XCORNCRCN`` + ``YCORNCRCN`` + ``ZCORNCRCN`` (compressed structured corners)
3. ``COORD`` + ``ZCORN``                         (Eclipse-style pillar grid)
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple

import numpy as np
import pyvista as pv

from .base import GridStrategy, register_strategy
from .cartesian import CartesianGridStrategy
from .geometry import (
    active_cell_mask,
    compute_parent_ijk,
    grid_mode_keep_mask,
    infer_levels,
    refined_parent_ids,
    subgrid_ijk,
)

logger = logging.getLogger(__name__)


@register_strategy("CornerPoint")
class CornerPointGridStrategy(GridStrategy):
    """Build a corner-point grid from any supported SR3 encoding."""

    def build(self, data: Dict, grid_mode: str, include_inactive: bool,
              keep_refined_parents: bool = True):
        nodes, blocks = self._resolve_nodes_blocks(
            data, grid_mode, include_inactive, keep_refined_parents
        )
        if nodes is None:  # Cartesian fallback already produced the grid
            return blocks

        icstps = data.get("ICSTPS")
        if icstps is None:
            raise ValueError("Missing ICSTPS for CornerPoint grid.")
        icstpb = data.get("ICSTPB")
        igntnc = data.get("IGNTNC")
        total_cells = len(icstps)

        if icstpb is not None and igntnc is not None:
            level = infer_levels(icstpb, igntnc)
        else:
            level = np.zeros(total_cells, dtype=np.int16)

        icstcg = data.get("ICSTCG")
        keep_mask = np.ones(total_cells, dtype=bool)
        if not include_inactive:
            active = active_cell_mask(icstps, data)
            if keep_refined_parents and icstpb is not None and igntnc is not None:
                refined_parents = refined_parent_ids(icstpb, igntnc, icstcg=icstcg)
                if refined_parents.size:
                    active[refined_parents] = True
            keep_mask &= active
        if icstpb is not None and igntnc is not None:
            keep_mask &= grid_mode_keep_mask(grid_mode, level, icstpb, igntnc, icstcg=icstcg)
        elif grid_mode == "refined":
            keep_mask &= level > 0
        elif grid_mode.startswith("level"):
            try:
                keep_mask &= level == int(grid_mode[len("level"):])
            except ValueError:
                pass

        indices = np.where(keep_mask)[0]
        if indices.size == 0:
            logger.warning("No cells to build.")
            return pv.UnstructuredGrid()

        points = nodes.reshape(-1, 3) if nodes.ndim == 1 else nodes
        blocks_reshaped = blocks.reshape(total_cells, 8) if blocks.ndim == 1 else blocks
        kept_blocks = blocks_reshaped[indices]

        # CMG node indices are usually 1-based; shift to 0-based when no node 0
        # is referenced. (Edge case: a 0-based grid that never uses node 0.)
        if np.min(kept_blocks) >= 1:
            kept_blocks = kept_blocks - 1

        num_keep = indices.size
        cells_matrix = np.zeros((num_keep, 9), dtype=np.int64)
        cells_matrix[:, 0] = 8
        cells_matrix[:, 1:] = kept_blocks
        cell_types = np.full(num_keep, pv.CellType.HEXAHEDRON, dtype=np.uint8)
        grid = pv.UnstructuredGrid(cells_matrix.flatten(), cell_types, points)

        grid.cell_data["PropGlobalID"] = icstps[indices].astype(np.int32) - 1
        grid.cell_data["GlobalCellID"] = indices
        grid.cell_data["Level"] = level[indices]

        i_arr = np.full(total_cells, -1, dtype=np.int32)
        j_arr = np.full(total_cells, -1, dtype=np.int32)
        k_arr = np.full(total_cells, -1, dtype=np.int32)
        if all(k in data for k in ("IGNTID", "IGNTJD", "IGNTKD")) and igntnc is not None:
            try:
                i_arr, j_arr, k_arr = subgrid_ijk(
                    data["IGNTID"], data["IGNTJD"], data["IGNTKD"], igntnc, total_cells
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed to generate IJK for CornerPoint: {exc}")

        if icstpb is not None:
            parent_i, parent_j, parent_k = compute_parent_ijk(icstpb, level, i_arr, j_arr, k_arr)
        else:
            parent_i = np.full(total_cells, -1, dtype=np.int32)
            parent_j = np.full(total_cells, -1, dtype=np.int32)
            parent_k = np.full(total_cells, -1, dtype=np.int32)

        grid.cell_data["I"] = i_arr[indices]
        grid.cell_data["J"] = j_arr[indices]
        grid.cell_data["K"] = k_arr[indices]
        grid.cell_data["ParentI"] = parent_i[indices]
        grid.cell_data["ParentJ"] = parent_j[indices]
        grid.cell_data["ParentK"] = parent_k[indices]
        return grid

    # ------------------------------------------------------------------ #
    # Geometry-encoding resolution
    # ------------------------------------------------------------------ #
    def _resolve_nodes_blocks(self, data, grid_mode, include_inactive,
                               keep_refined_parents=True):
        """Return ``(nodes, blocks)``; or ``(None, grid)`` for the fallback."""
        if "NODES" in data and "BLOCKS" in data:
            return data["NODES"], data["BLOCKS"]
        if all(k in data for k in ("XCORNCRCN", "YCORNCRCN", "ZCORNCRCN")):
            logger.info("Using compressed corner-coordinate path for CornerPoint grid")
            return self._crcn_to_nodes_blocks(data)
        if "COORD" in data and "ZCORN" in data:
            logger.info("Using COORD/ZCORN legacy path for CornerPoint grid")
            return self._coord_zcorn_to_nodes_blocks(data)
        if all(k in data for k in ("BLOCKSIZE", "BLOCKDEPTH", "IGNTID", "IGNTJD", "IGNTKD")):
            logger.warning(
                "CornerPoint geometry arrays are absent; falling back to Cartesian/LGR arrays. "
                "This can occur for CONVERT-TO-CORNER-POINT cases with DFN_REFINE."
            )
            cartesian = CartesianGridStrategy(self.indexer)
            return None, cartesian.build(
                data, grid_mode, include_inactive, keep_refined_parents
            )
        raise ValueError(
            "CornerPoint grid requires NODES/BLOCKS, compressed "
            "XCORNCRCN/YCORNCRCN/ZCORNCRCN, or COORD/ZCORN arrays"
        )

    def _crcn_to_nodes_blocks(self, data: Dict) -> Tuple[np.ndarray, np.ndarray]:
        """Convert compressed structured corner arrays to NODES/BLOCKS (vectorized)."""
        xcorn = np.asarray(data["XCORNCRCN"], dtype=float).ravel()
        ycorn = np.asarray(data["YCORNCRCN"], dtype=float).ravel()
        zcorn = np.asarray(data["ZCORNCRCN"], dtype=float).ravel()
        if not (xcorn.size == ycorn.size == zcorn.size):
            raise ValueError(
                "Compressed corner arrays must have the same length: "
                f"XCORNCRCN={xcorn.size}, YCORNCRCN={ycorn.size}, ZCORNCRCN={zcorn.size}"
            )
        for key in ("IGNTID", "IGNTJD", "IGNTKD", "IGNTNC", "ICSTPS"):
            if key not in data:
                raise ValueError(f"Missing required compressed CornerPoint array: {key}")

        igntid = np.asarray(data["IGNTID"], dtype=np.int64).ravel()
        igntjd = np.asarray(data["IGNTJD"], dtype=np.int64).ravel()
        igntkd = np.asarray(data["IGNTKD"], dtype=np.int64).ravel()
        igntnc = np.asarray(data["IGNTNC"], dtype=np.int64).ravel()
        total_cells = len(data["ICSTPS"])

        expected_cells = 0
        expected_nodes = 0
        for subgrid_idx, (ni, nj, nk) in enumerate(zip(igntid, igntjd, igntkd)):
            start = int(igntnc[subgrid_idx])
            end = int(igntnc[subgrid_idx + 1]) if subgrid_idx < len(igntid) - 1 else total_cells
            expected_cells += end - start
            expected_nodes += int((ni + 1) * (nj + 1) * (nk + 1))

        if expected_cells != total_cells:
            raise ValueError(
                f"Compressed corner sub-grid cell count {expected_cells} "
                f"does not match ICSTPS length {total_cells}"
            )
        if xcorn.size != expected_nodes:
            raise ValueError(
                "Compressed corner arrays do not match structured segment node count: "
                f"found {xcorn.size}, expected {expected_nodes}. "
                "This SR3 layout may require an explicit cell-to-corner connectivity table."
            )

        nodes = np.column_stack((xcorn, ycorn, zcorn))
        blocks = np.zeros((total_cells, 8), dtype=np.int64)

        node_offset = 0
        for subgrid_idx, (ni_raw, nj_raw, nk_raw) in enumerate(zip(igntid, igntjd, igntkd)):
            ni, nj, nk = int(ni_raw), int(nj_raw), int(nk_raw)
            cell_start = int(igntnc[subgrid_idx])
            cell_end = int(igntnc[subgrid_idx + 1]) if subgrid_idx < len(igntid) - 1 else total_cells
            segment_cells = ni * nj * nk
            if cell_end - cell_start != segment_cells:
                raise ValueError(
                    f"Compressed corner segment {subgrid_idx} has {cell_end - cell_start} cells, "
                    f"but dimensions imply {segment_cells}"
                )

            k_grid, j_grid, i_grid = np.meshgrid(
                np.arange(nk), np.arange(nj), np.arange(ni), indexing="ij"
            )
            ci, cj, ck = i_grid.ravel(), j_grid.ravel(), k_grid.ravel()

            def nid(i, j, k):
                return node_offset + ((k * (nj + 1) + j) * (ni + 1) + i)

            blocks[cell_start:cell_end] = np.column_stack(
                [
                    nid(ci, cj, ck),
                    nid(ci + 1, cj, ck),
                    nid(ci + 1, cj + 1, ck),
                    nid(ci, cj + 1, ck),
                    nid(ci, cj, ck + 1),
                    nid(ci + 1, cj, ck + 1),
                    nid(ci + 1, cj + 1, ck + 1),
                    nid(ci, cj + 1, ck + 1),
                ]
            )
            node_offset += (ni + 1) * (nj + 1) * (nk + 1)

        logger.info(f"Compressed corner coordinates converted: {total_cells} cells, {len(nodes)} nodes")
        return nodes, blocks

    def _coord_zcorn_to_nodes_blocks(self, data: Dict) -> Tuple[np.ndarray, np.ndarray]:
        """Convert COORD/ZCORN (Eclipse-style pillar grid) to NODES/BLOCKS (vectorized).

        COORD: 6 values per pillar (top xyz, bottom xyz), ``(NJ+1)*(NI+1)`` pillars.
        ZCORN: 8 Z-values per cell, ``NI*NJ*NK*8`` total.

        Each cell becomes 8 explicit corners; XY is interpolated along its pillars
        from the corner Z, and Z is negated for a Z-up coordinate system.
        """
        coord = data["COORD"]
        zcorn = data["ZCORN"]
        igntid = data.get("IGNTID", np.array([1]))
        igntjd = data.get("IGNTJD", np.array([1]))
        igntkd = data.get("IGNTKD", np.array([1]))
        ni, nj, nk = int(igntid[0]), int(igntjd[0]), int(igntkd[0])

        n_pillars = (ni + 1) * (nj + 1)
        if coord.size != n_pillars * 6:
            raise ValueError(
                f"COORD size {coord.size} doesn't match expected {n_pillars * 6} for {ni}x{nj} grid"
            )
        if zcorn.size != ni * nj * nk * 8:
            raise ValueError(f"ZCORN size {zcorn.size} doesn't match expected {ni * nj * nk * 8}")

        coord_reshaped = coord.reshape((nj + 1, ni + 1, 2, 3))
        zcorn_reshaped = zcorn.reshape((nk, 2, nj, 2, ni, 2))

        # Cell-indexed grids in C-order (k, j, i) with i fastest.
        kk, jj, ii = np.meshgrid(np.arange(nk), np.arange(nj), np.arange(ni), indexing="ij")
        kk, jj, ii = kk.ravel(), jj.ravel(), ii.ravel()
        total_cells = ni * nj * nk

        # The four pillars of each cell: (j,i), (j,i+1), (j+1,i), (j+1,i+1).
        pillar_ji = [(jj, ii), (jj, ii + 1), (jj + 1, ii), (jj + 1, ii + 1)]
        # Top Z index for each of the 4 pillar corners within zcorn_reshaped[k, t, j, b, i, r].
        z_top_sel = [(0, 0), (0, 1), (1, 0), (1, 1)]   # (back/front=b, left/right=r) for top
        nodes = np.empty((total_cells * 8, 3), dtype=float)

        # corner_coords order matches the original loop: index 2c=top, 2c+1=bot.
        corner_coords = [None] * 8
        for c, (b, r) in enumerate(z_top_sel):
            pj, pi = pillar_ji[c]
            pillar_top = coord_reshaped[pj, pi, 0]   # (N, 3)
            pillar_bot = coord_reshaped[pj, pi, 1]   # (N, 3)
            z_top = zcorn_reshaped[kk, 0, jj, b, ii, r]
            z_bot = zcorn_reshaped[kk, 1, jj, b, ii, r]

            dz_pillar = pillar_bot[:, 2] - pillar_top[:, 2]
            safe = np.abs(dz_pillar) > 1e-10
            with np.errstate(divide="ignore", invalid="ignore"):
                t_top = np.where(safe, (z_top - pillar_top[:, 2]) / dz_pillar, 0.0)
                t_bot = np.where(safe, (z_bot - pillar_top[:, 2]) / dz_pillar, 1.0)
            t_top = np.clip(t_top, 0.0, 1.0)
            t_bot = np.clip(t_bot, 0.0, 1.0)

            xy_top = pillar_top[:, :2] + t_top[:, None] * (pillar_bot[:, :2] - pillar_top[:, :2])
            xy_bot = pillar_top[:, :2] + t_bot[:, None] * (pillar_bot[:, :2] - pillar_top[:, :2])

            corner_coords[2 * c] = np.column_stack([xy_top, -z_top])
            corner_coords[2 * c + 1] = np.column_stack([xy_bot, -z_bot])

        # VTK hexahedron order (see original mapping).
        vtk_order = [1, 3, 7, 5, 0, 2, 6, 4]
        for slot, src in enumerate(vtk_order):
            nodes[slot::8] = corner_coords[src]

        blocks = np.arange(total_cells * 8, dtype=np.int64).reshape(total_cells, 8)
        logger.info(f"COORD/ZCORN converted: {total_cells} cells, {len(nodes)} nodes")
        return nodes, blocks
