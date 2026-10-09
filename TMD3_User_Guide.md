# TMD 3 – User Guide — Full-Workforce Reconciled Build

## Run in VS Code on Windows
1. Extract this ZIP and open the extracted folder in VS Code.
2. Open Terminal → New Terminal.
3. Run `py -m venv .venv`.
4. Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and then `./.venv/Scripts/Activate.ps1` in PowerShell.
5. Run `python -m pip install -r requirements.txt`.
6. Run `python -m streamlit run app.py`.
7. Open `http://localhost:8501` if needed.

## Annual whole-workforce run
1. Open `TMD3_Batch_Cycle_Input_Template.xlsx`. It contains all 5,000 Officer IDs.
2. Fill the five preference centres and zones from authorised employee submissions. Do not invent choices. Keep each Officer_ID unique and each officer's five preferences distinct and valid.
3. Fill optional request fields only from authorised records. Sentiment and comments are self-reported and optional.
4. Upload the completed file in HRMD CO and run the plan.
5. Review the 5,000-row decision register and the separate allocation table. Officers due for transfer but missing valid preferences are explicitly flagged for HRMD action.
6. Do not treat a partial input run as a complete annual transfer plan. The app will screen the 5,000-person master but allocations are limited to officers with valid preferences.

## Employee view
Enter an Officer ID (0001–5000). The employee view reads the latest completed 5,000-officer decision register saved by HRMD CO, including after a browser rerun or app restart. It verifies the transfer cycle and refuses to show stale or incomplete results. It does not display an unvalidated probability percentage.

## Reconciled workforce data
The model contains 5,000 synthetic officer records. Agartala Grade A=8 and its centre total=25. Centre totals, grade totals and Centre × Grade × Cadre counts reconcile to the master. Skill profile has been removed.

## Data caveat
Posting-history fields are illustrative generated test data, not verified historical records. Do not enter real personnel information into this capstone prototype. Obtain authorised validation of policy, data, security, fairness and allocation results before operational use.


Mandatory preference rule: before a whole-workforce plan can be generated, every officer identified as routine transfer-due must have exactly five valid, distinct destination preferences. Missing, duplicate, unknown-centre, current-centre, or grade/zone-invalid preferences block final allocation. The app displays the due officers needing correction and provides a completion template. No preferences or destinations are invented.


Employee-result integration: after a successful full-workforce run, the app writes `TMD3_Latest_Completed_Batch_Result.csv` and `TMD3_Latest_Completed_Batch_Result.json` to the project folder. Keep both files together with the app. If a new run is blocked by missing mandatory preferences, the previous result is marked unavailable so it is not represented as the current cycle result.

Preference requirement distinction: exactly five valid destination preferences are mandatory only for officers identified as routine transfer-due. Officers who are not due for routine transfer do not need to submit preferences; the employee view directs exceptional cases to Samadhan, subject to the applicable process. The completion report lists only transfer-due officers with missing or invalid preferences.

## Application modes

- **RO Employee Portal:** Read-only individual lookup for officer details, routine-transfer eligibility, and the final recommendation from the latest completed HRMD CO whole-workforce plan. It does not display unvalidated posting probabilities or issue transfer orders.
- **HRMD CO — Full-Batch Process:** Screens the full master workforce, requires exactly five valid distinct destination preferences from every officer identified as transfer-due, blocks allocation while mandatory preferences are missing or invalid, runs the whole-workforce allocation, and publishes the decision register used by the employee portal.
- Officers not due for routine transfer do not need five preferences under this workflow; the employee view provides Samadhan special-request guidance, subject to the applicable process.
