"""Central simulation configuration.

Numeric values that the project report states explicitly are used as stated.
Where the report describes a pattern without a numeric table, the assumption
is named in ASSUMPTIONS and returned by the API.
"""

from __future__ import annotations

BLOOD_TYPES: tuple[str, ...] = (
    "O-",
    "O+",
    "A-",
    "A+",
    "B-",
    "B+",
    "AB-",
    "AB+",
)

# Clinical priority weights from the report.
PRIORITY: dict[str, float] = {
    "O-": 2.0,
    "O+": 1.0,
    "A-": 1.3,
    "A+": 1.0,
    "B-": 1.5,
    "B+": 1.0,
    "AB-": 1.5,
    "AB+": 1.0,
}

# Red Cross-style population shares. The report states O-negative is about 7%
# and that the mix is a population distribution; it does not print the other
# seven shares. These eight values sum to 1 and keep O- at 7%.
POPULATION_MIX: dict[str, float] = {
    "O-": 0.07,
    "O+": 0.38,
    "A-": 0.06,
    "A+": 0.34,
    "B-": 0.02,
    "B+": 0.09,
    "AB-": 0.01,
    "AB+": 0.03,
}

# Demand shares. The report says O-negative is over-represented relative to
# the donor mix because it is the universal donor. Four percentage points are
# moved from O+ to O- so the shares still sum to 1. This vector is synthetic.
DEMAND_SHARE: dict[str, float] = {
    "O-": 0.11,
    "O+": 0.34,
    "A-": 0.06,
    "A+": 0.34,
    "B-": 0.02,
    "B+": 0.09,
    "AB-": 0.01,
    "AB+": 0.03,
}

# UCI-derived loyalty tiers. Endpoints 14.4% and 36.6% are the report's
# frequency-quartile anchors. 21.8% and 29.2% are the report's linear
# interpolations, not separate empirical estimates.
LOYALTY_RATE: dict[int, float] = {
    1: 0.144,
    2: 0.218,
    3: 0.292,
    4: 0.366,
}

# The report says three sites have a higher O-negative share. It does not
# name them. These three are the labeled choice used by the simulator.
O_NEGATIVE_BOOSTED_ARMS: frozenset[str] = frozenset(
    {"hospital_camp", "community_centre", "tech_park_evening"}
)
O_NEGATIVE_BOOST = 1.5

# Illustrative means printed in the report's Table 4. They are not hardcoded
# into the sampler. The sampler uses pool × loyalty × seasonal multiplier.
REPORT_TABLE_MEAN_DONORS: dict[str, float] = {
    "campus_weekday": 34,
    "campus_weekend": 15,
    "corporate_lunch": 52,
    "corporate_weekend": 17,
    "community_centre": 41,
    "mall_weekend": 39,
    "hospital_camp": 24,
    "tech_park_evening": 45,
}

ARMS: tuple[dict, ...] = (
    {
        "id": "campus_weekday",
        "name": "Campus Weekday",
        "tier": 1,
        "pool": 300,
        "pattern": "Low in summer and winter breaks (×0.30, inside the report's ×0.25–0.35 band) and exam-period peaks (×1.35).",
    },
    {
        "id": "campus_weekend",
        "name": "Campus Weekend",
        "tier": 1,
        "pool": 110,
        "pattern": "Weak academic dip in summer (×0.6); otherwise flat.",
    },
    {
        "id": "corporate_lunch",
        "name": "Corporate Lunch",
        "tier": 3,
        "pool": 170,
        "pattern": "CSR peaks in two six-week windows per year (×1.9); ×0.75 otherwise.",
    },
    {
        "id": "corporate_weekend",
        "name": "Corporate Weekend",
        "tier": 2,
        "pool": 70,
        "pattern": "Flat.",
    },
    {
        "id": "community_centre",
        "name": "Community Centre",
        "tier": 4,
        "pool": 130,
        "pattern": "Flat until week 30, then a linear decay to ×0.55 at week 104.",
    },
    {
        "id": "mall_weekend",
        "name": "Mall Weekend",
        "tier": 1,
        "pool": 250,
        "pattern": "Festival-season peak (×1.8 for twelve weeks); ×0.85 otherwise.",
    },
    {
        "id": "hospital_camp",
        "name": "Hospital Camp",
        "tier": 4,
        "pool": 60,
        "pattern": "Flat.",
    },
    {
        "id": "tech_park_evening",
        "name": "Tech-Park Evening",
        "tier": 3,
        "pool": 90,
        "pattern": "New site: ×0.3 through week 40, then a linear ramp to ×2.6 at week 104.",
    },
)

DEFAULT_WEEKLY_DEMAND = 90.0
DEFAULT_WASTAGE = 0.02
DEFAULT_INITIAL_STOCK_FRACTION = 0.6
DEFAULT_HORIZON = 104
DEFAULT_SEEDS = list(range(10))
DEFAULT_DISCOUNT = 0.95
DEFAULT_UCB_C = 0.1
REWARD_SCALE = 100.0
TARGET_WEEKS = 2.0
TURNOUT_CAP = 0.95
TS_PRIOR_MEAN = 0.5
TS_PRIOR_STRENGTH = 1.0
TS_SIGMA0 = 0.1

QUICK_PRESET = {"horizon": 52, "n_seeds": 3, "preset": "quick"}
FULL_PRESET = {"horizon": 104, "n_seeds": 10, "preset": "full"}

ASSUMPTIONS: tuple[str, ...] = (
    "The attached UCI file has donor RFM features and a March 2007 return label. It has no blood types, drive locations, hospital stock, or weekly turnout.",
    "The e-RaktKosh / NBTC extract described in the report is not in this workspace. Pool sizes and seasonal shapes follow the report's synthetic arm table.",
    "Population ABO/Rh shares use a Red Cross-style mix with O-negative fixed at 7%. The report does not print the other seven shares.",
    "Demand shares move four percentage points from O+ to O- so O-negative is over-represented, matching the report's description without a printed demand vector.",
    "Hospital Camp, Community Centre, and Tech-Park Evening are the three arms given a 1.5× O-negative share before renormalising. The report does not name those three sites.",
    "Seasonal multipliers use a 52-week calendar. Summer break is weeks-of-year 18–30, winter break is weeks 51–52 and 1–2, exams are weeks 10–14 and 42–46, CSR windows are weeks 8–13 and 32–37, and the festival peak is weeks 38–49.",
    "Campus weekday breaks use ×0.30, the midpoint of the report's ×0.25–0.35 range.",
    "Community Centre decays linearly from ×1 at week 30 to ×0.55 at week 104. Tech-Park Evening ramps linearly from ×0.3 at week 40 to ×2.6 at week 104. Horizons shorter than those anchors only see the early part of the pattern.",
    "Rewards passed to the learning rules are divided by 100. Cumulative reward in the API and UI is the raw shortage-weighted sum.",
    "Each seed pre-draws turnout, blood-type mix, and demand for every arm and week. Policies on the same seed face the same potential outcomes.",
)

WEEK_ORDER: tuple[str, ...] = (
    "Shortage is computed from current stock, before collection.",
    "The policy selects one arm from its own statistics.",
    "Turnout is the pre-drawn binomial count for that arm and week, capped by p = min(0.95, loyalty × seasonal multiplier).",
    "Collected units are the pre-drawn multinomial split of that turnout across eight ABO/Rh types.",
    "Raw reward is the sum over types of units × priority × (0.1 + shortage).",
    "The policy observes only that reward, divided by 100, and updates only the selected arm.",
    "Demand is the pre-drawn independent Poisson count for each type, with mean equal to weekly demand × that type's demand share.",
    "Wastage of 2% is applied to stock already on hand. New units are not wasted in the week they are collected.",
    "Stock becomes max(0, (1 − wastage) × stock + collected − demand). Inventory is never negative.",
)

LIMITATIONS = (
    "Policies that share a seed see the same pre-drawn week: the same demand, and the same collection each arm would have produced. "
    "A simulator that draws noise only after the arm is chosen would give each policy a different random stream, so rankings can move for that reason alone. "
    "Table 4 means in the report are illustrative. This simulator does not copy them or the Table 6 scores. "
    "The e-RaktKosh facility file is absent, so nothing here is an estimate for a real Indian blood bank."
)
