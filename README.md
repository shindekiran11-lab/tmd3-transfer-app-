# TMD 3 – AI-Assisted Transfer Planner v17.1

Rebuilt using the user's latest centre-wise grade cells. At the user's direction, Agartala Grade A has been reduced from 9 to 8, reconciling its centre total to 25 and the grand total to 5,000.

## New dashboard features
- Preferred-centre demand summary by preference rank.
- Optional employee-reported sentiment distribution and comments (only if submitted).
- CO action queue for allocations beyond preference 2 or cases needing human review.
- Employee view highlights the score-based estimate for preference 1 and shows estimates for all five preferences.

**Important:** Employee likelihood percentages are normalised model scores, not calibrated statistical probabilities, and are not guarantees. Employee sentiment is not inferred; it must be explicitly provided. Treat comments as sensitive HR information and restrict access.

## Run locally
Install Python 3.12, then run:
`python -m pip install -r requirements.txt`
`python -m streamlit run app.py`
Open `http://localhost:8501` if required.

Synthetic data only. This remains a capstone prototype, not a production-ready transfer system. Policy, allocation, fairness, security and end-to-end behaviour require independent validation and human approval.
