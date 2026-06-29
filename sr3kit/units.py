"""Unit subsystem for CMG STARS SR3 files.

A focused collaborator that owns the unit math — token parsing, label
composition, and UCT-based value conversion. Takes plain dicts at
construction time (loaded elsewhere by :class:`SR3Indexer`), so the
class itself has zero coupling to HDF5 and is trivial to unit-test
against hand-crafted fixtures.

Three input dicts:

- ``units`` (from ``/General/UnitsTable``):
  ``{idx: {'output_unit': str, 'internal_unit': str, 'dimensionality': str}}``
- ``unit_conversions`` (from ``/General/UnitConversionTable``):
  ``{dim_idx: {unit_name: (gain, offset)}}`` — formula
  ``canonical = stored * gain + offset``.
- ``name_records`` (from ``/General/NameRecordTable``): the per-keyword
  metadata dict; only the ``'dim_token'`` field is consulted here.

Public surface mirrors :class:`SR3Indexer` (which forwards to this object):

- :meth:`UnitConverter.get_unit` — resolve the unit string for a keyword.
- :meth:`UnitConverter.convert`  — convert per-cell values to a target unit.

Two module-level pure helpers are exported for callers that need to compose
a unit label from a token without instantiating the class (e.g. the indexer's
``_load_name_records`` pre-caches output/internal unit strings on each
:class:`SR3Indexer.name_records` entry):

- :func:`parse_dim_tokens` — ``'11|-13|'`` → ``[(11, +1), (13, -1)]``.
- :func:`parse_unit_key`   — ``'11|-13|'`` + ``units`` → ``'cm3/min'``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["UnitConverter", "parse_dim_tokens", "parse_unit_key"]


# --------------------------------------------------------------------------- #
# Pure-function helpers (no class state, no HDF5)
# --------------------------------------------------------------------------- #
def parse_dim_tokens(token: str) -> List[Tuple[int, int]]:
    """Parse a Dimensionality token like ``'11|-13|'`` into ``[(idx, sign), ...]``.

    Positive sign = numerator, negative = denominator. Empty / malformed
    pieces are silently skipped; a fully empty or unparsable token returns
    ``[]`` (callers treat that as "dimensionless").
    """
    out: List[Tuple[int, int]] = []
    for piece in token.strip('|').split('|'):
        if not piece:
            continue
        try:
            i = int(piece)
            out.append((abs(i), 1 if i > 0 else -1))
        except ValueError:
            continue
    return out


def parse_unit_key(token: str, units: Dict[int, Dict[str, str]], which: str = 'output') -> str:
    """Compose a unit-string label from a Dimensionality token + UnitsTable.

    ``which='output'`` (default) composes from each dimension's
    ``UnitsTable.Output Unit`` — i.e. what the stored bytes are in.
    ``which='internal'`` composes from ``UnitsTable.Internal Unit`` — the
    simulator's solver units.
    """
    if not token:
        return ""
    which_field = 'internal_unit' if which == 'internal' else 'output_unit'
    nums: List[str] = []
    dens: List[str] = []
    for idx, sign in parse_dim_tokens(token):
        unit_obj = units.get(idx)
        if isinstance(unit_obj, dict):
            u = unit_obj.get(which_field) or "?"
        else:
            u = str(unit_obj) if unit_obj else "?"
        (nums if sign > 0 else dens).append(u)
    n_str = "*".join(nums) if nums else "1"
    if not dens:
        return n_str if nums else ""
    d_str = "*".join(dens)
    return f"{n_str}/{d_str}"


# --------------------------------------------------------------------------- #
# UnitConverter — the focused collaborator
# --------------------------------------------------------------------------- #
class UnitConverter:
    """Resolve and convert units for SR3 property keywords.

    Held privately by :class:`SR3Indexer` as ``self._units``; the indexer's
    public ``get_unit`` / ``convert`` methods are thin forwarders. Useful
    standalone for unit-only testing — construct with three plain dicts
    (no HDF5 file required).
    """

    def __init__(
        self,
        units: Dict[int, Dict[str, str]],
        unit_conversions: Dict[int, Dict[str, Tuple[float, float]]],
        name_records: Dict[str, Dict[str, Any]],
    ) -> None:
        self.units = units
        self.unit_conversions = unit_conversions
        self.name_records = name_records

    # ----- Label resolution --------------------------------------------------
    def get_unit(self, keyword: str, to_unit: str = "output") -> str:
        """Return the unit string for ``keyword`` under the requested policy.

        Args:
            keyword: A property keyword (e.g. ``'PRES'``) or TimeSeries
                variable keyword (e.g. ``'BHP'``, ``'OILRATSC'``).
            to_unit:
                - ``'output'`` (default): the unit the stored bytes are in
                  (``UnitsTable.Output Unit``).
                - ``'internal'``: the CMG simulator's internal units
                  (``UnitsTable.Internal Unit``).
                - any specific unit name (e.g. ``'psi'``, ``'MPa'``, ``'md'``):
                  only valid for single positive-dimension keywords.

        Returns:
            The unit string; ``""`` if dimensionless or unknown keyword.

        Raises:
            ValueError: when ``to_unit`` is a specific unit name on a
                multi-token or denominator-only keyword.
        """
        rec = self.name_records.get(keyword)
        if not rec:
            return ""
        token = (rec.get('dim_token') or "").strip('|')
        if not token:
            return ""
        parsed = parse_dim_tokens(token)
        if not parsed:
            return ""
        if to_unit == "output":
            return parse_unit_key(rec['dim_token'], self.units, which='output')
        if to_unit == "internal":
            return parse_unit_key(rec['dim_token'], self.units, which='internal')
        if len(parsed) == 1 and parsed[0][1] > 0:
            return to_unit
        raise ValueError(
            f"to_unit={to_unit!r} only valid for single positive-dimension keywords"
        )

    # ----- Value conversion --------------------------------------------------
    def convert(self, keyword: str, values: Any, to_unit: str = "output") -> np.ndarray:
        """Convert ``values`` for ``keyword`` from the file's Output unit to ``to_unit``.

        - ``to_unit='output'`` (default) — no-op (values already in Output unit).
        - ``to_unit='internal'`` — per-token UCT conversion. Compound
          (multi-token) dimensions support gain-only conversion; a per-token
          non-zero offset (e.g. Temperature appearing in a compound) raises
          ``ValueError``.
        - ``to_unit='psi'`` / ``'MPa'`` / ``'md'`` / ``...`` — single
          positive-dimension keywords only; uses UCT to apply ``gain`` +
          ``offset``.

        Returns a NumPy array for array input, or a NumPy scalar for scalar
        input.
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
        parsed = parse_dim_tokens(token)
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
                        f"dim={idx} (stored={stored!r}, target={target!r}); "
                        f"leaving values unchanged"
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
