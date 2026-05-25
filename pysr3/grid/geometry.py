"""Reusable, pure-numpy geometry helpers shared by every grid strategy.

These functions intentionally take plain numpy arrays (and the raw grid-data
dict from ``SR3Indexer.get_grid_data``) rather than the indexer or PyVista
objects, so they are trivial to unit-test in isolation and can be reused by
``GridBuilder`` strategies and ``DataMapper`` alike.
"""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

import numpy as np
import pyvista as pv

__all__ = [
    "infer_levels",
    "refined_parent_ids",
    "grid_mode_keep_mask",
    "active_cell_mask",
    "parse_kdir",
    "hexahedra_from_corners",
    "polygon_cells",
    "segment_ijk",
    "compute_parent_ijk",
]


# --------------------------------------------------------------------------- #
# LGR level inference
# --------------------------------------------------------------------------- #
def infer_levels(icstpb: np.ndarray, igntnc: np.ndarray) -> np.ndarray:
    """Infer LGR levels from parent pointers (``ICSTPB``) and segment offsets.

    Segment 0 is always level 0; every other cell's level is its parent level
    plus one, resolved by vectorized iteration.

    Raises:
        RuntimeError: if a round resolves no new cells while some remain
            unresolved -- a circular reference or an invalid ``ICSTPB``.
    """
    icstpb = np.asarray(icstpb)
    igntnc = np.asarray(igntnc)
    total_cells = len(icstpb)

    level = np.full(total_cells, -1, dtype=np.int16)
    seg0_end = int(igntnc[1]) if len(igntnc) > 1 else total_cells
    level[0:seg0_end] = 0

    parents_0based = icstpb - 1
    unresolved = np.arange(seg0_end, total_cells)

    while unresolved.size:
        prev_count = unresolved.size
        current_parents = parents_0based[unresolved]

        # Guard against invalid parent pointers (e.g. ICSTPB == 0 -> -1) so we
        # never silently wrap around the level array.
        valid = (current_parents >= 0) & (current_parents < total_cells)
        parent_levels = np.full(unresolved.size, -1, dtype=np.int16)
        parent_levels[valid] = level[current_parents[valid]]

        resolved = parent_levels >= 0
        level[unresolved[resolved]] = parent_levels[resolved] + 1
        unresolved = unresolved[~resolved]

        if unresolved.size == prev_count:
            raise RuntimeError(
                f"Level inference deadlock: {unresolved.size} cells have unresolved "
                "or invalid parents (possible circular reference or bad ICSTPB)."
            )

    return level


def refined_parent_ids(icstpb: np.ndarray, igntnc: np.ndarray) -> np.ndarray:
    """Return 0-based IDs of parent cells that LGR children have replaced."""
    icstpb = np.asarray(icstpb)
    igntnc = np.asarray(igntnc)
    if len(igntnc) <= 1:
        return np.empty(0, dtype=np.int64)
    lgr_start = int(igntnc[1])
    parents = np.unique(icstpb[lgr_start:])
    parents = parents[parents > 0] - 1
    return parents.astype(np.int64)


def grid_mode_keep_mask(
    grid_mode: str,
    level: np.ndarray,
    icstpb: np.ndarray | None,
    igntnc: np.ndarray | None,
) -> np.ndarray:
    """Boolean keep-mask for the requested display mode (geometry/level only).

    Modes:
        - ``mixed``  : drop parents that were replaced by LGR children.
        - ``refined``: keep only refined cells (level > 0).
        - ``levelN`` : keep only cells at level ``N``.

    The active-cell filter is applied separately by the caller.
    """
    total = len(level)
    keep = np.ones(total, dtype=bool)

    if grid_mode == "mixed":
        if icstpb is not None and igntnc is not None:
            keep[refined_parent_ids(icstpb, igntnc)] = False
    elif grid_mode == "refined":
        keep &= level > 0
    elif grid_mode.startswith("level"):
        try:
            target = int(grid_mode[len("level"):])
            keep &= level == target
        except ValueError:
            pass
    return keep


def active_cell_mask(icstps: np.ndarray, data: Dict) -> np.ndarray:
    """Return active matrix/grid cells.

    ``ICSTPS`` only tells whether a geometry cell points to a property slot.
    DFN cases can keep property slots for null-layer host cells while
    ``IPSTAC`` marks them inactive. Respecting ``IPSTAC`` keeps the matrix grid
    consistent with CMG Results' Active Blocks count.
    """
    icstps = np.asarray(icstps, dtype=np.int64).ravel()
    mask = icstps > 0

    ipstac = data.get("IPSTAC")
    if ipstac is None:
        return mask

    ipstac = np.asarray(ipstac).ravel()
    prop_ids = icstps - 1
    in_bounds = (prop_ids >= 0) & (prop_ids < ipstac.size)
    active = np.zeros_like(mask, dtype=bool)
    active[in_bounds] = ipstac[prop_ids[in_bounds]] != 0
    return mask & active


def parse_kdir(data: Dict, default: str = "DOWN") -> str:
    """Decode the ``KDIR`` grid attribute to an upper-case string."""
    raw = data.get("KDIR", default)
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="ignore").strip().upper()
    return str(raw).strip().upper()


# --------------------------------------------------------------------------- #
# VTK cell assembly
# --------------------------------------------------------------------------- #
def hexahedra_from_corners(
    corners: Sequence[np.ndarray],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build an exploded hexahedron mesh from 8 corner-coordinate arrays.

    Args:
        corners: sequence of exactly 8 ``(N, 3)`` arrays, in VTK hexahedron
            node order (bottom face 0-3, top face 4-7).

    Returns:
        ``(cells, cell_types, points)`` ready for ``pv.UnstructuredGrid``.
    """
    if len(corners) != 8:
        raise ValueError(f"hexahedra need 8 corner arrays, got {len(corners)}")
    n = len(corners[0])
    points = np.zeros((n * 8, 3), dtype=float)
    for c in range(8):
        points[c::8] = corners[c]

    base = np.arange(0, n * 8, 8)
    cells = np.zeros((n, 9), dtype=np.int64)
    cells[:, 0] = 8
    for c in range(8):
        cells[:, c + 1] = base + c

    cell_types = np.full(n, pv.CellType.HEXAHEDRON, dtype=np.uint8)
    return cells.ravel(), cell_types, points


def polygon_cells(
    n_cells: int,
    n_verts: int,
    cell_type,
) -> Tuple[np.ndarray, np.ndarray]:
    """Build a VTK connectivity/type pair for ``n_cells`` polygons.

    Assumes points are laid out consecutively, ``n_verts`` per cell
    (vertex ``v`` of cell ``c`` lives at point index ``c * n_verts + v``).
    """
    cells = np.zeros((n_cells, n_verts + 1), dtype=np.int64)
    cells[:, 0] = n_verts
    cells[:, 1:] = np.arange(n_cells * n_verts, dtype=np.int64).reshape(n_cells, n_verts)
    cell_types = np.full(n_cells, cell_type, dtype=np.uint8)
    return cells.ravel(), cell_types


# --------------------------------------------------------------------------- #
# Structured I/J/K indexing
# --------------------------------------------------------------------------- #
def segment_ijk(
    igntid: np.ndarray,
    igntjd: np.ndarray,
    igntkd: np.ndarray,
    igntnc: np.ndarray,
    total_cells: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate per-cell local I/J/K indices for all structured segments.

    Cells are assumed laid out C-order ``(K, J, I)`` within each segment, with
    I varying fastest -- matching CMG's SR3 segment layout.
    """
    i_arr = np.full(total_cells, -1, dtype=np.int32)
    j_arr = np.full(total_cells, -1, dtype=np.int32)
    k_arr = np.full(total_cells, -1, dtype=np.int32)

    igntid = np.asarray(igntid)
    igntjd = np.asarray(igntjd)
    igntkd = np.asarray(igntkd)
    igntnc = np.asarray(igntnc)
    n_seg = len(igntid)

    for seg in range(n_seg):
        start = int(igntnc[seg])
        end = int(igntnc[seg + 1]) if seg < n_seg - 1 else total_cells
        if end <= start:
            continue
        ni, nj, nk = int(igntid[seg]), int(igntjd[seg]), int(igntkd[seg])
        k_grid, j_grid, i_grid = np.meshgrid(
            np.arange(nk), np.arange(nj), np.arange(ni), indexing="ij"
        )
        count = min(end - start, i_grid.size)
        i_arr[start:start + count] = i_grid.ravel()[:count]
        j_arr[start:start + count] = j_grid.ravel()[:count]
        k_arr[start:start + count] = k_grid.ravel()[:count]

    return i_arr, j_arr, k_arr


def compute_parent_ijk(
    icstpb: np.ndarray,
    level: np.ndarray,
    i_arr: np.ndarray,
    j_arr: np.ndarray,
    k_arr: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map each refined cell to its parent's I/J/K (level-0 cells stay -1)."""
    icstpb = np.asarray(icstpb)
    total = len(icstpb)
    parent_i = np.full(total, -1, dtype=np.int32)
    parent_j = np.full(total, -1, dtype=np.int32)
    parent_k = np.full(total, -1, dtype=np.int32)

    mask = (icstpb > 0) & (level > 0)
    parents = (icstpb[mask] - 1).clip(0, total - 1)
    parent_i[mask] = i_arr[parents]
    parent_j[mask] = j_arr[parents]
    parent_k[mask] = k_arr[parents]
    return parent_i, parent_j, parent_k
