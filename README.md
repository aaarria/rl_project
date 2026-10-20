# HEMORA

Blood Drive Intelligence. A Streamlit app that turns the stock a blood bank enters into one donation-drive recommendation.

The suggestion is calculated by the project simulator. It is a planning estimate, not a live hospital feed and not a copy of the scores in the research report.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open the local URL Streamlit prints, usually http://localhost:8501.

The app reads `transfusion.data` from this folder. It does not download data when it starts.

## What you can do

- Home shows how many blood types are below the target. The first visit uses labeled sample stock.
- Plan a drive accepts a facility name, weekly demand, a planning length, current stock, target stock, and the drives you can run. A CSV can fill the stock fields after you preview it.
- The recommendation scores every allowed drive against the gap between current stock and target. Each estimated donation is one unit, then split by blood type.
- Inventory shows the numbers you entered. A later projection, when you have generated one, is labeled separately and explains demand and wastage if the shelf reaches zero.
- Compare runs the six planning methods on the same simulated weeks.
- Methodology and data states what comes from the UCI file and what is a configured assumption.

Advanced settings (planning method, goal, discount, exploration weight, seed) stay inside an expander. The default goal fills current gaps. It does not change the research reward formula used by the learning methods.

## Tests

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Streamlit Community Cloud

This repository is prepared for Community Cloud. Deployment is not claimed here until the app is actually deployed.

- Main file: `streamlit_app.py`
- Python packages: `requirements.txt` at the repository root
- Python version: `runtime.txt` (`python-3.12`)
- Theme: `.streamlit/config.toml`
- Keep `transfusion.data` in the repository so the app does not fetch it

## Research API

`backend/` still contains the FastAPI service and the Next.js dashboard in `frontend/`. They are not required to use HEMORA. To run the API:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

## Data

`transfusion.data` is the UCI Blood Transfusion Service Center file. It records recency, frequency, monetary value, time, and whether the donor returned. It has no blood types, drive sites, or hospital stock. Blood-type mix, weekly patient need, and seasonal swings are labeled assumptions in `backend/app/config.py`.
