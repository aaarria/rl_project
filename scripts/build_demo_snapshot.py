"""Build the labeled offline snapshot used when the API is unavailable."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.data_audit import run_audit
from app.experiment import recommend, run_comparison
from app.policies import POLICY_ORDER


def main() -> None:
    result = run_comparison(
        horizon=52,
        seeds=[0, 1, 2],
        policies=list(POLICY_ORDER),
        initial_stock_fraction=0.6,
        weekly_demand=90,
        discount=0.95,
        ucb_c=0.1,
        wastage=0.02,
        preset="quick",
    )
    recommendation = recommend(
        policy_id="discounted_ucb",
        horizon=52,
        seed=0,
        initial_stock_fraction=0.6,
        weekly_demand=90,
        discount=0.95,
        ucb_c=0.1,
        wastage=0.02,
    )
    payload = {
        "label": "Offline demo snapshot",
        "notice": (
            "Computed by this project's simulator (52 weeks, seeds 0–2) and stored so the "
            "interface can be inspected when the API is down. It is not a live response and "
            "it is not copied from the report's Table 6."
        ),
        "result": result,
        "recommendation": recommendation,
        "data_quality": run_audit(),
    }
    out = ROOT / "frontend" / "public" / "demo-snapshot.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload))
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
