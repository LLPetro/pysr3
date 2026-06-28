#!/usr/bin/env python3
"""Indexer for CMG STARS SR3 (HDF5) reservoir-simulation files.

:class:`SR3Indexer` opens a single ``.sr3`` file and exposes:

- Raw array access (``get_grid_data``, ``get_property_data``, ``get_grid_array``)
  with a transparent ``/SpatialProperties/<step>/GRID/`` fallback for static
  arrays such as ``BLOCKPVOL``/``BLOCKSIZE``/``ICSTPS``.
- Time-step navigation (``get_grid_time_steps``, ``get_available_times``,
  ``get_nearest_grid_ts``, ``time_to_offset``).
- Property catalog (``get_available_properties``, ``get_property_info``) with
  STARS component-model resolution (e.g. ``SOLCONC3(1)`` → ``Solid Conc (CH4-HyD)``).
- Unit subsystem driven by ``/General/UnitsTable`` + ``/General/UnitConversionTable``
  (``unit_of``, ``convert``, plus ``to_unit=`` on every value-returning method).
- IGNTGT-based grid-type detection (``detect_grid_type``) used by
  :class:`pysr3.GridBuilder` to auto-pick a strategy.
- Pandas-shaped well/time-series data (``get_well_data``, ``get_timeseries_data``).

The indexer is the single source of truth; downstream classes
(:class:`pysr3.GridBuilder`, :class:`pysr3.DataMapper`) consume it but never
read HDF5 directly.
"""

from __future__ import annotations

import bisect
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import h5py
import numpy as np

from .grid.type_detect import detect_grid_type as _detect_grid_type

# Optional Pandas support
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

logger = logging.getLogger("pysr3.indexer")

class SR3Indexer:
    """
    The central data accessor for CMG SR3 files.
    
    Responsibilities:
    1. Manage HDF5 file handle (Open/Close).
    2. Index metadata, components, units, and variable names.
    3. Fetch raw data arrays (Grid, Properties) without geometric interpretation.
    4. Fetch and format Well data.
    """
    
    def __init__(self, file_path: str, list_props_ts: Optional[int] = None):
        """
        Initialize the SR3 Indexer.

        Args:
            file_path: Path to the .sr3 file.
            list_props_ts: Eagerly index property keywords for the first N
                timesteps; the rest are filled in lazily on demand. ``None``
                (default) eagerly indexes every step — appropriate for typical
                SR3 files. Pass an integer (e.g. ``1``) for very large files
                where listing every step's property catalog up-front is slow;
                ``get_available_properties`` will still resolve missing steps
                on demand.
        """
        self.file_path = file_path
        self.handle: Optional[h5py.File] = None
        
        # --- Metadata Stores ---
        self.metadata: Dict[str, Any] = {}
        self.components: Dict[str, List[str]] = {
            'all': [],
            'fluid': [],   # numy
            'liquid': [],  # numx
            'aqueous': [], # numw
            'solid': [],   # ncomp - numy
            'dimensions': (0, 0, 0, 0) # (ncomp, numy, numx, numw)
        }
        
        self.units: Dict[int, Dict[str, str]] = {}  # ID -> {output, internal, dimension}
        # CMG-provided unit conversion table: dim_idx -> {unit_name: (gain, offset)}
        # Formula: canonical_value = stored_value * gain + offset
        self.unit_conversions: Dict[int, Dict[str, Tuple[float, float]]] = {}
        self.name_records: Dict[str, Dict] = {}     # Keyword -> Info Dict
        
        # --- Time & Grid Index ---
        self.time_index: Dict[str, Any] = {
            'spatial_time_indices': [], # List of int
            'time_to_offset': {},          # step_idx -> days (float)
            'time_to_date': {}         # step_idx -> date string
        }
        
        self.spatial_props: Dict[str, Any] = {
            'timesteps': [],        # List of str keys ("000000")
            'properties_by_ts': {}, # step_idx -> List[str]
            'grid_timesteps': []    # List of int containing GRID
        }
        
        # --- TimeSeries (per-entity index: WELLS, LAYERS, GROUPS, SECTORS, ...) ---
        self.timeseries: Dict[str, Dict[str, Any]] = {}

        # --- Initialization Sequence ---
        self._open_file()
        try:
            self._load_metadata()
            self._load_components()
            self._load_units()
            self._load_unit_conversions()
            self._load_name_records()
            self._load_time_index()
            self._index_spatial_properties(list_props_ts=list_props_ts)
            self._detect_grid_timesteps()
            self._load_timeseries_index()
        except Exception as e:
            logger.error(f"Initialization failed for {file_path}: {e}")
            self.close()
            raise

    def _open_file(self):
        """Open HDF5 file in read-only mode."""
        if not Path(self.file_path).exists():
            raise FileNotFoundError(f"SR3 file not found: {self.file_path}")
        try:
            self.handle = h5py.File(self.file_path, 'r')
        except Exception as e:
            raise IOError(f"Failed to open SR3 file: {e}")

    def close(self):
        """Close the HDF5 file handle."""
        if self.handle:
            self.handle.close()
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _decode_bytes(self, data: Any) -> str:
        """Helper to decode bytes to string."""
        if isinstance(data, bytes):
            return data.decode('utf-8', errors='ignore').strip().strip('"').strip("'")
        return str(data).strip()

    @staticmethod
    def _pick_dtype_field(dtype_names: Tuple[str, ...], candidates: List[str]) -> Optional[str]:
        """Pick a column name by candidates (case-insensitive)."""
        for cand in candidates:
            for name in dtype_names:
                if name.lower() == cand.lower():
                    return name
        return None

    # --- Loading Methods ---

    def _load_metadata(self):
        """Load attributes from Root and /General."""
        # 1. Root Attributes
        for k, v in self.handle.attrs.items():
            self.metadata[k] = self._decode_bytes(v)

        # 2. General Group Attributes (if any)
        if 'General' in self.handle:
            gen = self.handle['General']
            for k, v in gen.attrs.items():
                self.metadata[k] = self._decode_bytes(v)
            
        # Format and Log Metadata
        log_msg = ["Loaded SR3 Metadata:"]
        
        # 1. Standard Fields
        std_keys = ['RunDate', 'SR3 Version', 'Simulator Name', 'Simulator Version']
        for k in std_keys:
            val = self.metadata.get(k, "N/A")
            log_msg.append(f"  {k}: {val}")
            
        # 2. Titles (Merge Title 1, Title 2, etc.)
        titles = []
        for k, v in self.metadata.items():
            if k.startswith("Title"):
                titles.append((k, v))
        # Sort by key to ensure Title 1, Title 2 order
        titles.sort(key=lambda x: x[0]) 
        if titles:
            # Merge with newlines as requested
            full_title = "\n    ".join([t[1] for t in titles])
            log_msg.append(f"  Title:\n    {full_title}")
            
        # 3. Case ID
        if 'Case ID' in self.metadata:
            log_msg.append(f"  Case ID: {self.metadata['Case ID']}")
            
        logger.info("\n".join(log_msg))

    def _load_components(self):
        """
        Load component info from /General/ComponentTable.
        Implements STARS logic:
        ncomp: Total
        numy: Fluid (Oil/Gas/Water phases)
        numx: Liquid (Oil/Water phases)
        numw: Aqueous
        """
        if 'General/ComponentTable' not in self.handle:
            return

        ct = self.handle['General/ComponentTable']
        
        # Parse DIMENSIONS
        dims = (0, 0, 0, 0)
        if 'DIMENSIONS' in ct.attrs:
            d_str = self._decode_bytes(ct.attrs['DIMENSIONS'])
            try:
                # "4 3 2 1" -> [4, 3, 2, 1]
                parts = [int(x) for x in d_str.split()]
                if len(parts) >= 4:
                    dims = tuple(parts[:4])
            except ValueError:
                logger.warning(f"Failed to parse DIMENSIONS: {d_str}")
        
        self.components['dimensions'] = dims
        ncomp, numy, numx, numw = dims
        
        # Read Component Names
        try:
            raw_data = ct[()]
            all_comps = []
            
            # Check if structured
            if raw_data.dtype.names:
                name_col = self._pick_dtype_field(raw_data.dtype.names, ["Name"])
                name_col = name_col or raw_data.dtype.names[0]
                for row in raw_data:
                    all_comps.append(self._decode_bytes(row[name_col]))
            else:
                # Simple array
                for val in raw_data:
                    all_comps.append(self._decode_bytes(val))
            
            self.components['all'] = all_comps
            
            # Check Simulator Name
            sim_name = self.metadata.get('Simulator Name', '').upper()
            
            if 'STARS' not in sim_name and 'SR3' not in sim_name: # SR3 might be generic
                 logger.warning(f"Simulator '{sim_name}' is not STARS. Applying STARS component logic by default, but verify results.")

            # Categorize based on STARS logic (Applied to all for now)
            # Fluid: First numy components
            self.components['fluid'] = all_comps[:numy]
            
            # Liquid: First numx components (Subset of fluid)
            self.components['liquid'] = all_comps[:numx]
            
            # Aqueous: First numw components (Subset of liquid/fluid)
            self.components['aqueous'] = all_comps[:numw]
            
            # Solid: The rest (from numy to end)
            # Note: If ncomp > numy, the remainder are solids/others
            self.components['solid'] = all_comps[numy:]
            
            if ncomp != len(all_comps):
                logger.warning(f"Component count mismatch: DIMENSIONS says {ncomp}, found {len(all_comps)}")

        except Exception as e:
            logger.warning(f"Failed to load ComponentTable: {e}")

    def _load_units(self):
        """Load /General/UnitsTable."""
        if 'General/UnitsTable' not in self.handle:
            return
            
        try:
            ut = self.handle['General/UnitsTable'][()]
            if ut.dtype.names:
                # Robust column picking
                idx_col = self._pick_dtype_field(ut.dtype.names, ["Index", "ID"])
                out_col = self._pick_dtype_field(ut.dtype.names, ["Output Unit", "Unit"])
                in_col = self._pick_dtype_field(ut.dtype.names, ["Internal Unit"])
                dim_col = self._pick_dtype_field(ut.dtype.names, ["Dimensionality", "Dim"])
                
                # Fallback to column indices if names don't match
                if not idx_col: idx_col = ut.dtype.names[0]
                
                # We need all columns
                
                for row in ut:
                    try:
                        uid = int(row[idx_col])
                        ustr_out = self._decode_bytes(row[out_col]) if out_col else ""
                        ustr_in = self._decode_bytes(row[in_col]) if in_col else ""
                        dim_str = self._decode_bytes(row[dim_col]) if dim_col else ""
                        
                        self.units[uid] = {
                            'index': uid,
                            'output_unit': ustr_out,
                            'internal_unit': ustr_in,
                            'dimensionality': dim_str
                        }
                    except Exception as ex:
                        logger.warning(f"Error parsing unit row: {ex}")
                        
        except Exception as e:
            logger.warning(f"Failed to load UnitsTable: {e}")

    def _load_unit_conversions(self):
        """Load /General/UnitConversionTable.

        Each row maps a (Dimensionality, Unit Name) pair to a (Gain, Offset)
        such that ``canonical_value = stored_value * Gain + Offset``. The
        canonical for each dimension is the row whose Gain=1 and Offset=0.

        We use this table both to convert from the stored Output unit to the
        Internal unit (for ``to_unit='internal'``) and to convert to an
        arbitrary user-supplied unit name (for ``to_unit='psi'`` etc.).
        """
        if 'General/UnitConversionTable' not in self.handle:
            return
        try:
            uct = self.handle['General/UnitConversionTable'][()]
            names = uct.dtype.names
            if not names:
                return
            col_dim = self._pick_dtype_field(names, ["Dimensionality"])
            col_name = self._pick_dtype_field(names, ["Unit Name", "Unit"])
            col_gain = self._pick_dtype_field(names, ["Gain"])
            col_offset = self._pick_dtype_field(names, ["Offset"])
            if not all((col_dim, col_name, col_gain, col_offset)):
                logger.warning("UnitConversionTable: missing expected columns")
                return
            for row in uct:
                try:
                    dim = int(row[col_dim])
                    uname = self._decode_bytes(row[col_name])
                    gain = float(row[col_gain])
                    offset = float(row[col_offset])
                    self.unit_conversions.setdefault(dim, {})[uname] = (gain, offset)
                except Exception as ex:
                    logger.warning(f"Error parsing UCT row: {ex}")
        except Exception as e:
            logger.warning(f"Failed to load UnitConversionTable: {e}")

    def _load_name_records(self):
        """Load /General/NameRecordTable."""
        if 'General/NameRecordTable' not in self.handle:
            return

        try:
            nt = self.handle['General/NameRecordTable'][()]
            names = nt.dtype.names
            if not names:
                return

            # Map columns with robust picking
            col_key = self._pick_dtype_field(names, ["Keyword", "Key"])
            col_name = self._pick_dtype_field(names, ["Name"]) # 'Long Name' usually separate
            col_dim = self._pick_dtype_field(names, ["Dimensionality", "Units", "UnitKey"])
            col_size = self._pick_dtype_field(names, ["Size", "SizeRef"])

            if not col_key:
                return

            for row in nt:
                key = self._decode_bytes(row[col_key])
                name = self._decode_bytes(row[col_name]) if col_name else key

                # Parse the Dimensionality token (e.g. "3|" or "11|-13|") and
                # compose unit labels for BOTH Output (default — the stored
                # bytes) and Internal (the simulator's units).
                dim_key = self._decode_bytes(row[col_dim]) if col_dim else ""
                unit_out = self._parse_unit_key(dim_key, which='output')
                unit_int = self._parse_unit_key(dim_key, which='internal')

                # Parse SizeRef
                size_ref = ""
                if col_size:
                    size_ref = self._decode_bytes(row[col_size])

                self.name_records[key] = {
                    'name': name,
                    'unit': unit_out,            # default label: Output Unit
                    'unit_internal': unit_int,   # CMG simulator's Internal Unit
                    'dim_token': dim_key,        # raw token, needed for conversion
                    'size_ref': size_ref,
                }
        except Exception as e:
            logger.warning(f"Failed to load NameRecordTable: {e}")

    def _parse_unit_key(self, key: str, which: str = 'output') -> str:
        """Parse a Dimensionality token like '11|-13|' into a unit string.

        ``which='output'`` (default) composes the label from each dimension's
        ``UnitsTable.Output Unit`` — i.e. what the stored bytes are in.
        ``which='internal'`` composes from ``UnitsTable.Internal Unit`` — the
        simulator's solver units.
        """
        if not key:
            return ""
        which_field = 'internal_unit' if which == 'internal' else 'output_unit'
        parts = key.strip('|').split('|')
        nums, dens = [], []
        for p in parts:
            if not p:
                continue
            try:
                uid = int(p)
                unit_obj = self.units.get(abs(uid))
                if isinstance(unit_obj, dict):
                    u = unit_obj.get(which_field) or "?"
                else:
                    u = str(unit_obj) if unit_obj else "?"
                if uid > 0:
                    nums.append(u)
                else:
                    dens.append(u)
            except Exception:
                pass
        n_str = "*".join(nums) if nums else "1"
        d_str = "*".join(dens) if dens else ""
        if not dens:
            return n_str if nums else ""
        return f"{n_str}/{d_str}"

    # --- Public unit helpers --------------------------------------------------

    def unit_of(self, keyword: str, to_unit: str = "output") -> str:
        """Return the unit string for ``keyword`` under the requested policy.

        Args:
            keyword: A property keyword (e.g. ``'PRES'``) or a TimeSeries
                variable keyword (e.g. ``'BHP'``, ``'OILRATSC'``).
            to_unit:
                - ``'output'`` (default): the unit the stored bytes are in
                  (``UnitsTable.Output Unit``).
                - ``'internal'``: the CMG simulator's internal units
                  (``UnitsTable.Internal Unit``).
                - any specific unit name (e.g. ``'psi'``, ``'MPa'``, ``'md'``):
                  only valid for single positive-dimension keywords.

        Returns:
            The unit string, ``""`` if dimensionless or unknown keyword.
        """
        rec = self.name_records.get(keyword)
        if not rec:
            return ""
        token = (rec.get('dim_token') or "").strip('|')
        if not token:
            return ""
        parsed = self._parse_dim_tokens(token)
        if not parsed:
            return ""
        if to_unit == "output":
            return self._parse_unit_key(rec['dim_token'], which='output')
        if to_unit == "internal":
            return self._parse_unit_key(rec['dim_token'], which='internal')
        # Specific unit name: only valid for single positive-dimension keywords
        if len(parsed) == 1 and parsed[0][1] > 0:
            return to_unit
        raise ValueError(
            f"to_unit={to_unit!r} only valid for single positive-dimension keywords"
        )

    def convert(self, keyword: str, values: Any, to_unit: str = "output") -> np.ndarray:
        """Convert ``values`` for ``keyword`` from the file's Output unit to ``to_unit``.

        - ``to_unit='output'`` (default) — no-op (values already in Output unit).
        - ``to_unit='internal'`` — per-token UCT conversion. Compound (multi-token)
          dimensions support gain-only conversion; a per-token non-zero offset
          (e.g. Temperature appearing in a compound) raises ``ValueError``.
        - ``to_unit='psi'`` / ``'MPa'`` / ``'md'`` / ``...`` — single positive-dimension
          keywords only; uses UCT to apply ``gain`` + ``offset``.

        Returns a NumPy array for array input, or a NumPy scalar for scalar input.
        """
        arr = np.asarray(values, dtype=np.float64)
        if to_unit == "output":
            return arr
        rec = self.name_records.get(keyword)
        if not rec:
            return arr
        token = (rec.get('dim_token') or "").strip('|')
        if not token:
            return arr  # dimensionless
        parsed = self._parse_dim_tokens(token)
        if not parsed:
            return arr

        result = arr.copy()

        if to_unit == "internal":
            for idx, sign in parsed:
                stored = (self.units.get(idx) or {}).get('output_unit') or ""
                target = (self.units.get(idx) or {}).get('internal_unit') or ""
                if not stored or not target or stored == target:
                    continue
                rows = self.unit_conversions.get(idx)
                if not rows or stored not in rows or target not in rows:
                    logger.warning(
                        f"convert({keyword!r}, to_unit='internal'): no UCT entry for "
                        f"dim={idx} (stored={stored!r}, target={target!r}); leaving values unchanged"
                    )
                    return arr
                g_in, o_in = rows[stored]
                g_t, o_t = rows[target]
                if len(parsed) == 1:
                    # Single-dimension: full formula (handles Temperature offsets)
                    if sign > 0:
                        result = (result * g_in + o_in - o_t) / g_t
                    else:
                        # Single-token denominator quantity (unusual)
                        result = g_t / (result * g_in + o_in - o_t)
                else:
                    # Compound: per-token offsets must be zero to compose meaningfully
                    if o_in != 0.0 or o_t != 0.0:
                        raise ValueError(
                            f"convert({keyword!r}): cannot apply per-token offset "
                            f"conversion for dim={idx} inside a compound quantity"
                        )
                    ratio = g_in / g_t
                    result = result * ratio if sign > 0 else result / ratio
            return result

        # Specific unit name: only valid for single positive-dim keywords
        if len(parsed) != 1 or parsed[0][1] < 0:
            raise ValueError(
                f"to_unit={to_unit!r} only valid for single positive-dimension keywords"
            )
        idx, _ = parsed[0]
        stored = (self.units.get(idx) or {}).get('output_unit') or ""
        rows = self.unit_conversions.get(idx)
        if not rows or stored not in rows or to_unit not in rows:
            raise ValueError(
                f"convert({keyword!r}, to_unit={to_unit!r}): UCT does not know how to "
                f"convert dim={idx} from {stored!r} to {to_unit!r}"
            )
        g_in, o_in = rows[stored]
        g_t, o_t = rows[to_unit]
        return (result * g_in + o_in - o_t) / g_t

    def _parse_dim_tokens(self, token: str) -> List[Tuple[int, int]]:
        """Parse '11|-13|' into [(11, +1), (13, -1)]."""
        out: List[Tuple[int, int]] = []
        for t in token.strip('|').split('|'):
            if not t:
                continue
            try:
                i = int(t)
                out.append((abs(i), 1 if i > 0 else -1))
            except ValueError:
                continue
        return out

    def _load_time_index(self):
        """Load /General/MasterTimeTable."""
        if 'General/MasterTimeTable' not in self.handle:
            return
            
        try:
            mtt = self.handle['General/MasterTimeTable'][()]
            if mtt.dtype.names:
                # User requested direct column indexing to handle variable units (days, years, etc.)
                # Col 0: Index
                # Col 1: Time Offset
                # Col 2: Date
                
                idx_col = mtt.dtype.names[0]
                off_col = mtt.dtype.names[1] if len(mtt.dtype.names) > 1 else idx_col
                date_col = mtt.dtype.names[2] if len(mtt.dtype.names) > 2 else None

                # Ensure storage exists
                if 'time_to_date' not in self.time_index:
                    self.time_index['time_to_date'] = {}

                for row in mtt:
                    idx = int(row[idx_col])
                    
                    # Time Value
                    time_val = self._parse_time_to_offset(row[off_col])
                    if time_val is None:
                        time_val = float(idx)
                    self.time_index['time_to_offset'][idx] = time_val
                    
                    # Date Value
                    if date_col:
                        self.time_index['time_to_date'][idx] = self._decode_bytes(row[date_col])
        except Exception as e:
            logger.warning(f"Failed to load MasterTimeTable: {e}")

    def _parse_time_to_offset(self, value: Any) -> Optional[float]:
        """Parse 'Offset in days' which may be numeric or a string."""
        if value is None:
            return None
        if isinstance(value, (float, int, np.floating, np.integer)):
            return float(value)
        value = self._decode_bytes(value)
        try:
            return float(value)
        except Exception:
            pass
        for part in str(value).split():
            try:
                return float(part)
            except Exception:
                continue
        return None

    def _index_spatial_properties(self, list_props_ts: Optional[int] = 0):
        """Index /SpatialProperties."""
        if 'SpatialProperties' not in self.handle:
            return
            
        sp = self.handle['SpatialProperties']
        # Filter for numeric keys
        steps = sorted([k for k in sp.keys() if k.isdigit()], key=lambda x: int(x))
        self.spatial_props['timesteps'] = steps
        
        # Index properties for requested steps
        for i, step_key in enumerate(steps):
            step_idx = int(step_key)
            self.time_index['spatial_time_indices'].append(step_idx)
            
            # If list_props_ts is set, only index first N steps
            if list_props_ts is not None and i >= list_props_ts:
                continue
                
            self.spatial_props['properties_by_ts'][step_idx] = self._list_step_properties(step_idx)

    def _list_step_properties(self, step_idx: int) -> List[str]:
        """List non-GRID dataset names under a SpatialProperties timestep."""
        path = f"SpatialProperties/{step_idx:06d}"
        if path not in self.handle:
            return []
        grp = self.handle[path]
        return [k for k in grp.keys() if k != 'GRID' and isinstance(grp[k], h5py.Dataset)]

    def _detect_grid_timesteps(self):
        """Find which steps have GRID definition."""
        if 'SpatialProperties' not in self.handle:
            return
            
        for step_key in self.spatial_props['timesteps']:
            if 'GRID' in self.handle[f"SpatialProperties/{step_key}"]:
                self.spatial_props['grid_timesteps'].append(int(step_key))

    def _load_timeseries_index(self):
        """Index /TimeSeries entities without loading large data arrays."""
        if 'TimeSeries' not in self.handle:
            return

        ts_root = self.handle['TimeSeries']
        for entity_name in ts_root.keys():
            entity = ts_root[entity_name]
            if not isinstance(entity, h5py.Group):
                continue

            try:
                origins = []
                variables = []
                timesteps = []
                shape = (0, 0, 0)

                if 'Origins' in entity:
                    origins = [self._decode_bytes(v) for v in entity['Origins'][()]]
                if 'Variables' in entity:
                    variables = [self._decode_bytes(v) for v in entity['Variables'][()]]
                if 'Timesteps' in entity:
                    timesteps = [int(v) for v in entity['Timesteps'][()]]
                if 'Data' in entity:
                    shape = entity['Data'].shape

                self.timeseries[entity_name.upper()] = {
                    'name': entity_name,
                    'origins': origins,
                    'variables': variables,
                    'timesteps': timesteps,
                    'shape': shape,
                }
            except Exception as e:
                logger.warning(f"Failed to index TimeSeries/{entity_name}: {e}")

    # --- Public Data Access ---

    def get_grid_data(self, ts: int) -> Dict[str, Any]:
        """
        Fetch raw grid data for a timestep.
        Returns a dictionary of numpy arrays and attributes.
        Does NOT return h5py objects.
        """
        path = f"SpatialProperties/{ts:06d}/GRID"
        if path not in self.handle:
            return {}
            
        grid_grp = self.handle[path]
        data = {}
        
        # Read Datasets
        for k in grid_grp.keys():
            obj = grid_grp[k]
            if isinstance(obj, h5py.Dataset):
                data[k] = obj[()]
        
        # Read Attributes
        for k, v in grid_grp.attrs.items():
            data[k] = v # Keep raw or decode? Usually raw numbers are fine.
            
        return data

    def get_property_data(self, name: str, timestep: Union[int, float]) -> Optional[np.ndarray]:
        """Fetch a raw 1-D property array by keyword.

        Lookup order:

        1. ``/SpatialProperties/<step>/<name>`` — the usual location for
           per-step properties (``PRES``, ``SO``, ``MODBVOL``, …).
        2. ``/SpatialProperties/<grid_step>/GRID/<name>`` — static arrays
           written only at grid time steps (``BLOCKPVOL``, ``BLOCKSIZE``,
           ``ICSTPS``, …). ``grid_step`` is resolved via
           :meth:`get_nearest_grid_ts`, so the call works for any results step.

        Args:
            name: Property keyword (case-sensitive, as stored in
                ``/General/NameRecordTable``).
            timestep: Integer step index, or a float in the same unit as
                :meth:`time_to_offset` (auto-snaps to the nearest indexed step).

        Returns:
            The 1-D NumPy array, or ``None`` if no dataset for that keyword
            exists at the resolved step or in its GRID group.
        """
        # Resolve timestep
        ts_idx = timestep
        if isinstance(timestep, float):
            # time_to_offset is a small dict of {step_idx: days}; a linear
            # scan beats building a sorted index for one-off lookups.
            best_ts = -1
            min_diff = float('inf')
            for t_idx, t_val in self.time_index['time_to_offset'].items():
                diff = abs(t_val - timestep)
                if diff < min_diff:
                    min_diff = diff
                    best_ts = t_idx
            if best_ts != -1:
                ts_idx = best_ts
            else:
                ts_idx = int(timestep) # Fallback
        
        path = f"SpatialProperties/{int(ts_idx):06d}/{name}"
        if path in self.handle:
            return self.handle[path][()]
        # Fall back to /GRID/ — some static arrays (BLOCKPVOL, BLOCKSIZE, etc.)
        # live there instead of at the step root, but are queryable by keyword
        # via the same NameRecordTable.Dimensionality. Since /GRID/ is only
        # written at grid time steps, resolve to the nearest one before lookup
        # so the call works for any results time step.
        grid_ts = self.get_nearest_grid_ts(int(ts_idx))
        grid_path = f"SpatialProperties/{int(grid_ts):06d}/GRID/{name}"
        if grid_path in self.handle:
            return self.handle[grid_path][()]
        return None

    def get_available_properties(self, ts: Optional[int] = None) -> List[str]:
        """Get list of properties for a timestep."""
        if not self.time_index['spatial_time_indices']:
            return []
            
        target_ts = ts if ts is not None else self.time_index['spatial_time_indices'][0]
        
        # Check cache
        if target_ts in self.spatial_props['properties_by_ts']:
            return self.spatial_props['properties_by_ts'][target_ts]
            
        # Fetch on demand and cache
        props = self._list_step_properties(target_ts)
        self.spatial_props['properties_by_ts'][target_ts] = props
        return props

    def get_timeseries_entities(self) -> List[str]:
        """Return available TimeSeries entity names, e.g. WELLS, LAYERS, GROUPS."""
        return sorted(self.timeseries.keys())

    def get_timeseries_info(self, entity: str = 'WELLS') -> Dict[str, Any]:
        """Return indexed metadata for a TimeSeries entity."""
        key = entity.upper()
        if key not in self.timeseries:
            return {
                'name': entity,
                'origins': [],
                'variables': [],
                'timesteps': [],
                'shape': (0, 0, 0),
            }
        return self.timeseries[key]

    def get_timeseries_data(self,
                            entity: str = 'WELLS',
                            origins: Optional[List[str]] = None,
                            variables: Optional[List[str]] = None,
                            timesteps: Optional[List[int]] = None,
                            drop_empty_origins: bool = True,
                            to_unit: str = 'output') -> Any:
        """
        Fetch TimeSeries data as a long-form DataFrame.

        SR3 stores TimeSeries/Data as (time, variable, origin).
        Columns:
        Entity, Origin, Variable, TimeIndex, Time, Date, Value, Unit, OriginIndex, VariableIndex.

        ``to_unit`` controls how ``Value`` (and ``Unit``) are returned:
          - ``'output'`` (default) — values as stored, labelled by Output Unit.
          - ``'internal'`` — values converted to CMG's Internal Unit, labelled accordingly.
          - any specific unit name (e.g. ``'psi'``) — single-dimension variables only.
        """
        if not HAS_PANDAS:
            raise ImportError("Pandas is required for get_timeseries_data")

        key = entity.upper()
        info = self.timeseries.get(key)
        path = f"TimeSeries/{key}/Data"

        if not info or path not in self.handle:
            return pd.DataFrame()

        all_origins = list(info.get('origins', []))
        all_variables = list(info.get('variables', []))
        all_timesteps = list(info.get('timesteps', []))
        data = self.handle[path][()]

        if data.ndim != 3:
            raise ValueError(f"TimeSeries/{key}/Data must be 3D, got shape {data.shape}")

        n_times, n_vars, n_origins = data.shape
        if len(all_timesteps) != n_times:
            logger.warning(f"TimeSeries/{key}: Timesteps length {len(all_timesteps)} does not match data axis {n_times}")
            all_timesteps = all_timesteps[:n_times] or list(range(n_times))
        if len(all_variables) != n_vars:
            logger.warning(f"TimeSeries/{key}: Variables length {len(all_variables)} does not match data axis {n_vars}")
            all_variables = all_variables[:n_vars]
        if len(all_origins) != n_origins:
            logger.warning(f"TimeSeries/{key}: Origins length {len(all_origins)} does not match data axis {n_origins}")
            all_origins = all_origins[:n_origins]

        origin_indices = self._resolve_name_indices(all_origins, origins, 'origin')
        variable_indices = self._resolve_name_indices(all_variables, variables, 'variable')
        timestep_indices = self._resolve_timestep_indices(all_timesteps, timesteps)

        if drop_empty_origins:
            origin_indices = [i for i in origin_indices if i < len(all_origins) and all_origins[i] != ""]

        # If a non-default unit policy is requested, convert each used variable's
        # slice up-front (vectorized) and remember the resolved unit label.
        var_units: Dict[int, str] = {}
        if to_unit == 'output':
            for v_idx in set(variable_indices):
                var_units[v_idx] = self.unit_of(all_variables[v_idx], 'output')
            converted = data
        else:
            converted = data.astype(np.float64, copy=True)
            for v_idx in set(variable_indices):
                var_name = all_variables[v_idx]
                try:
                    converted[:, v_idx, :] = self.convert(var_name, data[:, v_idx, :], to_unit)
                    var_units[v_idx] = self.unit_of(var_name, to_unit)
                except ValueError as exc:
                    logger.warning(f"get_timeseries_data: {exc}; leaving {var_name!r} in output units")
                    converted[:, v_idx, :] = data[:, v_idx, :]
                    var_units[v_idx] = self.unit_of(var_name, 'output')

        records = []
        for t_pos in timestep_indices:
            ts = int(all_timesteps[t_pos])
            time_value = self.time_to_offset(ts)
            date_value = self.time_index.get('time_to_date', {}).get(ts)

            for origin_idx in origin_indices:
                origin_name = all_origins[origin_idx]
                for var_idx in variable_indices:
                    var_name = all_variables[var_idx]
                    records.append({
                        'Entity': key,
                        'Origin': origin_name,
                        'Variable': var_name,
                        'TimeIndex': ts,
                        'Time': time_value,
                        'Date': date_value,
                        'Value': converted[t_pos, var_idx, origin_idx],
                        'Unit': var_units[var_idx],
                        'OriginIndex': origin_idx,
                        'VariableIndex': var_idx,
                    })

        if not records:
            return pd.DataFrame(columns=[
                'Entity', 'Origin', 'Variable', 'TimeIndex', 'Time', 'Date',
                'Value', 'Unit', 'OriginIndex', 'VariableIndex'
            ])

        return pd.DataFrame.from_records(records)

    def _resolve_name_indices(self, names: List[str], selected: Optional[List[str]], label: str) -> List[int]:
        """Resolve exact names to indices while preserving requested order."""
        if selected is None:
            return list(range(len(names)))

        name_to_index = {name: i for i, name in enumerate(names)}
        missing = [name for name in selected if name not in name_to_index]
        if missing:
            raise ValueError(f"Unknown TimeSeries {label}(s): {missing}")
        return [name_to_index[name] for name in selected]

    def _resolve_timestep_indices(self, timesteps: List[int], selected: Optional[List[int]]) -> List[int]:
        """Resolve timestep values to positions in the TimeSeries time axis."""
        if selected is None:
            return list(range(len(timesteps)))

        ts_to_index = {int(ts): i for i, ts in enumerate(timesteps)}
        missing = [int(ts) for ts in selected if int(ts) not in ts_to_index]
        if missing:
            raise ValueError(f"Unknown TimeSeries timestep(s): {missing}")
        return [ts_to_index[int(ts)] for ts in selected]

    def get_well_data(self,
                      well_names: Optional[List[str]] = None,
                      variable_names: Optional[List[str]] = None,
                      timesteps: Optional[List[int]] = None,
                      to_unit: str = 'output') -> Any:
        """
        Fetch well data as a Pandas DataFrame.

        ``to_unit`` is forwarded to :meth:`get_timeseries_data` — see its
        docstring for the accepted values.
        """
        df = self.get_timeseries_data(
            entity='WELLS',
            origins=well_names,
            variables=variable_names,
            timesteps=timesteps,
            to_unit=to_unit,
        )
        if df.empty:
            return df

        df = df.copy()
        df['Well'] = df['Origin']
        columns = [
            'Date', 'Time', 'TimeIndex', 'Well', 'Variable', 'Value', 'Unit',
            'OriginIndex', 'VariableIndex'
        ]
        return df[columns]

    # --- Info Resolution ---

    def get_property_info(self, name: str, to_unit: str = 'output') -> Dict[str, str]:
        """
        Resolve display name and unit for a property.
        e.g. 'SOLCONC3(1)' -> 'Solid Conc (CH4-HyD)'

        ``to_unit`` controls which unit string is returned (default ``'output'``
        — the unit the stored bytes are in). See :meth:`unit_of` for details.
        """
        # 1. Parse input
        match = re.match(r"([A-Za-z0-9_]+)(?:\((\d+)\))?", name)
        if not match:
            return {'display_name': name, 'unit': '', 'original_key': name, 'component': ''}
        
        base_key = match.group(1)
        idx_str = match.group(2)
        idx = int(idx_str) if idx_str else None
        
        # 2. Find Record
        record_key = base_key
        record = self.name_records.get(base_key)
        if not record:
            record_key = base_key + "$C"
            record = self.name_records.get(record_key)

        if not record:
            return {'display_name': name, 'unit': '', 'original_key': name, 'component': ''}

        template = record['name']
        # Resolve unit under the requested policy (handles 'output' / 'internal' /
        # any specific unit name); falls back to the stored Output Unit label.
        try:
            unit = self.unit_of(record_key, to_unit=to_unit)
        except ValueError:
            unit = record.get('unit', '')
        size_ref = record['size_ref']
        
        # 3. Resolve Component
        comp_name = ""
        if idx is not None:
            # Determine list based on size_ref
            c_list = []
            if size_ref == 'nsold':
                c_list = self.components['solid']
            elif size_ref == 'numy': # Fluid
                c_list = self.components['fluid']
            elif size_ref == 'numx': # Liquid
                c_list = self.components['liquid']
            elif size_ref == 'numw': # Aqueous
                c_list = self.components['aqueous']
            
            # Map index (1-based) to list
            if c_list and 1 <= idx <= len(c_list):
                comp_name = c_list[idx-1]
            else:
                comp_name = str(idx)
        
        # 4. Format Display Name
        if "$C" in template:
            display_name = template.replace("$C", f"({comp_name})" if comp_name else "")
        else:
            display_name = f"{template} ({comp_name})" if comp_name else template
            
        return {
            'display_name': display_name.strip(),
            'unit': unit,
            'original_key': name,
            'component': comp_name
        }

    def get_grid_time_steps(self) -> List[int]:
        return self.spatial_props['grid_timesteps']

    def get_available_times(self) -> List[int]:
        return self.time_index['spatial_time_indices']

    def time_to_offset(self, ts: int) -> float:
        return self.time_index['time_to_offset'].get(ts, float(ts))

    def get_nearest_grid_ts(self, time_step: int) -> int:
        """
        Find the nearest grid timestep not exceeding the target.
        Fallback: if none found, return the first grid timestep; if list is empty, return 0.
        """
        grid_steps = self.get_grid_time_steps()
        if not grid_steps:
            return 0
        grid_steps_sorted = sorted(grid_steps)
        pos = bisect.bisect_right(grid_steps_sorted, time_step)
        if pos == 0:
            return grid_steps_sorted[0]
        return grid_steps_sorted[pos - 1]

    def detect_grid_type(self, time_step: int = 0) -> Optional[str]:
        """Return the file's root grid-type name (or ``None`` if undetectable).

        Reads ``/SpatialProperties/<step>/GRID/IGNTGT[0]`` and maps it through
        :data:`pysr3.grid.type_detect.IGNTGT_CODE_MAP`. Returns ``None`` when
        ``IGNTGT`` is missing/empty or the code is unknown — letting the caller
        decide whether to raise or fall back.
        """
        data = self.get_grid_data(self.get_nearest_grid_ts(time_step))
        return _detect_grid_type(data)

    def get_grid_array(self, name: str, time_step: int) -> Optional[np.ndarray]:
        """Read one dataset from ``/SpatialProperties/<step>/GRID/<name>``.

        Returns ``None`` when the dataset is absent. Centralises the GRID-group
        read path so callers don't need to know whether a static array lives in
        ``/GRID/`` (e.g. ``BLOCKPVOL``, ``BLOCKSIZE``, ``ICSTPS``) versus at the
        step root (e.g. ``MODBVOL``, ``PRES``).
        """
        ts = self.get_nearest_grid_ts(time_step)
        path = f"SpatialProperties/{int(ts):06d}/GRID/{name}"
        if path in self.handle:
            return self.handle[path][()]
        return None
