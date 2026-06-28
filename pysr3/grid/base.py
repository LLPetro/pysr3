"""Grid strategy base class and registry.

Each SR3 grid family is implemented as a :class:`GridStrategy` subclass and
registered under its public ``grid_type`` name. Adding a new grid type is
therefore additive: write a strategy, decorate it with
:func:`register_strategy`, and the :class:`pysr3.grid_builder.GridBuilder` facade
picks it up automatically.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Type

import pyvista as pv

_REGISTRY: Dict[str, Type["GridStrategy"]] = {}


def register_strategy(name: str) -> Callable[[Type["GridStrategy"]], Type["GridStrategy"]]:
    """Class decorator registering a strategy under a public ``grid_type``."""

    def _decorator(cls: Type["GridStrategy"]) -> Type["GridStrategy"]:
        cls.grid_type = name
        _REGISTRY[name] = cls
        return cls

    return _decorator


def get_strategy(name: str, indexer) -> "GridStrategy":
    """Instantiate the strategy registered under ``name``."""
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unsupported grid_type: {name!r}. Available: {available_grid_types()}"
        )
    return cls(indexer)


def available_grid_types() -> List[str]:
    """Return the registered grid-type names."""
    return sorted(_REGISTRY)


class GridStrategy(ABC):
    """Pure transformation from raw SR3 grid arrays to a PyVista grid.

    Strategies never re-read the file: the facade fetches the grid-data dict
    once via ``SR3Indexer.get_grid_data`` and passes it to :meth:`build`.
    """

    grid_type: str = ""

    def __init__(self, indexer):
        self.indexer = indexer

    @abstractmethod
    def build(
        self,
        data: Dict,
        grid_mode: str,
        include_inactive: bool,
        keep_refined_parents: bool = True,
    ) -> pv.UnstructuredGrid:
        """Return an ``UnstructuredGrid`` with standard cell-data arrays.

        Implementations must stamp ``PropGlobalID`` and ``GlobalCellID`` so
        ``DataMapper`` can attach property values. The strategy receives the
        already-fetched ``data`` dict (see ``SR3Indexer.get_grid_data``); the
        facade resolves the time-step before calling, so strategies never need
        to re-read the file.

        ``keep_refined_parents`` (default ``True``): when ``include_inactive`` is
        ``False``, refined-parent cells (flagged ``IPSTAC=0`` solely because
        their LGR children replace them) are still kept in the grid, so they
        can serve as landing sites for bottom-up aggregation in ``DataMapper``.
        """
        raise NotImplementedError
