"""FastAPI application."""

from __future__ import annotations

import os

from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import (
    ARMS,
    ASSUMPTIONS,
    BLOOD_TYPES,
    DEFAULT_DISCOUNT,
    DEFAULT_HORIZON,
    DEFAULT_INITIAL_STOCK_FRACTION,
    DEFAULT_UCB_C,
    DEFAULT_WASTAGE,
    DEFAULT_WEEKLY_DEMAND,
    DEMAND_SHARE,
    FULL_PRESET,
    LOYALTY_RATE,
    POPULATION_MIX,
    PRIORITY,
    QUICK_PRESET,
    REPORT_TABLE_MEAN_DONORS,
    REWARD_SCALE,
    WEEK_ORDER,
)
from app.data_audit import run_audit, write_reports
from app.environment import (
    N_ARMS,
    expected_reward,
    expected_turnout,
    seasonal_multiplier,
    shortage_vector,
    target_stock,
    turnout_probability,
)
from app.experiment import compare_plan, plan_drive, recommend, run_comparison, run_sensitivity
from app.export import comparison_to_csv
from app.policies import POLICY_ORDER, POLICIES
from app.schemas import PlanRequest, RecommendRequest, SensitivityRequest, SimulateRequest

app = FastAPI(
    title="Adaptive Blood Drive Scheduling",
    version="1.0.0",
    summary="Shortage-weighted multi-armed bandit simulator for eight donation drives.",
)

_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_extra = [item.strip() for item in os.environ.get("CORS_ORIGINS", "").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra,
    allow_origin_regex=os.environ.get("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app"),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _jsonable(value):
    if isinstance(value, BaseException):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": _jsonable(details or []),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def on_validation_error(_request, exc: RequestValidationError):
    return _error(
        422,
        "validation_error",
        "The request parameters are not valid.",
        exc.errors(),
    )


@app.exception_handler(ValidationError)
async def on_pydantic_error(_request, exc: ValidationError):
    return _error(422, "validation_error", "The request parameters are not valid.", exc.errors())


@app.exception_handler(StarletteHTTPException)
async def on_http_error(_request, exc: StarletteHTTPException):
    return _error(exc.status_code, "http_error", str(exc.detail))


@app.exception_handler(Exception)
async def on_unexpected(_request, exc: Exception):
    return _error(500, "server_error", f"The simulator failed: {exc.__class__.__name__}: {exc}")


def _run(body: SimulateRequest) -> dict:
    return run_comparison(
        horizon=body.horizon,
        seeds=body.resolved_seeds(),
        policies=body.resolved_policies(),
        initial_stock_fraction=body.initial_stock_fraction,
        weekly_demand=body.weekly_demand,
        discount=body.discount,
        ucb_c=body.ucb_c,
        wastage=body.wastage,
        preset=body.preset,
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "adaptive-blood-drive-scheduling"}


@app.get("/api/v1/config")
def config():
    return {
        "blood_types": list(BLOOD_TYPES),
        "priority": PRIORITY,
        "population_mix": POPULATION_MIX,
        "demand_share": DEMAND_SHARE,
        "loyalty_rate": {str(k): v for k, v in LOYALTY_RATE.items()},
        "reward": {
            "formula": "sum(units_collected[k] * priority[k] * (0.1 + shortage[k]))",
            "scale_used_by_learners": REWARD_SCALE,
            "displayed_reward": "raw, before dividing by the learning scale",
        },
        "defaults": {
            "horizon": DEFAULT_HORIZON,
            "seeds": 10,
            "discount": DEFAULT_DISCOUNT,
            "ucb_c": DEFAULT_UCB_C,
            "weekly_demand": DEFAULT_WEEKLY_DEMAND,
            "wastage": DEFAULT_WASTAGE,
            "initial_stock_fraction": DEFAULT_INITIAL_STOCK_FRACTION,
            "target_weeks_of_demand": 2,
        },
        "presets": {"quick": QUICK_PRESET, "full": FULL_PRESET},
        "policies": [
            {"id": pid, "name": POLICIES[pid].name}
            for pid in POLICY_ORDER
        ],
        "week_order": list(WEEK_ORDER),
        "assumptions": list(ASSUMPTIONS),
        "arms": [arm["id"] for arm in ARMS],
    }


@app.get("/api/v1/data-quality")
def data_quality():
    report = run_audit()
    try:
        write_reports(report)
    except OSError:
        pass
    return report


@app.get("/api/v1/arms")
def arms(week: int = Query(default=1, ge=1, le=520)):
    week_index = week - 1
    target = target_stock(DEFAULT_WEEKLY_DEMAND)
    stock = DEFAULT_INITIAL_STOCK_FRACTION * target
    shortage = shortage_vector(stock, target)
    payload = []
    for index, arm in enumerate(ARMS):
        payload.append(
            {
                **arm,
                "loyalty_rate": LOYALTY_RATE[arm["tier"]],
                "report_table_mean_donors": REPORT_TABLE_MEAN_DONORS[arm["id"]],
                "week": week,
                "seasonal_multiplier": seasonal_multiplier(index, week_index),
                "turnout_probability": turnout_probability(index, week_index),
                "expected_turnout": expected_turnout(index, week_index),
                "expected_reward_at_initial_stock": expected_reward(index, week_index, shortage),
                "expected_reward_note": (
                    "Mean-field reward at 60% of target stock and the default demand of 90. "
                    "Not a sampled drive."
                ),
            }
        )
    return {"week": week, "arms": payload, "n_arms": N_ARMS}


@app.post("/api/v1/simulate")
def simulate(body: SimulateRequest):
    return _run(body)


@app.post("/api/v1/compare")
def compare(body: SimulateRequest, format: str = Query(default="json")):
    if format not in {"json", "csv"}:
        return _error(422, "validation_error", "format must be json or csv")
    # Comparison always evaluates the six policies on a shared seed set.
    body.policies = None
    result = _run(body)
    if format == "csv":
        return PlainTextResponse(comparison_to_csv(result), media_type="text/csv")
    return result


@app.post("/api/v1/sensitivity")
def sensitivity(body: SensitivityRequest):
    return run_sensitivity(
        horizon=body.horizon,
        seeds=list(range(body.n_seeds)),
        discount_grid=body.discount_grid,
        ucb_c=body.ucb_c,
        initial_stock_fraction=body.initial_stock_fraction,
        weekly_demand=body.weekly_demand,
        wastage=body.wastage,
    )


@app.post("/api/v1/recommend")
def recommend_drive(body: RecommendRequest):
    return recommend(
        policy_id=body.policy,
        horizon=body.horizon,
        seed=body.seed,
        initial_stock_fraction=body.initial_stock_fraction,
        weekly_demand=body.weekly_demand,
        discount=body.discount,
        ucb_c=body.ucb_c,
        wastage=body.wastage,
    )


def _plan(body: PlanRequest) -> dict:
    return plan_drive(
        facility_name=body.facility_name,
        planning_date=body.planning_date,
        horizon=body.horizon,
        weekly_demand=body.weekly_demand,
        stock=body.stock,
        target=body.target,
        arm_ids=body.arms,
        policy_id=body.policy,
        objective=body.objective,
        discount=body.discount,
        ucb_c=body.ucb_c,
        seed=body.seed,
        wastage=body.wastage,
    )


@app.post("/api/v1/plan")
def create_plan(body: PlanRequest):
    return _plan(body)


@app.post("/api/v1/plan/compare")
def create_plan_compare(body: PlanRequest):
    return compare_plan(
        planning_date=body.planning_date,
        horizon=body.horizon,
        weekly_demand=body.weekly_demand,
        stock=body.stock,
        target=body.target,
        arm_ids=body.arms,
        objective=body.objective,
        discount=body.discount,
        ucb_c=body.ucb_c,
        seed=body.seed,
        wastage=body.wastage,
        selected_policy=body.policy,
    )
