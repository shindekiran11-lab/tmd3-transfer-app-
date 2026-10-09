# TMD 3 – AI-Assisted Transfer Planner v17.1

## Reconciled data
The user authorised reducing Agartala Grade A from 9 to 8. Agartala now has A=8, B=7, C=4, D=3, E=2, F=1, total 25. Declared centre totals and grade-cell totals both sum to 5,000. Synthetic officer IDs run from 0001 to 5000.

## HRMD CO dashboard
- Whole-batch allocation and policy screening.
- Submitted preference demand by centre and rank.
- Employee-reported sentiment distribution and optional comments, if included in the input.
- Human-review/exception queue and CO action queue.
- Existing centre manpower, grade/recruitment, cadre/skill, retirement and PAR views.

## Employee view
Shows an estimated score-based likelihood for each of the five selected preferences and highlights the first-preference estimate. These percentages are normalised scores, not calibrated statistical probabilities, and do not guarantee an outcome. Actual batch outcomes depend on eligibility, competing demand, capacity and human review.

## Sentiment governance
The model does not infer sentiment from PAR, grade, cadre, preferences or special requests. `Employee_Sentiment`, `Sentiment_Comment` and `Transfer_Concern` are optional self-reported input fields. Restrict access to comments and use them only for authorised HR review.

## Limitations
Synthetic data only. This local capstone prototype is not production-ready. Independent policy verification, code review, fairness testing, edge-case testing, security review, performance validation and human approval are required before operational use.
