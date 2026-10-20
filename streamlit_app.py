"""HEMORA — Blood Drive Intelligence.

Run: streamlit run streamlit_app.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.advice import (
    DISPLAY_ORDER,
    LABELS,
    SLOTS,
    advise,
    demo_levels,
    inventory_rows,
    parse_inventory_csv,
)
from app.config import ARMS
from app.experiment import compare_plan

st.set_page_config(
    page_title="HEMORA · Blood Drive Intelligence",
    page_icon="H",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#192A38"
IVORY = "#F7F5F0"
BURGUNDY = "#8E4249"
LINE = "#E4DDD4"

ARM_IDS = [arm["id"] for arm in ARMS]
ARM_NAMES = {arm["id"]: arm["name"] for arm in ARMS}
POLICIES = [
    ("discounted_ucb", "Discounted UCB"),
    ("ucb1", "UCB1"),
    ("greedy", "Greedy"),
    ("discounted_thompson", "Discounted Thompson Sampling"),
    ("fixed_rotation", "Fixed Rotation"),
    ("random", "Random"),
]
GOALS = [
    ("shortage", "Fill current gaps"),
    ("weighted", "Also count extra units"),
    ("o_negative", "Focus on O-negative"),
]


def init_state() -> None:
    if st.session_state.get("ready"):
        return
    stock, target = demo_levels(90)
    st.session_state.ready = True
    st.session_state.nav = "Home"
    st.session_state.facility = ""
    st.session_state.demand = 90
    st.session_state.horizon = 4
    st.session_state.using_demo = True
    st.session_state.show_form = True
    st.session_state.arms = list(ARM_IDS)
    st.session_state.policy = "discounted_ucb"
    st.session_state.objective = "shortage"
    st.session_state.discount = 0.95
    st.session_state.ucb = 0.1
    st.session_state.seed = 0
    st.session_state.result = None
    st.session_state.compare = None
    st.session_state.form_error = ""
    for blood, amount in stock.items():
        st.session_state[f"stock_{blood}"] = int(amount)
        st.session_state[f"target_{blood}"] = int(target[blood])


def apply_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {IVORY}; color: {NAVY}; }}
        .block-container {{ max-width: 1080px; padding-top: 1.25rem; }}
        [data-testid="stSidebar"] {{ background: {NAVY} !important; }}
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2 {{ color: {IVORY} !important; }}
        [data-testid="stSidebar"] hr {{ border-color: rgba(247,245,240,0.15); }}
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {{
          background-color: #ffffff !important;
          color: {NAVY} !important;
          border-color: {LINE} !important;
        }}
        div[data-baseweb="select"] span,
        div[data-baseweb="input"] input {{ color: {NAVY} !important; }}
        h1, h2, h3 {{ color: {NAVY}; letter-spacing: -0.02em; }}
        .kicker {{ color: {BURGUNDY}; font-size: 0.75rem; font-weight: 650; letter-spacing: 0.14em; text-transform: uppercase; margin: 0; }}
        .lede {{ font-size: 1.08rem; line-height: 1.5; color: #4E5963; margin: 0.4rem 0 0.8rem; }}
        .card {{ background: white; border: 1px solid {LINE}; border-radius: 12px; padding: 1rem 1.15rem 0.9rem; }}
        .rec {{ background: white; border: 1px solid {LINE}; border-left: 4px solid {BURGUNDY}; border-radius: 12px; padding: 1.1rem 1.25rem 0.4rem; }}
        .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.7rem; margin: 0.8rem 0 0.2rem; }}
        .metric {{ background: white; border: 1px solid {LINE}; border-radius: 12px; padding: 0.75rem 0.85rem; }}
        .metric span {{ display: block; color: #5C6770; font-size: 0.82rem; line-height: 1.3; }}
        .metric strong {{ display: block; color: {NAVY}; font-size: 1.35rem; margin-top: 0.2rem; }}
        .note {{ color: #5C6770; font-size: 0.92rem; }}
        .sample {{ background: white; border: 1px solid {LINE}; border-radius: 10px; padding: 0.55rem 0.8rem; color: {NAVY}; font-size: 0.92rem; }}
        @media (max-width: 900px) {{
          .metrics {{ grid-template-columns: 1fr 1fr; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def levels_from_state() -> tuple[dict[str, float], dict[str, float]]:
    stock = {blood: float(st.session_state[f"stock_{blood}"]) for blood in LABELS}
    target = {blood: float(st.session_state[f"target_{blood}"]) for blood in LABELS}
    return stock, target


def load_demo() -> None:
    demand = float(st.session_state.get("demand") or 90)
    stock, target = demo_levels(demand)
    st.session_state.facility = "Example City Blood Bank"
    st.session_state.using_demo = True
    st.session_state.arms = list(ARM_IDS)
    for blood, amount in stock.items():
        st.session_state[f"stock_{blood}"] = int(amount)
        st.session_state[f"target_{blood}"] = int(target[blood])


def sync_sample_flag() -> None:
    stock, target = levels_from_state()
    sample_stock, sample_target = demo_levels(float(st.session_state.demand))
    st.session_state.using_demo = all(
        stock[blood] == sample_stock[blood] and target[blood] == sample_target[blood]
        for blood in stock
    )


def open_plan() -> None:
    st.session_state.nav = "Plan a drive"
    st.session_state.show_form = True


def current_plan() -> dict:
    stock, target = levels_from_state()
    return advise(
        facility_name=st.session_state.facility,
        horizon=int(st.session_state.horizon),
        weekly_demand=float(st.session_state.demand),
        stock=stock,
        target=target,
        arm_ids=list(st.session_state.arms),
        policy_id=st.session_state.policy,
        objective=st.session_state.objective,
        discount=float(st.session_state.discount),
        ucb_c=float(st.session_state.ucb),
        seed=int(st.session_state.seed),
        on_date=date.today(),
    )


def stock_chart(rows: list[dict]) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(name="Current stock", x=[row["blood_type"] for row in rows], y=[row["current_stock"] for row in rows], marker_color=NAVY)
    fig.add_bar(name="Target", x=[row["blood_type"] for row in rows], y=[row["target_stock"] for row in rows], marker_color=BURGUNDY)
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": NAVY, "size": 13},
        legend={"orientation": "h", "y": 1.12},
        margin={"l": 8, "r": 8, "t": 28, "b": 8},
        height=340,
        yaxis_title="Units",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#EFEAE3", zeroline=False)
    return fig


def render_result(result: dict) -> None:
    drive = result["recommended"]
    recommended_after = result["after_one_drive"]
    projection = result["projection"]
    shelf = projection["final_total"]
    priority_caption = (
        "All estimated units are types below target"
        if abs(drive["priority_units"] - drive["estimated_units"]) < 0.5
        else "Estimated units of types below target"
    )
    st.markdown('<div class="rec">', unsafe_allow_html=True)
    st.markdown('<p class="kicker">Recommended drive</p>', unsafe_allow_html=True)
    st.markdown(f"## {drive['name']}")
    st.markdown(f"**{drive['slot']}**")
    st.markdown("**Why this option?**")
    for reason in result["reasons"]:
        st.markdown(f"- {reason}")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="metrics">
          <div class="metric"><span>Estimated donations, one unit each</span><strong>{drive['estimated_donations']:.0f}</strong></div>
          <div class="metric"><span>{priority_caption}</span><strong>{drive['priority_units']:.0f}</strong></div>
          <div class="metric"><span>Shortages this drive can help</span><strong>{drive['shortages_helped']} of {drive['shortages_open']}</strong></div>
          <div class="metric"><span>Projected shelf after {projection['weeks']} weeks</span><strong>{shelf:.0f} units</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="note">Planning estimates based on the selected model and inputs. Each donation is counted as one unit.</p>',
        unsafe_allow_html=True,
    )
    if "reach zero" in projection["note"].lower():
        st.caption(projection["note"])

    table = pd.DataFrame(
        [
            {
                "Drive option": row["name"],
                "Estimated collection": round(row["estimated_donations"]),
                "Priority shortage coverage": f"{row['gap_units']:.0f} units toward gaps",
                "Recommendation": row["label"],
            }
            for row in result["options"]
        ]
    )
    st.markdown("### Other drives you allowed")
    st.caption(result["objective_note"])
    st.dataframe(table, hide_index=True, width="stretch")

    names = [row["name"] for row in result["options"]]
    chosen_name = st.selectbox("Inspect another drive", names, index=0)
    chosen = next(row for row in result["options"] if row["name"] == chosen_name)
    left, right = st.columns(2)
    compare_frame = pd.DataFrame(
        {
            "Blood type": [LABELS[blood] for blood in DISPLAY_ORDER],
            f"{drive['name']} (recommended)": [
                round(recommended_after[blood], 1) for blood in DISPLAY_ORDER
            ],
            f"{chosen['name']} (inspected)": [
                round(chosen["after_one_drive"][blood], 1) for blood in DISPLAY_ORDER
            ],
        }
    )
    with left:
        st.markdown("**Projected shelf after one drive**")
        st.caption("Average patient need for one week, not a record of today's stock.")
    with right:
        st.dataframe(compare_frame, hide_index=True, width="stretch")

    with st.expander("What the shelf looks like after the full plan"):
        balance = pd.DataFrame(
            [
                {
                    "Blood type": LABELS[blood],
                    "You entered": round(projection["opening_stock"][blood]),
                    "Collected in the path": round(projection["collected"][blood], 1),
                    "Used for patients": round(projection["patient_use"][blood], 1),
                    "Counted unusable": round(projection["unusable"][blood], 1),
                    "Projected remaining": round(projection["final_stock"][blood], 1),
                }
                for blood in DISPLAY_ORDER
            ]
        )
        st.dataframe(balance, hide_index=True, width="stretch")
        st.markdown(projection["note"])

    with st.expander("How the model decided"):
        st.markdown(result["learning"]["note"])
        st.markdown(
            f"The ordering score for {drive['name']} is {drive['score']:.1f}. "
            "A higher score means a better estimated match to the goal you selected. It is not a count of donors."
        )
        st.markdown(
            f"Seasonal patterns use calendar week {result['calendar_week']} of this year. "
            "Campus, mall, and workplace drives change with the time of year. "
            "The community-centre slowdown and the tech-park opening follow the number of weeks in the plan."
        )


def page_home() -> None:
    st.markdown('<p class="kicker">HEMORA</p>', unsafe_allow_html=True)
    st.markdown("# Plan the right drive. Meet the right need.")
    st.markdown(
        '<p class="lede">Turn blood inventory insights into clear, actionable donation-drive recommendations.</p>',
        unsafe_allow_html=True,
    )
    if st.session_state.using_demo:
        st.markdown(
            '<p class="sample">Sample inventory is on screen so you can look around. It is not a hospital record.</p>',
            unsafe_allow_html=True,
        )
    stock, target = levels_from_state()
    rows = inventory_rows(stock, target)
    short = sum(1 for row in rows if row["units_short"] > 0)
    critical = sum(1 for row in rows if row["status"] == "Critical")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="card"><p class="kicker">Tracking</p><h3>{len(rows)} blood types</h3></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="card"><p class="kicker">Below target</p><h3>{short} shortages</h3></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="card"><p class="kicker">Needs attention</p><h3>{critical} critical</h3></div>', unsafe_allow_html=True)
    st.write("")
    st.button("Plan a drive", type="primary", on_click=open_plan)
    st.plotly_chart(stock_chart(rows), width="stretch")


def page_plan() -> None:
    result = st.session_state.result
    if result and not st.session_state.show_form:
        render_result(result)
        left, right = st.columns(2)
        with left:
            if st.button("Change inputs"):
                st.session_state.show_form = True
                st.rerun()
        with right:
            if st.button("Run again", type="primary"):
                try:
                    st.session_state.result = current_plan()
                    st.session_state.compare = None
                    st.session_state.form_error = ""
                except ValueError as exc:
                    st.session_state.form_error = str(exc)
                st.rerun()
        if st.session_state.form_error:
            st.error(st.session_state.form_error)
        return

    st.markdown('<p class="kicker">Plan a drive</p>', unsafe_allow_html=True)
    st.markdown("# Tell us what you have on the shelf.")
    st.markdown(
        '<p class="lede">Enter stock, targets, and the drives you can run. The suggestion is calculated from those numbers.</p>',
        unsafe_allow_html=True,
    )
    if st.session_state.using_demo:
        st.markdown(
            '<p class="sample">These starting numbers are a sample, not a hospital record. Change any field and they become your entries.</p>',
            unsafe_allow_html=True,
        )
    if st.session_state.form_error:
        st.error(st.session_state.form_error)

    st.button("Load demo data", on_click=load_demo)
    uploaded = st.file_uploader("Upload inventory CSV", type=["csv"])
    if uploaded is not None:
        parsed = parse_inventory_csv(uploaded.getvalue().decode("utf-8", errors="replace"))
        if parsed["errors"]:
            for error in parsed["errors"]:
                st.error(error)
        else:
            preview = pd.DataFrame(
                [
                    {
                        "Blood type": LABELS[blood],
                        "Current stock": parsed["stock"].get(blood, "—"),
                        "Target stock": parsed["target"].get(blood, "—"),
                    }
                    for blood in DISPLAY_ORDER
                    if blood in parsed["stock"] or blood in parsed["target"]
                ]
            )
            st.dataframe(preview, hide_index=True, width="stretch")
            for note in parsed["notes"]:
                st.caption(note)
            if st.button("Use this file"):
                for blood, amount in parsed["stock"].items():
                    st.session_state[f"stock_{blood}"] = amount
                for blood, amount in parsed["target"].items():
                    st.session_state[f"target_{blood}"] = amount
                st.session_state.using_demo = False
                st.rerun()

    with st.form("plan"):
        st.markdown("### Planning details")
        st.text_input("Blood-bank name", key="facility", placeholder="Optional")
        a, b = st.columns(2)
        with a:
            st.number_input("Expected weekly demand (units)", min_value=0.0, max_value=5000.0, step=1.0, key="demand")
        with b:
            st.number_input("Planning horizon (weeks)", min_value=1, max_value=104, step=1, key="horizon")

        st.markdown("### Current inventory")
        st.caption("Units on the shelf, and the level you want to hold.")
        header = st.columns([1.4, 1, 1])
        header[1].markdown("**Current stock**")
        header[2].markdown("**Target stock**")
        for blood in DISPLAY_ORDER:
            cols = st.columns([1.4, 1, 1])
            cols[0].markdown(LABELS[blood])
            cols[1].number_input(
                f"Current {LABELS[blood]}",
                min_value=0.0,
                max_value=1_000_000.0,
                step=1.0,
                key=f"stock_{blood}",
                label_visibility="collapsed",
            )
            cols[2].number_input(
                f"Target {LABELS[blood]}",
                min_value=0.0,
                max_value=1_000_000.0,
                step=1.0,
                key=f"target_{blood}",
                label_visibility="collapsed",
            )

        st.markdown("### Available drives")
        st.multiselect(
            "Drives you can run",
            options=ARM_IDS,
            format_func=lambda arm_id: ARM_NAMES[arm_id],
            key="arms",
        )

        with st.expander("Advanced settings"):
            st.selectbox("Planning method", options=[item[0] for item in POLICIES], format_func=lambda value: dict(POLICIES)[value], key="policy")
            st.selectbox("What the score should favour", options=[item[0] for item in GOALS], format_func=lambda value: dict(GOALS)[value], key="objective")
            c, d, e = st.columns(3)
            with c:
                st.number_input("How fast old weeks fade", min_value=0.05, max_value=1.0, step=0.05, key="discount")
            with d:
                st.number_input("Extra weight for less-used drives", min_value=0.01, max_value=5.0, step=0.01, key="ucb")
            with e:
                st.number_input("Random seed", min_value=0, max_value=1_000_000, step=1, key="seed")
            st.caption("Leave these as they are unless you are comparing planning methods. The main suggestion still uses your stock.")

        submitted = st.form_submit_button("Generate Recommendation", type="primary")

    if submitted:
        if not st.session_state.arms:
            st.session_state.form_error = "Choose at least one drive."
            st.rerun()
        try:
            sync_sample_flag()
            st.session_state.result = current_plan()
            st.session_state.compare = None
            st.session_state.form_error = ""
            st.session_state.show_form = False
        except ValueError as exc:
            st.session_state.form_error = str(exc)
        st.rerun()


def page_inventory() -> None:
    st.markdown('<p class="kicker">Inventory</p>', unsafe_allow_html=True)
    st.markdown("# Stock against the targets you set")
    if st.session_state.using_demo:
        st.markdown('<p class="sample">Sample data. Load your own numbers from Plan a drive.</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="note">These figures are what you entered. They are not a live hospital feed.</p>', unsafe_allow_html=True)
    stock, target = levels_from_state()
    rows = inventory_rows(stock, target)
    st.plotly_chart(stock_chart(rows), width="stretch")
    frame = pd.DataFrame(
        [
            {
                "Blood type": row["blood_type"],
                "Current stock": round(row["current_stock"]),
                "Target stock": round(row["target_stock"]),
                "Units short": round(row["units_short"]),
                "Status": row["status"],
            }
            for row in rows
        ]
    )
    st.dataframe(frame, hide_index=True, width="stretch")
    st.caption(
        "Critical means you have less than half of the target. Low means you are below target but still have at least half. Adequate means you are at or above target."
    )
    result = st.session_state.result
    if result:
        st.markdown("### Projected shelf")
        st.markdown(result["projection"]["note"])


def page_compare() -> None:
    st.markdown('<p class="kicker">Compare</p>', unsafe_allow_html=True)
    st.markdown("# Six ways to practice the same plan")
    st.markdown(
        '<p class="lede">Each method sees the same stock, the same drives, and the same simulated weeks. The numbers are practice totals, not a promise about the next drive.</p>',
        unsafe_allow_html=True,
    )
    if st.button("Compare methods", type="primary"):
        stock, target = levels_from_state()
        try:
            st.session_state.compare = compare_plan(
                planning_date=date.today().isoformat(),
                horizon=int(st.session_state.horizon),
                weekly_demand=float(st.session_state.demand),
                stock=stock,
                target=target,
                arm_ids=list(st.session_state.arms) or list(ARM_IDS),
                objective=st.session_state.objective,
                discount=float(st.session_state.discount),
                ucb_c=float(st.session_state.ucb),
                seed=int(st.session_state.seed),
                wastage=0.02,
                selected_policy=st.session_state.policy,
            )
        except ValueError as exc:
            st.error(str(exc))
    comparison = st.session_state.compare
    if not comparison:
        return
    frame = pd.DataFrame(
        [
            {
                "Method": row["name"],
                "Drive it would try next": row["recommended_name"],
                "Units collected in the practice run": round(row["simulated_units"]),
                "O-negative units": round(row["simulated_o_negative_units"], 1),
                "Score for the selected goal": round(row["simulated_objective_score"]),
            }
            for row in comparison["rows"]
        ]
    )
    st.dataframe(frame, hide_index=True, width="stretch")
    st.caption(comparison["note"])
    st.caption("Variation across seeds is available by changing the random seed under Advanced settings on the plan form, then comparing again.")


@st.cache_data
def donor_file_summary() -> str:
    from app.data_audit import load_frame

    frame, parsing = load_frame()
    donated = frame["Donated"].dropna()
    positives = int((donated == 1).sum())
    return (
        f"The stored UCI file has {parsing['rows_read']} donor rows. "
        f"{positives} of them returned to donate in the recorded window "
        f"({positives / len(donated):.1%}). "
        "Recency, frequency, and time describe past visits. They do not name a blood type or a drive site."
    )


def page_method() -> None:
    st.markdown('<p class="kicker">Methodology and data</p>', unsafe_allow_html=True)
    st.markdown("# Where the numbers come from")
    try:
        st.markdown(donor_file_summary())
    except FileNotFoundError:
        st.markdown("The UCI donor file was not found next to the application.")
    st.markdown(
        "Planning estimates are based on the selected model and the inventory you enter. "
        "They are not a live connection to a hospital, and they are not a count of people who have already donated."
    )
    st.markdown(
        """
- Historical donor timing comes from the UCI Blood Transfusion Service Center file already stored with this project. That file has no blood types, drive sites, or hospital stock.
- Blood-type mix, weekly patient need, and seasonal swings are configured assumptions. O-negative is about 7% of donors in the base mix, and three drives are modelled with a higher O-negative share.
- Each estimated donation is one unit. The unit is then assigned to a blood type.
- A drive is recommended by scoring every drive you allowed against the gap between your current stock and your target. The learning methods still practice over the planning horizon, and their practice totals are on the Compare page.
- About 2% of stock already on the shelf is treated as unusable each week. If patient need is larger than collections, the projected shelf can reach zero. That projection is separate from the stock you typed in.
        """
    )
    st.caption(f"Drives you can choose: {', '.join(SLOTS.values())}.")


def main() -> None:
    init_state()
    apply_css()
    st.sidebar.markdown("## HEMORA")
    st.sidebar.caption("Blood Drive Intelligence")
    st.sidebar.radio(
        "Go to",
        ["Home", "Plan a drive", "Inventory", "Compare", "Methodology"],
        key="nav",
        label_visibility="collapsed",
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Planning estimates based on the selected model and inputs.")
    pages = {
        "Home": page_home,
        "Plan a drive": page_plan,
        "Inventory": page_inventory,
        "Compare": page_compare,
        "Methodology": page_method,
    }
    pages[st.session_state.nav]()


main()
