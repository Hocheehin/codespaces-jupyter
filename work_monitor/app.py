"""Work Monitoring Tracker.

A small Streamlit app for logging monitoring checks on your work, tracking
issues and follow-up actions, and seeing what is open or overdue.

Run with:
    streamlit run work_monitor/app.py
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).with_name("monitoring.db")

STATUSES = ["OK", "Issue found", "Needs follow-up"]
PRIORITIES = ["Low", "Medium", "High"]


# ---------------------------------------------------------------- database
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                check_date   TEXT NOT NULL,
                project      TEXT NOT NULL,
                item         TEXT NOT NULL,
                status       TEXT NOT NULL,
                priority     TEXT NOT NULL DEFAULT 'Medium',
                findings     TEXT,
                action       TEXT,
                owner        TEXT,
                due_date     TEXT,
                resolved     INTEGER NOT NULL DEFAULT 0,
                resolved_on  TEXT,
                created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def add_check(**fields) -> None:
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    with get_conn() as conn:
        conn.execute(f"INSERT INTO checks ({cols}) VALUES ({marks})", tuple(fields.values()))


def set_resolved(check_id: int, resolved: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE checks SET resolved = ?, resolved_on = ? WHERE id = ?",
            (int(resolved), date.today().isoformat() if resolved else None, check_id),
        )


def delete_check(check_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM checks WHERE id = ?", (check_id,))


def load_checks() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT * FROM checks ORDER BY check_date DESC, id DESC", conn)
    for col in ("check_date", "due_date", "resolved_on"):
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    df["resolved"] = df["resolved"].astype(bool)
    today = date.today()
    df["overdue"] = df.apply(
        lambda r: (not r["resolved"]) and pd.notna(r["due_date"]) and r["due_date"] < today,
        axis=1,
    ) if not df.empty else pd.Series(dtype=bool)
    return df


# ---------------------------------------------------------------- UI pages
def page_log() -> None:
    st.header("Log a monitoring check")
    df = load_checks()
    known_projects = sorted(df["project"].dropna().unique()) if not df.empty else []

    with st.form("new_check", clear_on_submit=True):
        c1, c2 = st.columns(2)
        check_date = c1.date_input("Date checked", value=date.today())
        project_choice = c2.selectbox(
            "Project / area", ["➕ New…"] + known_projects, index=1 if known_projects else 0
        )
        new_project = st.text_input("New project / area name") if project_choice == "➕ New…" else ""
        item = st.text_input("What was monitored?", placeholder="e.g. Weekly safety walk, KPI report, site visit")
        c3, c4 = st.columns(2)
        status = c3.selectbox("Result", STATUSES)
        priority = c4.selectbox("Priority", PRIORITIES, index=1)
        findings = st.text_area("Findings / notes")
        action = st.text_area("Action required (if any)")
        c5, c6 = st.columns(2)
        owner = c5.text_input("Action owner")
        has_due = c6.checkbox("Set a due date", value=status != "OK")
        due_date = c6.date_input("Due date", value=date.today()) if has_due else None

        if st.form_submit_button("Save check", type="primary"):
            project = (new_project if project_choice == "➕ New…" else project_choice).strip()
            if not project or not item.strip():
                st.error("Project and 'What was monitored' are required.")
            else:
                add_check(
                    check_date=check_date.isoformat(),
                    project=project,
                    item=item.strip(),
                    status=status,
                    priority=priority,
                    findings=findings.strip(),
                    action=action.strip(),
                    owner=owner.strip(),
                    due_date=due_date.isoformat() if due_date else None,
                    resolved=int(status == "OK"),
                    resolved_on=check_date.isoformat() if status == "OK" else None,
                )
                st.success(f"Saved: {project} — {item.strip()}")


def page_dashboard() -> None:
    st.header("Dashboard")
    df = load_checks()
    if df.empty:
        st.info("No checks logged yet. Use **Log a check** to add your first one.")
        return

    open_items = df[~df["resolved"]]
    this_month = df[pd.to_datetime(df["check_date"]).dt.to_period("M") == pd.Timestamp.today().to_period("M")]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total checks", len(df))
    m2.metric("Checks this month", len(this_month))
    m3.metric("Open actions", len(open_items))
    m4.metric("Overdue", int(df["overdue"].sum()))

    st.subheader("⚠️ Open actions")
    if open_items.empty:
        st.success("Nothing open — all caught up.")
    else:
        show = open_items.sort_values(["overdue", "due_date"], ascending=[False, True])
        for _, r in show.iterrows():
            flag = "🔴 OVERDUE" if r["overdue"] else ("🟠" if r["priority"] == "High" else "🟡")
            due = f" · due {r['due_date']}" if pd.notna(r["due_date"]) else ""
            owner = f" · {r['owner']}" if r["owner"] else ""
            with st.expander(f"{flag} [{r['project']}] {r['item']}{due}{owner}"):
                st.write(f"**Checked:** {r['check_date']} · **Result:** {r['status']} · **Priority:** {r['priority']}")
                if r["findings"]:
                    st.write(f"**Findings:** {r['findings']}")
                if r["action"]:
                    st.write(f"**Action:** {r['action']}")
                if st.button("Mark resolved ✅", key=f"res_{r['id']}"):
                    set_resolved(int(r["id"]), True)
                    st.rerun()

    st.subheader("Checks per week")
    weekly = (
        df.assign(week=pd.to_datetime(df["check_date"]).dt.to_period("W").dt.start_time)
        .groupby(["week", "status"]).size().unstack(fill_value=0)
        .reindex(columns=STATUSES, fill_value=0)
    )
    weekly.index = [d.strftime("%Y-%m-%d") for d in weekly.index]
    st.bar_chart(weekly, color=["#2e9e5b", "#d64545", "#e8a33d"], x_label="Week starting", y_label="Checks")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("By project")
        st.dataframe(
            df.groupby("project").agg(checks=("id", "count"), open=("resolved", lambda s: int((~s).sum())),
                                      last_checked=("check_date", "max")),
            width="stretch",
        )
    with c2:
        st.subheader("By result")
        st.dataframe(df["status"].value_counts().rename("count"), width="stretch")


def page_history() -> None:
    st.header("History")
    df = load_checks()
    if df.empty:
        st.info("No checks logged yet.")
        return

    c1, c2, c3 = st.columns(3)
    projects = c1.multiselect("Project", sorted(df["project"].unique()))
    statuses = c2.multiselect("Result", STATUSES)
    state = c3.selectbox("Show", ["All", "Open only", "Resolved only"])
    d1, d2 = st.columns(2)
    start = d1.date_input("From", value=min(df["check_date"]))
    end = d2.date_input("To", value=max(max(df["check_date"]), date.today()))
    text = st.text_input("Search findings / actions / items")

    f = df[(df["check_date"] >= start) & (df["check_date"] <= end)]
    if projects:
        f = f[f["project"].isin(projects)]
    if statuses:
        f = f[f["status"].isin(statuses)]
    if state == "Open only":
        f = f[~f["resolved"]]
    elif state == "Resolved only":
        f = f[f["resolved"]]
    if text:
        blob = (f["item"].fillna("") + " " + f["findings"].fillna("") + " " + f["action"].fillna("")).str.lower()
        f = f[blob.str.contains(text.lower(), regex=False)]

    cols = ["id", "check_date", "project", "item", "status", "priority", "findings",
            "action", "owner", "due_date", "resolved", "resolved_on", "overdue"]
    edited = st.data_editor(
        f[cols], hide_index=True, width="stretch",
        disabled=[c for c in cols if c != "resolved"],
        column_config={"resolved": st.column_config.CheckboxColumn("Resolved", help="Tick to close the action")},
        key="history_editor",
    )
    changed = edited[edited["resolved"] != f.set_index("id").loc[edited["id"], "resolved"].values]
    for _, r in changed.iterrows():
        set_resolved(int(r["id"]), bool(r["resolved"]))
    if not changed.empty:
        st.rerun()

    st.caption(f"{len(f)} of {len(df)} checks shown")
    st.download_button("⬇️ Download as CSV", f[cols].to_csv(index=False), "monitoring_checks.csv", "text/csv")

    with st.expander("Delete a check"):
        del_id = st.selectbox("Check ID", f["id"].tolist())
        if st.button("Delete permanently", type="secondary"):
            delete_check(int(del_id))
            st.rerun()


def page_import() -> None:
    st.header("Import from CSV")
    st.write("Upload a CSV with columns: `check_date, project, item, status` "
             "(optional: `priority, findings, action, owner, due_date, resolved`).")
    up = st.file_uploader("CSV file", type="csv")
    if up is None:
        return
    data = pd.read_csv(up)
    missing = {"check_date", "project", "item", "status"} - set(data.columns)
    if missing:
        st.error(f"Missing columns: {', '.join(sorted(missing))}")
        return
    st.dataframe(data.head(), width="stretch")
    if st.button(f"Import {len(data)} rows", type="primary"):
        for _, r in data.iterrows():
            resolved = bool(r.get("resolved", r["status"] == "OK")) if pd.notna(r.get("resolved", None)) else r["status"] == "OK"
            add_check(
                check_date=str(pd.to_datetime(r["check_date"]).date()),
                project=str(r["project"]), item=str(r["item"]), status=str(r["status"]),
                priority=str(r.get("priority", "Medium") if pd.notna(r.get("priority")) else "Medium"),
                findings=str(r.get("findings", "") if pd.notna(r.get("findings")) else ""),
                action=str(r.get("action", "") if pd.notna(r.get("action")) else ""),
                owner=str(r.get("owner", "") if pd.notna(r.get("owner")) else ""),
                due_date=str(pd.to_datetime(r["due_date"]).date()) if pd.notna(r.get("due_date")) else None,
                resolved=int(resolved), resolved_on=None,
            )
        st.success(f"Imported {len(data)} checks.")


# ---------------------------------------------------------------- main
def main() -> None:
    st.set_page_config(page_title="Work Monitoring Tracker", page_icon="📋", layout="wide")
    init_db()
    st.sidebar.title("📋 Work Monitoring")
    pages = {
        "Dashboard": page_dashboard,
        "Log a check": page_log,
        "History": page_history,
        "Import CSV": page_import,
    }
    choice = st.sidebar.radio("Go to", list(pages))
    st.sidebar.caption(f"Data stored in `{DB_PATH.name}`")
    pages[choice]()


if __name__ == "__main__":
    main()
