# TMD 3 – User Guide v17.1

1. Install Python 3.12.
2. Extract the package and open the folder in VS Code.
3. Run `python -m pip install -r requirements.txt`.
4. Run `python -m streamlit run app.py`.
5. Open `http://localhost:8501` if needed.

## HRMD CO
Upload the completed batch template and run the whole-batch plan. Review the preferred-centre demand summary, employee-reported sentiment (if provided), staffing and retirement dashboards, exception queue and CO action queue. Export the plan for authorised review.

Optional template fields:
- `Employee_Sentiment`: employee-selected category such as Positive, Neutral, Concerned, or Prefer not to say.
- `Sentiment_Comment`: optional free-text comment.
- `Transfer_Concern`: optional structured concern/reason.

These are self-reported only. Do not infer sentiment from performance or personal attributes. Restrict access to comments.

## Employee view
Enter a synthetic Officer ID (0001–5000), select five distinct preferences, then click Check Transfer Probability. The page highlights the estimated likelihood of the first preference and shows all five relative estimates. Percentages are model-score estimates, not calibrated probabilities or guarantees.

Synthetic data only; do not enter real personnel information in this capstone prototype.
