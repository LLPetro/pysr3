# Developer Guide

This guide is for **contributors and maintainers**: how sr3kit is structured, the
data model that ties the layers together, and how to extend and validate it.

If you just want to *use* sr3kit, start with the [User Guide](../user-guide/index.md).

<div class="grid cards" markdown>

-   :material-sitemap: **[Architecture](architecture.md)**

    The three layers, module layout, and data flow.

-   :material-database: **[Data model & types](data-model.md)**

    Cell-data arrays, the `PropGlobalID` / `GlobalCellID` keys, and the SR3 array glossary.

-   :material-relation-many-to-many: **[Component relationships](components.md)**

    How `SR3Indexer`, `GridBuilder`, strategies, and `DataMapper` interact.

-   :material-cog: **[Grid strategy internals](grid-internals.md)**

    The strategy registry, shared geometry helpers, and per-family algorithms.

-   :material-test-tube: **[Testing & validation](testing.md)**

    The unit suite, the real-SR3 fixtures, and the golden behavior harness.

-   :material-source-pull: **[Contributing](contributing.md)**

    Dev setup, conventions, and how to add a new grid type.

</div>

## Source layout

```text
sr3kit/
├── __init__.py          # public API: SR3Indexer, GridBuilder, DataMapper, available_grid_types
├── sr3_indexer.py       # access layer
├── grid_builder.py      # geometry facade (dispatches to strategies)
├── data_mapper.py       # property layer
└── grid/
    ├── geometry.py      # reusable pure-NumPy helpers
    ├── base.py          # GridStrategy ABC + registry
    ├── cartesian.py     # Cartesian / VARI strategy
    ├── corner_point.py  # corner-point strategy (3 encodings + fallback)
    ├── radial.py        # radial strategy (adaptive subdivision)
    └── dfn.py           # embedded DFN unit/segment builders
```
