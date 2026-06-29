# GridBuilder

The geometry layer: a thin facade that dispatches to a registered grid strategy
and returns a PyVista `UnstructuredGrid`. See
[Grid strategy internals](../developer-guide/grid-internals.md) for how the
strategies work.

::: sr3kit.grid_builder.GridBuilder
