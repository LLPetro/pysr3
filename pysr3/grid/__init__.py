"""Grid construction subpackage.

Splits the former monolithic ``GridBuilder`` into:

- :mod:`pysr3.grid.geometry` -- reusable, pure-numpy geometry helpers.
- :mod:`pysr3.grid.base`     -- the ``GridStrategy`` ABC and strategy registry.
- :mod:`pysr3.grid.cartesian`, ``corner_point``, ``radial`` -- one strategy per
  SR3 grid family.
- :mod:`pysr3.grid.dfn`      -- embedded DFN unit/segment surface builders.

The public entry point remains :class:`pysr3.grid_builder.GridBuilder`, which is a
thin facade that dispatches to these strategies.
"""

from .base import GridStrategy, register_strategy, get_strategy, available_grid_types

__all__ = [
    "GridStrategy",
    "register_strategy",
    "get_strategy",
    "available_grid_types",
]
