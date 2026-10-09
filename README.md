# TMD 3 – AI-Assisted Transfer Planner (Full-Workforce Reconciled Build)

## Run in VS Code on Windows
1. Extract this ZIP and open the extracted folder in VS Code.
2. Open Terminal → New Terminal.
3. Run `py -m venv .venv`.
4. In PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and then `./.venv/Scripts/Activate.ps1`.
5. Run `python -m pip install -r requirements.txt`.
6. Run `python -m streamlit run app.py`.
7. Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Annual workforce workflow
- The app screens all 5,000 master records on every HRMD CO run, regardless of how many preference rows are uploaded.
- Use `TMD3_Batch_Cycle_Input_Template.xlsx`, which has one row for every officer and intentionally blank preference fields. Do not invent preferences; fill them from authorised submissions.
- Officers due for transfer but without five valid unique preferences are flagged `PREFERENCES MISSING — HRMD ACTION`; they are not silently allocated.
- A partial input file can be used for testing, but the app warns that the annual plan is incomplete while preference records are missing. Do not treat a partial run as a final annual plan.
- The export includes a 5,000-row decision register, policy screening and the allocation-only table.

## Reconciliation
The workbook contains exactly 5,000 synthetic officer records. Agartala Grade A is 8 and Agartala total is 25, following the user's explicit correction. Centre totals and grade cells reconcile to the same officer master. Skill profile has been removed from the master workbook, interface and scoring.

## Data and limitations
Posting histories and other employee attributes in this capstone prototype are generated test data, not verified historical records. The employee view labels these records accordingly. Replace them with authorised, verified data before operational use. This is not a production-ready HR decision system; policy, security, fairness, capacity and end-to-end UI testing require authorised review.


Mandatory preference rule: before a whole-workforce plan can be generated, every officer identified as routine transfer-due must have exactly five valid, distinct destination preferences. Missing, duplicate, unknown-centre, current-centre, or grade/zone-invalid preferences block final allocation. The app displays the due officers needing correction and provides a completion template. No preferences or destinations are invented.
