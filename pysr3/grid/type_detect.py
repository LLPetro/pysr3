"""Auto-detect a file's grid type from ``/SpatialProperties/<step>/GRID/IGNTGT``.

CMG STARS stores an integer ``IGNTGT`` array (one entry per sub-grid) in every
SR3's GRID group. The first entry is always the root grid's type code; every
nested LGR sub-grid carries the inherit code ``3``. Confirmed across all 12
bundled real-fixture cases (cartesian, vari, lgr, lgr_nested, radial, corner,
corner_coord, convert_to_corner, dfn_multi, dfn_refine, tutorial_hm,
mutibranch — root code in each is one of {1, 2, 12}); the per-fixture table
is asserted by ``test/test_grid_type_detect.py::test_detect_grid_type_per_real_fixture``.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Code -> registered grid_type name.
# Add new codes here when CMG STARS exposes additional grid families.
IGNTGT_CODE_MAP: Dict[int, str] = {
    1: "Cartesian",
    2: "Radial",
    12: "CornerPoint",
}

# Reserved code for "this sub-grid inherits its parent's geometry kind".
# Always appears at IGNTGT[1:] for LGR sub-grids; never at IGNTGT[0].
IGNTGT_INHERIT_CODE = 3


def detect_grid_type(data: Dict) -> Optional[str]:
    """Return the registered grid-type name for ``data``, or ``None``.

    ``data`` is the dict returned by :meth:`SR3Indexer.get_grid_data`. Reads
    ``IGNTGT[0]`` (the root grid's type code) and maps it through
    :data:`IGNTGT_CODE_MAP`. Returns ``None`` when:

    - ``IGNTGT`` is absent or empty (e.g. older SR3 versions),
    - the code is unknown to :data:`IGNTGT_CODE_MAP`,
    - the code is :data:`IGNTGT_INHERIT_CODE` (which should never appear at
      index 0 in a well-formed SR3 — return ``None`` so the caller can decide).
    """
    igntgt = data.get("IGNTGT") if isinstance(data, dict) else None
    if igntgt is None:
        return None
    arr = np.asarray(igntgt)
    if arr.size == 0:
        return None
    code = int(arr.flat[0])
    if code == IGNTGT_INHERIT_CODE:
        logger.debug(
            "detect_grid_type: IGNTGT[0]==%d is the LGR inherit code; "
            "this should never happen at the root of a well-formed SR3 — "
            "returning None.",
            IGNTGT_INHERIT_CODE,
        )
        return None
    name = IGNTGT_CODE_MAP.get(code)
    if name is None:
        logger.debug(
            "detect_grid_type: IGNTGT[0]==%d is unknown to IGNTGT_CODE_MAP "
            "(known: %s); returning None.",
            code, sorted(IGNTGT_CODE_MAP),
        )
    return name
