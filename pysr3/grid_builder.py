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
    ) -> pv.UnstructuredGrid:
        """Build a grid of the given ``grid_type``.

        Args:
            grid_type: One of :func:`pysr3.grid.available_grid_types`
                (``"Cartesian"``, ``"CornerPoint"``, ``"Radial"``). Required.
            grid_mode:
                - ``"mixed"`` (default): unrefined level-0 blocks + all LGR leaves.
                - ``"refined"``: only LGR cells (level > 0).
                - ``"levelN"``: only cells at level N.
            include_inactive: Keep inactive cells (ICSTPS<=0 / IPSTAC==0).
            time_step: Time-step index whose GRID definition to use.
            merge_points: Merge coincident corners after building.
            merge_tolerance: Distance below which points are considered identical.

        Returns:
            ``pv.UnstructuredGrid`` with ``PropGlobalID``, ``GlobalCellID``,
            ``Level``, ``I/J/K`` and ``ParentI/J/K`` cell-data arrays.
        """
        if not grid_type:
            raise ValueError(
                f"grid_type must be specified, one of {available_grid_types()}"
            )

        logger.info(f"Building grid: type={grid_type}, mode={grid_mode}, step={time_step}")
        strategy = get_strategy(grid_type, self.indexer)
        data = self.indexer.get_grid_data(time_step)
        grid = strategy.build(
            data=data,
            time_step=time_step,
            grid_mode=grid_mode,
            include_inactive=include_inactive,
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
