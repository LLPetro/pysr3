#!/usr/bin/env python3
"""Export SR3 TimeSeries entities to CSV for registered cases."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sr3kit.sr3_indexer import SR3Indexer
from tools.export_case_assets import CASES, CaseSpec


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value.strip().lower()).strip("_") or "timeseries"


def _select_cases(names: Iterable[str] | None) -> list[CaseSpec]:
    if not names:
        return list(CASES)
    cases_by_name = {case.name: case for case in CASES}
    missing = sorted(set(names) - set(cases_by_name))
    if missing:
        raise ValueError(f"Unknown case(s): {', '.join(missing)}")
    return [cases_by_name[name] for name in names]


def export_case_timeseries(case: CaseSpec, entities: list[str] | None = None) -> dict:
    if not case.sr3_path.exists():
        raise FileNotFoundError(f"SR3 not found: {case.sr3_path}")

    out_dir = case.sr3_path.parent / "timeseries"
    out_dir.mkdir(parents=True, exist_ok=True)

    with SR3Indexer(str(case.sr3_path), eager_list_steps=None) as indexer:
        available = indexer.get_timeseries_entities()
        selected = [e.upper() for e in entities] if entities else available
        missing = sorted(set(selected) - set(available))
        if missing:
            raise ValueError(f"{case.name}: missing TimeSeries entity(s): {missing}")

        entity_summaries = []
        for entity in selected:
            df = indexer.get_timeseries_data(entity)
            if df.empty:
                continue

            csv_path = out_dir / f"{_safe_name(entity)}.csv"
            df.to_csv(csv_path, index=False)

            info = indexer.get_timeseries_info(entity)
            entity_summaries.append({
                "entity": entity,
                "rows": int(len(df)),
                "origins": int(len([x for x in info.get("origins", []) if x])),
                "variables": int(len(info.get("variables", []))),
                "timesteps": int(len(info.get("timesteps", []))),
                "shape": [int(x) for x in info.get("shape", ())],
                "csv": str(csv_path.relative_to(ROOT)),
            })

        summary = {
            "case": case.name,
            "sr3": str(case.sr3_path.relative_to(ROOT)),
            "entities": entity_summaries,
        }
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SR3 TimeSeries entities to CSV.")
    parser.add_argument("--case", action="append", dest="cases", help="Case name to export. Repeatable.")
    parser.add_argument("--entity", action="append", dest="entities", help="TimeSeries entity, e.g. WELLS.")
    args = parser.parse_args()

    summaries = []
    for case in _select_cases(args.cases):
        summary = export_case_timeseries(case, args.entities)
        summaries.append(summary)
        details = ", ".join(f"{e['entity']}={e['rows']}" for e in summary["entities"])
        print(f"{summary['case']}: {details}")

    out_path = ROOT / "test/timeseries_assets_summary.json"
    out_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"summary={out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
