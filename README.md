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

Database connectivity can be checked at `http://localhost:8000/health/database`.

The DL backend defaults to a NumPy neural network so the app runs cleanly on Windows machines where TensorFlow native DLLs are unavailable. Set `DL_BACKEND=tensorflow` in `.env` only after TensorFlow imports successfully.

Tests:

```powershell
pytest
```
