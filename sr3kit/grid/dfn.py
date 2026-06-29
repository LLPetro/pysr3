"""Embedded DFN (discrete fracture network) surface builders.

CMG DFN is *not* an LGR: SR3 stores DFU definitions and the embedded
segment/matrix intersections separately from the matrix grid. These build
functions emit 2D quadrilateral surfaces that carry ``PropGlobalID`` values
mapping to ordinary spatial properties (PRES/SO/SW...).
"""

from __future__ import annotations

import logging
from typing import Dict

import numpy as np
import pyvista as pv

from .geometry import polygon_cells, subgrid_ijk

logger = logging.getLogger(__name__)


def build_dfn_segments(
    indexer,
    time_step: int = 0,
    include_inactive: bool = False,
    merge_points: bool = False,
    merge_tolerance: float = 1e-10,
) -> pv.UnstructuredGrid:
    """Build embedded DFN segment control volumes as 2D quadrilateral surfaces."""
    data = indexer.get_grid_data(time_step)
    required = ("SGCORX", "SGCORY", "SGCORZ", "ISGTPS")
    if not all(key in data for key in required):
        return pv.UnstructuredGrid()

    x = np.asarray(data["SGCORX"], dtype=float).ravel()
    y = np.asarray(data["SGCORY"], dtype=float).ravel()
    z = np.asarray(data["SGCORZ"], dtype=float).ravel()
    prop_slots = np.asarray(data["ISGTPS"], dtype=np.int64).ravel()

    if not (x.size == y.size == z.size):
        raise ValueError("DFN segment coordinate arrays SGCORX/SGCORY/SGCORZ must have the same length")
    if x.size % 4 != 0:
        raise ValueError(f"DFN segment coordinates must contain 4 corners per segment, got {x.size}")

    n_segments = x.size // 4
    if prop_slots.size != n_segments:
        raise ValueError(f"ISGTPS length {prop_slots.size} does not match DFN segment count {n_segments}")

    prop_ids = prop_slots.astype(np.int32) - 1
    segment_ids = np.arange(n_segments, dtype=np.int32)
    keep_mask = prop_slots > 0
    if not include_inactive:
        ipstac = data.get("IPSTAC")
        if ipstac is not None:
            ipstac = np.asarray(ipstac).ravel()
            in_bounds = (prop_ids >= 0) & (prop_ids < ipstac.size)
            keep_mask &= in_bounds & (ipstac[prop_ids] != 0)

    if not np.all(keep_mask):
        xyz = np.column_stack((x, y, z)).reshape(n_segments, 4, 3)[keep_mask]
        prop_ids = prop_ids[keep_mask]
        segment_ids = segment_ids[keep_mask]
        n_segments = int(keep_mask.sum())
        if n_segments == 0:
            return pv.UnstructuredGrid()
        points = xyz.reshape(n_segments * 4, 3)
    else:
        points = np.column_stack((x, y, z))

    cells, cell_types = polygon_cells(n_segments, 4, pv.CellType.QUAD)
    grid = pv.UnstructuredGrid(cells, cell_types, points)

    grid.cell_data["PropGlobalID"] = prop_ids
    grid.cell_data["DFNSegmentID"] = segment_ids

    if "ISGTDU" in data:
        isgtdu = np.asarray(data["ISGTDU"], dtype=np.int32).ravel()
        grid.cell_data["DFUIndex"] = isgtdu[segment_ids] - 1
    if "IPSTCS" in data:
        ipstcs = np.asarray(data["IPSTCS"], dtype=np.int64).ravel()
        host = np.full(n_segments, -1, dtype=np.int32)
        valid = (prop_ids >= 0) & (prop_ids < ipstcs.size)
        host[valid] = ipstcs[prop_ids[valid]].astype(np.int32) - 1
        grid.cell_data["HostGlobalCellID"] = host
        _attach_host_ijk(grid, host, data)
    if "IPSTSG" in data:
        ipstsg = np.asarray(data["IPSTSG"], dtype=np.int64).ravel()
        segment_in_host = np.full(n_segments, -1, dtype=np.int32)
        valid = (prop_ids >= 0) & (prop_ids < ipstsg.size)
        segment_in_host[valid] = ipstsg[prop_ids[valid]].astype(np.int32)
        grid.cell_data["SegmentInHost"] = segment_in_host

    if merge_points and grid.n_points > 0:
        grid = grid.clean(tolerance=merge_tolerance, remove_unused_points=True)
    return grid


def build_dfn_units(
    indexer,
    time_step: int = 0,
    merge_points: bool = False,
    merge_tolerance: float = 1e-10,
) -> pv.UnstructuredGrid:
    """Build the original DFU quadrilateral surfaces (pre-intersection)."""
    data = indexer.get_grid_data(time_step)
    required = ("DFUCOX", "DFUCOY", "DFUCOZ", "DFUTNL")
    if not all(key in data for key in required):
        return pv.UnstructuredGrid()

    x = np.asarray(data["DFUCOX"], dtype=float).ravel()
    y = np.asarray(data["DFUCOY"], dtype=float).ravel()
    z = np.asarray(data["DFUCOZ"], dtype=float).ravel()
    node_ends = np.asarray(data["DFUTNL"], dtype=np.int64).ravel()

    if not (x.size == y.size == z.size):
        raise ValueError("DFU coordinate arrays DFUCOX/DFUCOY/DFUCOZ must have the same length")
    if x.size % 4 != 0:
        raise ValueError(f"DFU coordinates must contain 4 corners per DFU, got {x.size}")

    n_units = x.size // 4
    if node_ends.size != n_units:
        raise ValueError(f"DFUTNL length {node_ends.size} does not match DFU count {n_units}")

    points = np.column_stack((x, y, z))
    cells, cell_types = polygon_cells(n_units, 4, pv.CellType.QUAD)
    grid = pv.UnstructuredGrid(cells, cell_types, points)

    grid.cell_data["DFUIndex"] = np.arange(n_units, dtype=np.int32)
    grid.cell_data["DFUNodeEnd"] = node_ends.astype(np.int32)
    if "IUTDF" in data:
        grid.cell_data["DFNIndex"] = np.asarray(data["IUTDF"], dtype=np.int32).ravel()[:n_units] - 1

    aperture = indexer.get_property_data("DFUAPT", time_step)
    if aperture is not None and len(aperture) >= n_units:
        grid.cell_data["DFUAPT"] = np.asarray(aperture[:n_units], dtype=np.float32)

    permeability = indexer.get_property_data("DFUPERM", time_step)
    if permeability is not None and len(permeability) >= n_units:
        grid.cell_data["DFUPERM"] = np.asarray(permeability[:n_units], dtype=np.float32)

    if merge_points and grid.n_points > 0:
        grid = grid.clean(tolerance=merge_tolerance, remove_unused_points=True)
    return grid


def _attach_host_ijk(grid: pv.UnstructuredGrid, host_ids: np.ndarray, data: Dict) -> None:
    """Attach fundamental-grid host I/J/K indices for DFN segment surfaces."""
    n = len(host_ids)
    host_i = np.full(n, -1, dtype=np.int32)
    host_j = np.full(n, -1, dtype=np.int32)
    host_k = np.full(n, -1, dtype=np.int32)

    if not all(key in data for key in ("IGNTID", "IGNTJD", "IGNTKD", "IGNTNC")):
        grid.cell_data["HostI"] = host_i
        grid.cell_data["HostJ"] = host_j
        grid.cell_data["HostK"] = host_k
        return

    total_cells = len(np.asarray(data.get("ICSTPS", [])))
    full_i, full_j, full_k = subgrid_ijk(
        data["IGNTID"], data["IGNTJD"], data["IGNTKD"], data["IGNTNC"], total_cells
    )

    valid = (host_ids >= 0) & (host_ids < total_cells)
    host_i[valid] = full_i[host_ids[valid]]
    host_j[valid] = full_j[host_ids[valid]]
    host_k[valid] = full_k[host_ids[valid]]
    grid.cell_data["HostI"] = host_i
    grid.cell_data["HostJ"] = host_j
    grid.cell_data["HostK"] = host_k
