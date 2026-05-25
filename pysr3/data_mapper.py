import numpy as np
import pyvista as pv
import pandas as pd
from typing import Union, List, Dict, Optional
import logging
from .sr3_indexer import SR3Indexer
from .grid.geometry import infer_levels

logger = logging.getLogger(__name__)


class DataMapper:
    """Map SR3 property arrays onto a PyVista grid.

    Two mapping modes are supported:

    1. **Direct** (default): ``PropGlobalID -> prop_data``; simple and fast.
    2. **Aggregated**: bottom-up LGR aggregation that rolls child-cell values
       up into their parent cells.

    Key concepts:

    - ``PropGlobalID = ICSTPS - 1`` indexes directly into ``prop_data``.
    - ``GlobalCellID`` is the cell's 0-based linear index within the SR3 file.
    - Inactive cells have ``PropGlobalID == -1`` and map to ``NaN``.
    """

    def __init__(self, indexer: SR3Indexer):
        self.indexer = indexer
        self._geo_cache: Dict[int, Dict] = {}  # cache of per-step geometry info

    def map_prop(self,
                 grid: pv.UnstructuredGrid,
                 keywords: Union[str, List[str]],
                 times: Union[int, List[int]],
                 aggregate: bool = False,
                 agg_method: str = 'mean') -> pd.DataFrame:
        """Map one or more properties and return a fully labelled DataFrame.

        Args:
            grid: Target PyVista grid (must carry the ``PropGlobalID`` array).
            keywords: Property keyword(s), e.g. ``'PRES'`` or ``['PRES', 'SO']``.
            times: Time-step index or indices, e.g. ``0`` or ``[0, 1]``.
            aggregate: Whether to perform LGR aggregation. ``False`` (default)
                maps directly and suits ``mixed`` grids; ``True`` rolls child
                values up into parents and suits grids that contain parent cells
                such as ``level0``.
            agg_method: Aggregation method: ``'mean'``, ``'sum'``, ``'min'`` or
                ``'max'``.

        Returns:
            A DataFrame with one float column per ``(keyword, time)`` and one
            row per grid cell (index ``0 .. n_cells-1``). Columns use a 6-level
            MultiIndex: ``(Keyword, LongName, Unit, Time, TimeIndex, TimeUnit)``.
        """
        # 1. Normalise inputs
        if isinstance(keywords, str):
            keywords = [keywords]
        if isinstance(times, int):
            times = [times]

        # 2. Resolve the time unit
        time_unit = 'day'
        if hasattr(self.indexer, 'units'):
            for u in self.indexer.units.values():
                if isinstance(u, dict) and u.get('dimensionality', '').strip().lower() == 'time':
                    time_unit = u.get('internal_unit') or 'day'
                    break

        # 3. Prepare the data container
        data_dict = {}

        # 4. Iterate over time steps and properties
        for time_step in times:
            try:
                time_value = self.indexer.time_to_offset(time_step)
            except (AttributeError, KeyError):
                time_value = float(time_step)

            for kw in keywords:
                # Resolve property metadata
                try:
                    prop_info = self.indexer.get_property_info(kw)
                except AttributeError:
                    prop_info = {}

                long_name = prop_info.get('display_name', kw)
                unit = prop_info.get('unit', '')

                # Map the property
                try:
                    mapped_values = self._map_single_property(
                        grid, kw, time_step, aggregate, agg_method
                    )
                except Exception as e:
                    logger.error(f"Failed to map property '{kw}' at step {time_step}: {e}")
                    mapped_values = np.full(grid.n_cells, np.nan)

                # Build the column key
                col_key = (kw, long_name, unit, time_value, time_step, time_unit)
                data_dict[col_key] = mapped_values

        # 5. Assemble the DataFrame
        if not data_dict:
            return pd.DataFrame()

        df = pd.DataFrame(data_dict)
        df.columns.names = ['Keyword', 'LongName', 'Unit', 'Time', 'TimeIndex', 'TimeUnit']

        return df

    def _map_single_property(self,
                             grid: pv.UnstructuredGrid,
                             prop_name: str,
                             time_step: int,
                             aggregate: bool,
                             agg_method: str) -> np.ndarray:
        """Map a single property, dispatching to direct or aggregated mapping."""
        if not aggregate:
            return self._direct_map(grid, prop_name, time_step)
        else:
            return self._aggregated_map(grid, prop_name, time_step, agg_method)

    def _direct_map(self,
                    grid: pv.UnstructuredGrid,
                    prop_name: str,
                    time_step: int) -> np.ndarray:
        """Direct mapping: ``PropGlobalID -> prop_data``.

        Suited to ``mixed`` grids, which contain only leaf cells and so need no
        aggregation.
        """
        # 1. Fetch the raw property array
        prop_data = self.indexer.get_property_data(prop_name, time_step)
        if prop_data is None:
            logger.warning(f"Property '{prop_name}' not found at step {time_step}.")
            return np.full(grid.n_cells, np.nan)

        # 2. Read PropGlobalID
        if 'PropGlobalID' not in grid.cell_data:
            raise ValueError("Grid missing 'PropGlobalID' array. Cannot map data.")

        prop_ids = grid.cell_data['PropGlobalID']
        n_props = len(prop_data)

        # 3. Map directly, leaving out-of-range ids as NaN
        valid_mask = (prop_ids >= 0) & (prop_ids < n_props)
        mapped_values = np.full(grid.n_cells, np.nan, dtype=np.float32)
        mapped_values[valid_mask] = prop_data[prop_ids[valid_mask]]

        n_invalid = np.sum(~valid_mask)
        if n_invalid > 0:
            logger.debug(f"Property '{prop_name}': {n_invalid} cells have invalid PropGlobalID")

        return mapped_values

    def _aggregated_map(self,
                        grid: pv.UnstructuredGrid,
                        prop_name: str,
                        time_step: int,
                        agg_method: str) -> np.ndarray:
        """Aggregated mapping.

        Builds a full array in ``GlobalCellID`` space, performs bottom-up LGR
        aggregation, then maps onto the grid. Suited to grids that contain
        parent cells (e.g. ``level0``), where parents need their children's
        aggregated value.
        """
        # 1. Fetch the raw property array
        prop_data = self.indexer.get_property_data(prop_name, time_step)
        if prop_data is None:
            logger.warning(f"Property '{prop_name}' not found at step {time_step}.")
            return np.full(grid.n_cells, np.nan)

        # 2. Fetch geometry info
        geo_info = self._get_geometry_info(time_step)
        icstpb = geo_info['icstpb']
        icstps = geo_info['icstps']
        level = geo_info['level']
        max_level = geo_info['max_level']
        total_cells = len(icstpb)

        # 3. Build a full array in GlobalCellID space
        full_values = np.full(total_cells, np.nan, dtype=np.float32)
        valid_mask = (icstps > 0)
        prop_indices = icstps[valid_mask] - 1

        # Bounds check
        if len(prop_indices) > 0 and prop_indices.max() >= len(prop_data):
            logger.error(f"ICSTPS index out of bounds for property '{prop_name}'")
            valid_in_bounds = prop_indices < len(prop_data)
            valid_mask_indices = np.where(valid_mask)[0]
            safe_indices = valid_mask_indices[valid_in_bounds]
            safe_prop_indices = prop_indices[valid_in_bounds]
            full_values[safe_indices] = prop_data[safe_prop_indices]
        else:
            full_values[valid_mask] = prop_data[prop_indices]

        # 4. Perform bottom-up LGR aggregation
        if max_level > 0:
            full_values = self._aggregate_values(full_values, icstpb, level, max_level, agg_method)

        # 5. Map onto the grid via GlobalCellID
        if 'GlobalCellID' not in grid.cell_data:
            raise ValueError("Grid missing 'GlobalCellID' array. Cannot map aggregated data.")

        global_ids = grid.cell_data['GlobalCellID']

        if global_ids.max() >= len(full_values):
            logger.error(f"GlobalCellID {global_ids.max()} exceeds total cells {len(full_values)}")
            return np.full(grid.n_cells, np.nan)

        return full_values[global_ids]

    def _get_geometry_info(self, time_step: int) -> Dict:
        """Fetch and cache geometry info (ICSTPB, ICSTPS, inferred levels)."""
        if time_step in self._geo_cache:
            return self._geo_cache[time_step]

        # Find the nearest GRID time step
        grid_ts = self.indexer.get_nearest_grid_ts(time_step)
        if grid_ts != time_step:
            logger.debug(f"Geometry for step {time_step} not found. Using GRID from step {grid_ts}.")
            if grid_ts in self._geo_cache:
                self._geo_cache[time_step] = self._geo_cache[grid_ts]
                return self._geo_cache[grid_ts]

        # Fetch raw grid arrays
        data = self.indexer.get_grid_data(grid_ts)

        if 'ICSTPB' not in data or 'ICSTPS' not in data or 'IGNTNC' not in data:
            raise ValueError(f"Missing required geometry arrays at step {grid_ts}")

        icstpb = data['ICSTPB']
        icstps = data['ICSTPS']
        igntnc = data['IGNTNC']

        # Infer levels (shared implementation with GridBuilder)
        level = infer_levels(icstpb, igntnc)
        max_level = level.max() if len(level) > 0 else 0

        info = {
            'icstpb': icstpb,
            'icstps': icstps,
            'level': level,
            'max_level': max_level
        }

        self._geo_cache[time_step] = info
        return info

    def _aggregate_values(self,
                          full_values: np.ndarray,
                          icstpb: np.ndarray,
                          levels: np.ndarray,
                          max_level: int,
                          method: str = 'mean') -> np.ndarray:
        """Perform bottom-up LGR aggregation.

        Working from the deepest level upward, aggregate child-cell values into
        their parent cells using ``method``.
        """
        N = len(full_values)

        for lvl in range(max_level, 0, -1):
            # 1. Find the child cells at this level
            child_indices = np.where(levels == lvl)[0]
            if len(child_indices) == 0:
                continue

            # 2. Keep only finite values
            child_vals = full_values[child_indices]
            valid_mask = ~np.isnan(child_vals)
            valid_children = child_indices[valid_mask]
            valid_vals = child_vals[valid_mask]

            if len(valid_children) == 0:
                continue

            # 3. Resolve parent indices (1-based -> 0-based)
            parents = icstpb[valid_children] - 1

            # 4. Aggregate
            if method == 'mean':
                counts = np.bincount(parents, minlength=N)
                sums = np.bincount(parents, weights=valid_vals, minlength=N)
                with np.errstate(divide='ignore', invalid='ignore'):
                    aggs = sums / counts
                update_mask = (counts > 0)

            elif method == 'sum':
                aggs = np.bincount(parents, weights=valid_vals, minlength=N)
                counts = np.bincount(parents, minlength=N)
                update_mask = (counts > 0)

            elif method == 'min':
                aggs = np.full(N, np.inf)
                np.minimum.at(aggs, parents, valid_vals)
                update_mask = (aggs != np.inf)

            elif method == 'max':
                aggs = np.full(N, -np.inf)
                np.maximum.at(aggs, parents, valid_vals)
                update_mask = (aggs != -np.inf)

            else:
                logger.warning(f"Unknown aggregation method '{method}', defaulting to mean.")
                return self._aggregate_values(full_values, icstpb, levels, max_level, 'mean')

            # 5. Write aggregated values back into the parents
            full_values[update_mask] = aggs[update_mask]

        return full_values
