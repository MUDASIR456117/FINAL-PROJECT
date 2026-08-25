# FINAL-PROJECT

# AI Financial Advisor

A clean, local-first personal finance dashboard based on the supplied project plan. It includes six Streamlit sections, a reusable Pandas finance engine, ML/DL predictions, a FastAPI service layer, and MongoDB connectivity.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
	pip install -r requirements.txt
Copy-Item .env.example .env
# Add your MongoDB Atlas URI to .env
streamlit run frontend\streamlit_app.py
```

API:

```powershell
uvicorn backend.main:app --reload
```

For Vercel, deploy the FastAPI backend with `vercel.json`; the API root will be available at your Vercel URL and the interactive docs at `/docs`. Streamlit should be deployed separately on Streamlit Community Cloud or Render.

## Deployment hosts

This repository contains two different apps:

- Deploy the `frontend/streamlit_app.py` file to Streamlit Community Cloud or Render. Netlify cannot run a Streamlit server, so deploying this repository as a Netlify site results in a page-not-found response.
- Deploy the FastAPI API to Vercel using `vercel.json`, or to a Python server host with `uvicorn backend.main:app`.

When deploying the Streamlit app, set the main file to `frontend/streamlit_app.py` and use `frontend/requirements.txt` for its dependencies. The root `requirements.txt` is intentionally API-only so Vercel stays below its 500 MB serverless function limit.

Database connectivity can be checked at `http://localhost:8000/health/database`.

The DL backend defaults to a NumPy neural network. TensorFlow is intentionally excluded from the Vercel requirements because its package exceeds Vercel's serverless function size limit. Install TensorFlow separately only for local use, then set `DL_BACKEND=tensorflow` after it imports successfully.

Tests:

```powershell
python -m pytest
```
