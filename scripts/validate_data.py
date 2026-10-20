"""Write data/validation_report.json and data/validation_report.md."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.data_audit import run_audit, write_reports


def main() -> None:
    report = run_audit()
    json_path, md_path = write_reports(report)
    shape = report["shape"]
    target = report["target"]
    duplicates = report["duplicates"]
    calibration = report["calibration"]
    print(f"rows={shape['rows']} columns={shape['columns']} row_ok={shape['row_count_matches_uci']}")
    print(
        f"donated={target['donated_march_2007']} rate={target['positive_rate']:.4f} "
        f"duplicates={duplicates['extra_copies_of_repeated_rows']}"
    )
    print(
        f"quartile_low={calibration.get('lowest_rate')} gap={calibration.get('lowest_gap')} "
        f"quartile_high={calibration.get('highest_rate')} gap={calibration.get('highest_gap')}"
    )
    print(report["calibration_note"])
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
