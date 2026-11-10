# Work Monitoring Tracker

A small Streamlit app for logging the monitoring checks you do on your work and following up on what they find.

## Run it

```bash
pip install -r work_monitor/requirements.txt
streamlit run work_monitor/app.py
```

In Codespaces, open the forwarded port (8501) when it pops up.

## Pages

- **Dashboard**: total checks, checks this month, open actions and overdue items; a list of open actions (overdue ones first) with a one-click "Mark resolved"; checks per week by result; and a summary for each project.
- **Log a check**: date, project or area, what was monitored, result (OK / Issue found / Needs follow-up), priority, findings, action required, owner and due date.
- **History**: filter by project, result, open or resolved, date range and text search. Tick "Resolved" in the table to close an action. You can download the filtered rows as CSV or delete a check.
- **Import CSV**: load existing records. The required columns are `check_date, project, item, status`.

Data is kept in a local SQLite file, `work_monitor/monitoring.db`. Git ignores it, so your records stay private.
