# Contributing

## Dev setup

```bash
git clone <repository-url>
cd pysr3
pip install -e ".[dev]"     # runtime + pytest
pytest                       # should report 28 passed
```

To work on the docs:

```bash
pip install -e ".[docs]"
mkdocs serve                 # live preview at http://127.0.0.1:8000
```

## Conventions

- **Naming:** before introducing a new identifier or parameter name, check
  [Naming & glossary](naming.md) and prefer the canonical name there. New
  concepts should extend that page rather than ship a one-off variant.
- **Language:** code, comments, and docstrings are **English**. Docstrings use
  **Google style** (`Args:`, `Returns:`, `Raises:`) so mkdocstrings renders them
  cleanly into the [API reference](../api/index.md).
- **Types:** annotate public signatures; the API pages show them.
- **Geometry math is vectorized NumPy.** Avoid per-cell Python loops on hot
  paths; put reusable math in `grid/geometry.py` rather than duplicating it in a
  strategy.
- **HDF5 access stays in `SR3Indexer`.** Strategies and `DataMapper` receive
  plain arrays.
- **Keep the facade thin.** New geometry belongs in a strategy or a helper, not
  in `GridBuilder`.

## Adding a grid type { #adding-a-grid-type }

The strategy registry makes this additive — no edits to `GridBuilder`:

```python
# pysr3/grid/my_family.py
import pyvista as pv
from .base import GridStrategy, register_strategy
from .geometry import active_cell_mask, infer_levels  # reuse helpers

@register_strategy("MyFamily")
class MyFamilyStrategy(GridStrategy):
    def build(self, data, time_step, grid_mode, include_inactive):
        # 1. read arrays from `data`
        # 2. assemble points/cells (prefer geometry helpers)
        # 3. stamp PropGlobalID, GlobalCellID, Level, I/J/K, ParentI/J/K
        grid = pv.UnstructuredGrid(...)
        return grid
```

Then import it for its registration side effect in `pysr3/grid_builder.py`:

```python
from .grid import my_family as _my_family  # noqa: F401
```

`available_grid_types()` will now include `"MyFamily"`. Add it to
`pyproject.toml`'s package list if it lives in a new subpackage, and document it
under [Grid types](../user-guide/concepts/grid-types.md).

## Validating a change

1. `pytest` — must stay green (28 tests).
2. For grid/mapping changes, run the
   [golden harness and real-SR3 pipeline](testing.md) and confirm output is
   unchanged (or update fixtures intentionally).
3. `mkdocs build --strict` — docs must build with no warnings.

## Pull requests

- Keep diffs focused; separate mechanical changes (renames) from behavioral ones.
- Note in the PR whether output is intended to be bit-identical, and how you
  verified it.
