# TMD 3 – AI-Assisted Transfer Planner — Full-Workforce Reconciled Build

## Reconciled data
The Officer_Master contains exactly 5,000 synthetic records with unique IDs 0001–5000. Agartala Grade A is 8 and its centre total is 25, as explicitly authorised. Centre totals and centre-wise grade cells reconcile to the master; Centre × Grade × Cadre capacity counts are derived from the same master.

## Full-workforce annual plan
- Every HRMD CO run screens the complete 5,000-officer master, not only the uploaded subset.
- The batch template has 5,000 rows and blank preference fields; actual preferences must come from authorised employee submissions.
- Five valid, unique preferences are required for routine allocation in this prototype. Due officers without valid preferences are included in the 5,000-row decision register and marked for HRMD action, not allocated by invented preferences.
- The app separately reports total workforce, transfer-due population, allocated population, human-review population, preference completeness and officers awaiting preferences.
- The employee view reads the recommendation from the current HRMD CO full-workforce run when available; it does not show unvalidated likelihood percentages.

## HRMD CO dashboard
- Submitted preference demand by centre and rank.
- Employee-reported sentiment distribution and optional comments, if supplied.
- Human-review/exception queue and CO action queue.
- Centre manpower, centre-wise grade distribution, grade/recruitment, specialist cadre, retirement and PAR views.
- Skill profile and skill-based scoring have been removed.

## History and governance
Posting-history fields are generated illustrative test data, not verified history. The employee view explicitly labels this limitation; NER Centre History displays “Nil” when no centre history is present. Sentiment is not inferred from PAR, grade, cadre or preferences. Restrict access to self-reported comments.

## Limitations
Synthetic data only. The full Streamlit browser UI was not launched in the build environment. Syntax, workbook reconciliation and targeted data checks can be performed here, but full-workforce optimisation scalability, interface behavior, policy interpretation, fairness, security and production readiness require further independent testing and authorised human review.


Mandatory preference rule: before a whole-workforce plan can be generated, every officer identified as routine transfer-due must have exactly five valid, distinct destination preferences. Missing, duplicate, unknown-centre, current-centre, or grade/zone-invalid preferences block final allocation. The app displays the due officers needing correction and provides a completion template. No preferences or destinations are invented.

Preference requirement distinction: exactly five valid destination preferences are mandatory only for officers identified as routine transfer-due. Officers who are not due for routine transfer do not need to submit preferences; the employee view directs exceptional cases to Samadhan, subject to the applicable process. The completion report lists only transfer-due officers with missing or invalid preferences.

## Application modes

- **RO Employee Portal:** Read-only individual lookup for officer details, routine-transfer eligibility, and the final recommendation from the latest completed HRMD CO whole-workforce plan. It does not display unvalidated posting probabilities or issue transfer orders.
- **HRMD CO — Full-Batch Process:** Screens the full master workforce, requires exactly five valid distinct destination preferences from every officer identified as transfer-due, blocks allocation while mandatory preferences are missing or invalid, runs the whole-workforce allocation, and publishes the decision register used by the employee portal.
- Officers not due for routine transfer do not need five preferences under this workflow; the employee view provides Samadhan special-request guidance, subject to the applicable process.
