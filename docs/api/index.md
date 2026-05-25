# API Reference

This reference is generated directly from the source docstrings and type hints,
so it always matches the installed version.

The public API is re-exported from the top-level package:

```python
from pysr3 import SR3Indexer, GridBuilder, DataMapper, available_grid_types
```

| Class | Layer | Responsibility |
|---|---|---|
| [`SR3Indexer`](indexer.md) | Access | Open the SR3/HDF5 file; index metadata, time steps, properties, and time series; return raw arrays. |
| [`GridBuilder`](grid-builder.md) | Geometry | Convert SR3 grid arrays into a PyVista `UnstructuredGrid`; build DFN surfaces. |
| [`DataMapper`](data-mapper.md) | Properties | Map SR3 property arrays onto grid cells / DataFrames, with optional LGR aggregation. |

The reusable, pure-NumPy [grid geometry helpers](grid-geometry.md) underpin the
grid strategies and are documented for contributors.

!!! note "Stability"
    Prefer the four public classes above and `available_grid_types()`.
    Underscore-prefixed members and the per-family strategy classes are
    internal and may change between releases.
