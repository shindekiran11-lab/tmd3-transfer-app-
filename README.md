# TMD 3 – AI-Assisted Transfer Planner (Reconciled Build)

## Run in VS Code on Windows
1. Open this extracted folder in VS Code.
2. In Terminal → New Terminal, run `py -m venv .venv`.
3. Activate in PowerShell: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` then `./.venv/Scripts/Activate.ps1`.
4. Run `python -m pip install -r requirements.txt`.
5. Run `python -m streamlit run app.py`.
6. Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Reconciliation and limitations
The workbook is reconciled to exactly 5,000 synthetic officer records. Agartala Grade A is 8 and Agartala total is 25, following the user's explicit correction. Centre-wise grade and centre-wise cadre counts are derived from the same Officer_Master used by the app. Skill profile has been removed from scoring and dashboard views. Employee output uses the HRMD CO whole-batch result when available; no unsupported likelihood percentage is shown.

This is a capstone prototype using synthetic data, not a production-ready HR decision system. All policy assumptions, data quality, security, fairness, and final transfer decisions require authorised human validation.
