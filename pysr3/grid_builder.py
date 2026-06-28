"""Public grid-construction facade.

``GridBuilder`` is a thin dispatcher: it fetches the raw grid arrays from the
indexer once, hands them to the registered :class:`~pysr3.grid.base.GridStrategy`
for the requested ``grid_type``, then merges coincident points. The heavy
lifting lives in the :mod:`pysr3.grid` subpackage.

Backward-compatible entry points preserved from earlier versions:
``build``, ``build_dfn_segments``, ``build_dfn_units``.
"""

from __future__ import annotations

import logging
from typing import Optional

import pyvista as pv

from .grid import dfn
from .grid.base import available_grid_types, get_strategy
from .grid.type_detect import IGNTGT_CODE_MAP, detect_grid_type

# Import strategy modules for their registration side effects.
from .grid import cartesian as _cartesian  # noqa: F401
from .grid import corner_point as _corner_point  # noqa: F401
from .grid import radial as _radial  # noqa: F401
from .sr3_indexer import SR3Indexer

logger = logging.getLogger(__name__)


class GridBuilder:
    """Convert raw SR3 arrays into PyVista ``UnstructuredGrid`` objects."""

    def __init__(self, indexer: SR3Indexer):
        self.indexer = indexer

    def build(
        self,
        grid_type: Optional[str] = None,
        grid_mode: str = "mixed",
        include_inactive: bool = False,
        time_step: int = 0,
        merge_points: bool = True,
        merge_tolerance: float = 1e-10,
        keep_refined_parents: bool = True,
    ) -> pv.UnstructuredGrid:
        """Build a grid of the given ``grid_type``.

        Args:
            grid_type: One of :func:`pysr3.grid.available_grid_types`
                (``"Cartesian"``, ``"CornerPoint"``, ``"Radial"``). Default
                ``None`` triggers auto-detection from
                ``/SpatialProperties/<step>/GRID/IGNTGT[0]``; pass explicitly
                to override the detection (a warning is logged on mismatch).
            grid_mode:
                - ``"mixed"`` (default): unrefined level-0 blocks + all LGR leaves.
                - ``"refined"``: only LGR cells (level > 0).
                - ``"levelN"``: only cells at level N.
            include_inactive: Keep inactive cells (ICSTPS<=0 / IPSTAC==0).
            time_step: Time-step index whose GRID definition to use.
            merge_points: Merge coincident corners after building.
            merge_tolerance: Distance below which points are considered identical.
            keep_refined_parents: When ``include_inactive=False`` (default),
                still keep refined-parent cells in the grid (cells flagged
                ``IPSTAC=0`` solely because LGR children replace them). These
                cells are required as landing sites for
                ``DataMapper.map_prop(aggregate=True)``. Set ``False`` to drop
                them too (legacy behavior; can cause silent no-op aggregation).

        Returns:
            ``pv.UnstructuredGrid`` with ``PropGlobalID``, ``GlobalCellID``,
            ``Level``, ``I/J/K`` and ``ParentI/J/K`` cell-data arrays.

        Raises:
            ValueError: when ``grid_type`` is ``None`` and the file's IGNTGT is
                missing or carries an unknown code (auto-detection failed); pass
                ``grid_type`` explicitly to recover.
        """
        # Fetch the grid dict once and reuse it for both auto-detection and
        # strategy dispatch (single HDF5 read).
        data = self.indexer.get_grid_data(self.indexer.get_nearest_grid_time_step(time_step))
        detected = detect_grid_type(data)

        if grid_type is None:
            if detected is None:
                igntgt_raw = data.get("IGNTGT")
                igntgt_repr = "absent" if igntgt_raw is None else repr(list(igntgt_raw)[:8])
                file_path = getattr(self.indexer, "file_path", "<unknown file>")
                raise ValueError(
                    f"grid_type could not be auto-detected for {file_path!r}: "
                    f"IGNTGT={igntgt_repr}. Pass grid_type=... explicitly. "
                    f"Known IGNTGT codes: {sorted(IGNTGT_CODE_MAP)}; "
                    f"available strategies: {available_grid_types()}."
                )
            grid_type = detected
            logger.info(f"Auto-detected grid_type={grid_type!r} from IGNTGT")
        elif detected is not None and detected != grid_type:
            file_path = getattr(self.indexer, "file_path", "<unknown file>")
            logger.warning(
                f"Supplied grid_type={grid_type!r} contradicts IGNTGT[0] "
                f"({detected!r}) in {file_path!r}; honoring the user value"
            )

        logger.info(f"Building grid: grid_type={grid_type}, grid_mode={grid_mode}, time_step={time_step}")
        strategy = get_strategy(grid_type, self.indexer)
        grid = strategy.build(
            data=data,
            grid_mode=grid_mode,
            include_inactive=include_inactive,
            keep_refined_parents=keep_refined_parents,
        )

        if merge_points and grid.n_points > 0:
            n_before = grid.n_points
            grid = grid.clean(tolerance=merge_tolerance, remove_unused_points=True)
            reduction = (1 - grid.n_points / n_before) * 100
            logger.info(
                f"Merged duplicate points: {n_before} -> {grid.n_points} ({reduction:.1f}% reduction)"
            )
        return grid

    def build_dfn_segments(
        self,
        time_step: int = 0,
        include_inactive: bool = False,
        merge_points: bool = False,
        merge_tolerance: float = 1e-10,
    ) -> pv.UnstructuredGrid:
        """Build embedded DFN segment surfaces (see :mod:`pysr3.grid.dfn`)."""
        return dfn.build_dfn_segments(
            self.indexer,
            time_step=time_step,
            include_inactive=include_inactive,
            merge_points=merge_points,
            merge_tolerance=merge_tolerance,
        )

    def build_dfn_units(
        self,
        time_step: int = 0,
        merge_points: bool = False,
        merge_tolerance: float = 1e-10,
    ) -> pv.UnstructuredGrid:
        """Build original DFU surfaces (see :mod:`pysr3.grid.dfn`)."""
        return dfn.build_dfn_units(
            self.indexer,
            time_step=time_step,
            merge_points=merge_points,
            merge_tolerance=merge_tolerance,
        )
