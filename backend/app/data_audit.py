"""Audit of the local UCI Blood Transfusion Service Center file.

The original file is read only. Duplicates are counted and kept.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

COLUMN_NAMES = ["Recency", "Frequency", "Monetary", "Time", "Donated"]
PUBLISHED_TABLE = {
    "Recency": {"min": 0.03, "max": 74.4, "mean": 9.74, "std": 8.07, "unit": "months"},
    "Frequency": {"min": 1, "max": 50, "mean": 5.51, "std": 5.84, "unit": "times"},
    "Monetary": {"min": 250, "max": 12500, "mean": 1378.68, "std": 1459.83, "unit": "c.c. blood"},
    "Time": {"min": 2.27, "max": 98.3, "mean": 34.42, "std": 24.32, "unit": "months"},
    "Donated": {"min": 0, "max": 1, "mean": 0.24, "std": None, "unit": "1 = donated in March 2007"},
}
# Report anchors: lowest and highest frequency-quartile return rates.
REPORT_QUARTILE_ENDPOINTS = {"lowest": 0.144, "highest": 0.366}
REPORT_INTERPOLATED_TIERS = {"tier_2": 0.218, "tier_3": 0.292}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def locate_data() -> Path:
    candidates = [
        repo_root() / "transfusion.data",
        repo_root() / "backend" / "transfusion.data",
        Path.cwd() / "transfusion.data",
        Path.cwd().parent / "transfusion.data",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "transfusion.data was not found. Expected it at the repository root."
    )


def load_frame(path: Path | None = None) -> tuple[pd.DataFrame, dict]:
    source = path or locate_data()
    raw = source.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    header = lines[0] if lines else ""
    frame = pd.read_csv(source)
    parsing = {
        "path": str(source),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "physical_lines_including_header": len(lines),
        "file_ends_with_newline": raw.endswith(b"\n"),
        "header": header,
        "rows_read": int(frame.shape[0]),
        "columns_read": int(frame.shape[1]),
        "original_column_names": [str(c) for c in frame.columns],
    }
    if frame.shape[1] != 5:
        frame.columns = [f"column_{i}" for i in range(frame.shape[1])]
    else:
        frame.columns = COLUMN_NAMES
        for column in COLUMN_NAMES:
            frame[column] = pd.to_numeric(
                frame[column].astype(str).str.strip(), errors="coerce"
            )
    return frame, parsing


def _stats(series: pd.Series) -> dict:
    clean = series.dropna()
    return {
        "count": int(clean.shape[0]),
        "missing": int(series.isna().sum()),
        "min": None if clean.empty else float(clean.min()),
        "max": None if clean.empty else float(clean.max()),
        "mean": None if clean.empty else float(clean.mean()),
        "std_sample": None if clean.shape[0] < 2 else float(clean.std(ddof=1)),
        "median": None if clean.empty else float(clean.median()),
    }


def quartile_rates(frame: pd.DataFrame) -> dict:
    """Equal-count quartiles via rank, plus natural bins if qcut can form them."""
    if frame["Frequency"].isna().any() or frame["Donated"].isna().any():
        usable = frame.dropna(subset=["Frequency", "Donated"]).copy()
    else:
        usable = frame
    ranks = usable["Frequency"].rank(method="first")
    labels = ["Q1_lowest_frequency", "Q2", "Q3", "Q4_highest_frequency"]
    quartile = pd.qcut(ranks, 4, labels=labels)
    rows = []
    for label, part in usable.groupby(quartile, observed=True):
        rows.append(
            {
                "quartile": str(label),
                "n": int(part.shape[0]),
                "frequency_min": float(part["Frequency"].min()),
                "frequency_max": float(part["Frequency"].max()),
                "donated_rate": float(part["Donated"].mean()),
                "donated_count": int(part["Donated"].sum()),
            }
        )
    natural: list[dict] = []
    natural_note = "Bins from qcut on Frequency with duplicates='drop', so donors who share a frequency stay together."
    try:
        natural_bin = pd.qcut(usable["Frequency"], 4, duplicates="drop")
        for label, part in usable.groupby(natural_bin, observed=True):
            natural.append(
                {
                    "bin": str(label),
                    "n": int(part.shape[0]),
                    "donated_rate": float(part["Donated"].mean()),
                }
            )
    except ValueError as exc:
        natural_note = f"Natural qcut failed: {exc}"
    lowest = rows[0]["donated_rate"] if rows else None
    highest = rows[-1]["donated_rate"] if rows else None
    natural_low = natural[0]["donated_rate"] if natural else None
    natural_high = natural[-1]["donated_rate"] if natural else None
    return {
        "method": (
            "Donors were ranked by Frequency with method='first' so tied frequencies "
            "still form four groups of equal size. The rate is the share with Donated = 1."
        ),
        "equal_count_quartiles": rows,
        "natural_frequency_bins": natural,
        "natural_bin_note": natural_note,
        "lowest_rate": lowest,
        "highest_rate": highest,
        "natural_lowest_rate": natural_low,
        "natural_highest_rate": natural_high,
        "report_lowest": REPORT_QUARTILE_ENDPOINTS["lowest"],
        "report_highest": REPORT_QUARTILE_ENDPOINTS["highest"],
        "lowest_gap": None if lowest is None else float(lowest - REPORT_QUARTILE_ENDPOINTS["lowest"]),
        "highest_gap": None if highest is None else float(highest - REPORT_QUARTILE_ENDPOINTS["highest"]),
        "natural_lowest_gap": None if natural_low is None else float(natural_low - REPORT_QUARTILE_ENDPOINTS["lowest"]),
        "natural_highest_gap": None if natural_high is None else float(natural_high - REPORT_QUARTILE_ENDPOINTS["highest"]),
        "report_middle_tiers_are_interpolations": REPORT_INTERPOLATED_TIERS,
        "middle_tier_note": (
            "The report states that 21.8% and 29.2% are linear interpolations between "
            "the endpoint rates, not empirical middle-quartile rates. They are not tested "
            "as observed frequencies."
        ),
    }


def run_audit(path: Path | None = None) -> dict:
    frame, parsing = load_frame(path)
    expected_columns = COLUMN_NAMES
    missing = {column: int(frame[column].isna().sum()) for column in frame.columns if column in expected_columns}
    malformed = int(sum(missing.values())) if frame.shape[1] == 5 else int(frame.shape[0])
    duplicate_mask = frame.duplicated(keep=False) if frame.shape[1] == 5 else None
    exact_duplicate_rows = int(frame.duplicated().sum()) if frame.shape[1] == 5 else None
    rows_in_duplicate_groups = int(duplicate_mask.sum()) if duplicate_mask is not None else None

    target_values = sorted(frame["Donated"].dropna().unique().tolist()) if "Donated" in frame else []
    donated_count = int((frame["Donated"] == 1).sum()) if "Donated" in frame else 0
    not_donated = int((frame["Donated"] == 0).sum()) if "Donated" in frame else 0
    n = int(frame.shape[0])
    rate = float(donated_count / n) if n else None

    stats = {column: _stats(frame[column]) for column in COLUMN_NAMES if column in frame}
    names_comparison = []
    for column, published in PUBLISHED_TABLE.items():
        actual = stats.get(column, {})
        names_comparison.append(
            {
                "variable": column,
                "published_min": published["min"],
                "actual_min": actual.get("min"),
                "published_max": published["max"],
                "actual_max": actual.get("max"),
                "published_mean": published["mean"],
                "actual_mean": actual.get("mean"),
                "published_std": published["std"],
                "actual_std_sample": actual.get("std_sample"),
            }
        )

    monetary_gap = None
    time_before_recency = None
    if set(COLUMN_NAMES).issubset(frame.columns):
        expected_monetary = frame["Frequency"] * 250
        monetary_gap = int((frame["Monetary"] - expected_monetary).abs().gt(1e-6).sum())
        time_before_recency = int((frame["Time"] < frame["Recency"]).sum())

    calibration = quartile_rates(frame) if "Frequency" in frame and "Donated" in frame else {}
    row_ok = n == 748
    column_ok = list(frame.columns) == COLUMN_NAMES
    target_ok = target_values == [0, 1] or target_values == [0.0, 1.0]
    missing_ok = malformed == 0

    limitations = [
        "This file is the UCI Blood Transfusion Service Center donor table from Hsin-Chu City, Taiwan (Yeh, 2008). It does not contain blood types, drive locations, hospital inventory, or Indian weekly turnout.",
        "The e-RaktKosh / NBTC dataset cited in the project report is not in the workspace.",
        "transfusion.names prints a descriptive table (Recency mean 9.74, and a 24% / 76% class split) that does not match this file exactly. The audit keeps both and does not overwrite the data.",
        "Duplicate rows are reported and retained. They were not dropped.",
        "Simulator pool sizes, seasonality, ABO mix, and demand shares are synthetic assumptions. They are not estimated from these 748 rows, apart from the report's use of frequency-quartile return rates as loyalty anchors.",
    ]

    natural_low_gap = calibration.get("natural_lowest_gap")
    natural_high_gap = calibration.get("natural_highest_gap")
    calibration_note = (
        "The report's 14.4% and 36.6% anchors match frequency bins that keep tied Frequency values together. "
        f"Those natural bins donate at {calibration.get('natural_lowest_rate')} and {calibration.get('natural_highest_rate')} "
        f"(gaps {natural_low_gap} and {natural_high_gap}). "
        "Forcing four groups of equal size splits donors who share a frequency, and the highest group then sits slightly lower. "
        "Middle tiers 21.8% and 29.2% remain the report's interpolations. The simulator uses the published tier rates either way."
    )

    return {
        "dataset": {
            "name": "Blood Transfusion Service Center",
            "origin": "UCI Machine Learning Repository",
            "citation": "Yeh, I-Cheng (2008). Blood Transfusion Service Center. UCI Machine Learning Repository. CC BY 4.0.",
            "paper": "Yeh, Yang, and Ting (2008/2009), Knowledge discovery on RFM model using Bernoulli sequence, Expert Systems with Applications.",
            "geography": "Hsin-Chu City, Taiwan. Not an Indian facility extract.",
            "target_definition": "Whether the donor gave blood in March 2007 (1 = yes, 0 = no).",
            "features": [
                "Recency: months since last donation",
                "Frequency: total number of donations",
                "Monetary: total blood donated in c.c.",
                "Time: months since first donation",
            ],
        },
        "parsing": parsing,
        "shape": {
            "rows": n,
            "columns": int(frame.shape[1]),
            "column_names": list(frame.columns),
            "expected_rows": 748,
            "expected_columns": COLUMN_NAMES,
            "row_count_matches_uci": row_ok,
            "column_names_match": column_ok,
        },
        "missing_and_malformed": {
            "missing_by_column": missing,
            "malformed_or_non_numeric_cells": malformed,
            "passes": missing_ok and column_ok,
        },
        "target": {
            "observed_values": [float(v) for v in target_values],
            "encoding_is_binary_0_1": bool(target_ok),
            "donated_march_2007": donated_count,
            "did_not_donate": not_donated,
            "positive_rate": rate,
            "negative_rate": None if rate is None else float(1 - rate),
            "names_file_claims_positive_rate": 0.24,
            "imbalance": "The March 2007 class is the minority class." if rate is not None and rate < 0.5 else "Check the rate.",
        },
        "duplicates": {
            "extra_copies_of_repeated_rows": exact_duplicate_rows,
            "rows_that_belong_to_a_duplicate_group": rows_in_duplicate_groups,
            "unique_rows": None if exact_duplicate_rows is None else n - exact_duplicate_rows,
            "action": "Duplicates were counted and kept. Nothing was deleted from transfusion.data.",
        },
        "ranges_and_descriptive_statistics": stats,
        "consistency": {
            "monetary_not_equal_to_frequency_times_250": monetary_gap,
            "time_less_than_recency": time_before_recency,
            "note": "Each donation in this study is 250 c.c., so Monetary should equal Frequency × 250. Time (months since first donation) should be at least Recency.",
        },
        "names_file_comparison": names_comparison,
        "calibration": calibration,
        "calibration_note": calibration_note,
        "checks": {
            "row_count_748": row_ok,
            "five_columns": column_ok,
            "no_missing_values": missing_ok,
            "binary_target": bool(target_ok),
        },
        "limitations": limitations,
        "not_in_this_file": [
            "ABO and Rh blood types",
            "Drive location or time slot",
            "Hospital stock or shortage",
            "Indian weekly turnout",
            "e-RaktKosh or NBTC facility records",
        ],
    }


def _fmt(value, digits=4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(report: dict) -> str:
    shape = report["shape"]
    target = report["target"]
    duplicates = report["duplicates"]
    missing = report["missing_and_malformed"]
    lines = [
        "# UCI transfusion.data validation",
        "",
        "Measured from the local file. Synthetic simulator assumptions are listed separately and are not findings about this table.",
        "",
        "## Source",
        "",
        f"- Dataset: {report['dataset']['name']}",
        f"- Origin: {report['dataset']['origin']}",
        f"- Citation: {report['dataset']['citation']}",
        f"- Geography: {report['dataset']['geography']}",
        f"- Target: {report['dataset']['target_definition']}",
        f"- SHA-256: `{report['parsing']['sha256']}`",
        f"- Header: `{report['parsing']['header']}`",
        "",
        "## Parsing and shape",
        "",
        f"- Rows: **{shape['rows']}** (expected 748). Match: {shape['row_count_matches_uci']}.",
        f"- Columns: **{shape['columns']}**. Names used after rename: {', '.join(shape['column_names'])}.",
        f"- Physical lines including header: {report['parsing']['physical_lines_including_header']}.",
        f"- File ends with a newline: {report['parsing']['file_ends_with_newline']}.",
        "",
        "## Missing values and target",
        "",
        f"- Non-numeric or missing cells: {missing['malformed_or_non_numeric_cells']}.",
        f"- Target values observed: {target['observed_values']}.",
        f"- Binary 0/1 encoding: {target['encoding_is_binary_0_1']}.",
        f"- Donated in March 2007: {target['donated_march_2007']} ({_fmt(target['positive_rate'], 4)}).",
        f"- Did not donate: {target['did_not_donate']} ({_fmt(target['negative_rate'], 4)}).",
        f"- Names file claims a 24% positive rate. Actual rate is {_fmt(target['positive_rate'], 4)}.",
        "",
        "## Duplicates",
        "",
        f"- Extra copies: {duplicates['extra_copies_of_repeated_rows']}.",
        f"- Rows sitting in a duplicate group: {duplicates['rows_that_belong_to_a_duplicate_group']}.",
        f"- Unique rows if extras were ignored: {duplicates['unique_rows']}.",
        f"- {duplicates['action']}",
        "",
        "## Descriptive statistics",
        "",
        "| Variable | Min | Max | Mean | Sample std | Missing |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for column, stats in report["ranges_and_descriptive_statistics"].items():
        lines.append(
            f"| {column} | {_fmt(stats['min'], 3)} | {_fmt(stats['max'], 3)} | {_fmt(stats['mean'], 3)} | {_fmt(stats['std_sample'], 3)} | {stats['missing']} |"
        )
    lines.extend(
        [
            "",
            "## Comparison with transfusion.names Table 1",
            "",
            "The names file prints mins, maxes, means, and standard deviations that do not all match this CSV. Both are kept. The CSV is the file the simulator's calibration check uses.",
            "",
            "| Variable | Names min | File min | Names max | File max | Names mean | File mean | Names std | File std |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["names_file_comparison"]:
        lines.append(
            "| {variable} | {published_min} | {actual_min} | {published_max} | {actual_max} | {published_mean} | {actual_mean} | {published_std} | {actual_std} |".format(
                variable=row["variable"],
                published_min=_fmt(row["published_min"], 3),
                actual_min=_fmt(row["actual_min"], 3),
                published_max=_fmt(row["published_max"], 3),
                actual_max=_fmt(row["actual_max"], 3),
                published_mean=_fmt(row["published_mean"], 3),
                actual_mean=_fmt(row["actual_mean"], 3),
                published_std=_fmt(row["published_std"], 3),
                actual_std=_fmt(row["actual_std_sample"], 3),
            )
        )
    consistency = report["consistency"]
    lines.extend(
        [
            "",
            "## Consistency",
            "",
            f"- Rows where Monetary ≠ Frequency × 250: {consistency['monetary_not_equal_to_frequency_times_250']}.",
            f"- Rows where Time < Recency: {consistency['time_less_than_recency']}.",
            "",
            "## Loyalty-tier calibration",
            "",
            report["calibration_note"],
            "",
            report["calibration"].get("method", ""),
            "",
            "| Quartile | n | Frequency min | Frequency max | Donated rate |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["calibration"].get("equal_count_quartiles", []):
        lines.append(
            f"| {row['quartile']} | {row['n']} | {row['frequency_min']} | {row['frequency_max']} | {_fmt(row['donated_rate'], 4)} |"
        )
    cal = report["calibration"]
    lines.extend(
        [
            "",
            f"- Equal-count lowest gap vs 14.4%: {_fmt(cal.get('lowest_gap'), 4)}. Highest gap vs 36.6%: {_fmt(cal.get('highest_gap'), 4)}.",
            f"- Natural-bin lowest gap vs 14.4%: {_fmt(cal.get('natural_lowest_gap'), 4)}. Highest gap vs 36.6%: {_fmt(cal.get('natural_highest_gap'), 4)}.",
            f"- {cal.get('middle_tier_note')}",
            "",
            "### Natural frequency bins",
            "",
            cal.get("natural_bin_note", ""),
            "",
        ]
    )
    for row in cal.get("natural_frequency_bins", []):
        lines.append(f"- {row['bin']}: n={row['n']}, donated rate={_fmt(row['donated_rate'], 4)}")
    lines.extend(["", "## Not in this file", ""])
    for item in report["not_in_this_file"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_reports(report: dict | None = None, directory: Path | None = None) -> tuple[Path, Path]:
    payload = report or run_audit()
    out_dir = directory or (repo_root() / "data")
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "validation_report.json"
    md_path = out_dir / "validation_report.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    md_path.write_text(render_markdown(payload))
    return json_path, md_path
