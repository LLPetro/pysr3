"""sr3kit -- third-party reader and visualizer for CMG SR3 files.

Public API:
    SR3Indexer           -- HDF5 access / metadata / time-series (single source of truth)
    GridBuilder          -- raw SR3 arrays -> PyVista UnstructuredGrid
    DataMapper           -- SR3 property arrays -> grid cell data / DataFrame
    available_grid_types -- registered grid_type names for GridBuilder.build

Example:
    >>> from sr3kit import SR3Indexer, GridBuilder, DataMapper
    >>> with SR3Indexer("model.sr3") as ix:
    ...     grid = GridBuilder(ix).build(grid_type="CornerPoint")
    ...     df = DataMapper(ix).map_prop(grid, "PRES", 0)
"""

from .sr3_indexer import SR3Indexer
from .grid_builder import GridBuilder
from .data_mapper import DataMapper
from .grid import available_grid_types

__version__ = "0.1.0"

__all__ = [
    "SR3Indexer",
    "GridBuilder",
    "DataMapper",
    "available_grid_types",
    "__version__",
]
