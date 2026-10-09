# TMD 3 – User Guide — Final Reconciled Build

## Run in VS Code on Windows
1. Extract this ZIP and open the extracted folder in VS Code.
2. Open Terminal → New Terminal.
3. Run `py -m venv .venv`.
4. Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and then `./.venv/Scripts/Activate.ps1` in PowerShell.
5. Run `python -m pip install -r requirements.txt`.
6. Run `python -m streamlit run app.py`.
7. Open `http://localhost:8501` if needed.

## HRMD CO
Upload the completed batch template and run the whole-batch plan. Review the preference demand summary, employee-reported sentiment (if provided), all-centre staffing and centre-wise grade distribution, retirement dashboards, exception queue and CO action queue. Export the plan for authorised review.

Optional template fields:
- `Employee_Sentiment`: employee-selected category.
- `Sentiment_Comment`: optional free-text comment.
- `Transfer_Concern`: optional structured concern/reason.

These are self-reported only. Do not infer sentiment from performance or personal attributes. Restrict access to comments.

## Employee view
Enter a synthetic Officer ID (0001–5000) and select five distinct preferences. To view the batch recommendation, HRMD CO must first run the complete batch with that officer included. The employee view will display the same whole-batch result when available; it will not display an unsupported probability percentage.

## Reconciled workforce data
The model contains 5,000 synthetic officer records. Agartala Grade A=8 and its centre total=25. The officer master, centre-wise grade totals, and centre × Grade × Cadre current staff counts reconcile. Skill profile is removed from the dashboard and scoring.

Synthetic data only; do not enter real personnel information in this capstone prototype.
