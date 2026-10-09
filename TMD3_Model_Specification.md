# TMD 3 – AI-Assisted Transfer Planner — Final Reconciled Build

## Reconciled data
The user authorised reducing Agartala Grade A by one. Agartala is A=8, B=7, C=4, D=3, E=2, F=1, total 25. The officer master contains exactly 5,000 synthetic records. Centre totals and centre-wise grade cells are reconciled to the same master. Centre × Grade × Cadre capacity counts are also reconciled to the master.

## HRMD CO dashboard
- Whole-batch allocation and policy screening.
- Submitted preference demand by centre and rank.
- Employee-reported sentiment distribution and optional comments, if included in the input.
- Human-review/exception queue and CO action queue.
- Centre manpower, centre-wise grade distribution, grade/recruitment, specialist cadre, retirement and PAR views.
- Skill profile and skill-based scoring have been removed.

## Employee view
The employee view displays the result from the same whole-batch allocation used by HRMD CO, if the officer is included in the completed batch run. No individual likelihood percentage is shown because no user-approved and empirically validated probability method has been specified.

## Sentiment governance
The model does not infer sentiment from PAR, grade, cadre, preferences or special requests. `Employee_Sentiment`, `Sentiment_Comment` and `Transfer_Concern` are optional self-reported input fields. Restrict access to comments and use them only for authorised HR review.

## Display and assumption changes
- NER Centre History displays “Nil” when no value exists.
- Previous Posting History is displayed in a full-width field to avoid truncation.
- The “preference priority” what-if slider has been removed.
- Centre-wise workforce displays all centres and centre × grade distribution from the reconciled officer master.
- No unreconciled grade-cell warning is generated from the old raw reconciliation values.

## Limitations
Synthetic data only. This local capstone prototype is not production-ready. Independent policy verification, code review, fairness testing, security review and human approval are required before operational use.
