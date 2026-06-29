"""Grid construction subpackage.

Splits the former monolithic ``GridBuilder`` into:

- :mod:`sr3kit.grid.geometry` -- reusable, pure-numpy geometry helpers.
- :mod:`sr3kit.grid.base`     -- the ``GridStrategy`` ABC and strategy registry.
- :mod:`sr3kit.grid.cartesian`, ``corner_point``, ``radial`` -- one strategy per
  SR3 grid family.
- :mod:`sr3kit.grid.dfn`      -- embedded DFN unit/segment surface builders.

The public entry point remains :class:`sr3kit.grid_builder.GridBuilder`, which is a
thin facade that dispatches to these strategies.
"""

from .base import GridStrategy, register_strategy, get_strategy, available_grid_types
from .type_detect import IGNTGT_CODE_MAP, IGNTGT_INHERIT_CODE, detect_grid_type

__all__ = [
    "GridStrategy",
    "register_strategy",
    "get_strategy",
    "available_grid_types",
    "detect_grid_type",
    "IGNTGT_CODE_MAP",
    "IGNTGT_INHERIT_CODE",
]
