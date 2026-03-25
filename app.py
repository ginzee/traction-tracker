import os
import re
import json
import uuid
import tempfile
import streamlit as st
from datetime import date, timedelta
from itertools import groupby

# ── Config & constants ────────────────────────────────────────────────────────

DATA_FILE       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "data.json")
STATUS_OPTIONS  = ["On Track", "Off Track", "Complete"]
ISSUE_STATUSES  = ["Identified", "In Progress", "Resolved"]

# 90-day cycle anchored to first day of work
CYCLE_START     = date(2026, 3, 23)
CYCLE_DAYS      = 90
_OLD_QUARTER_RE = re.compile(r"^Q\d \d{4}$")


# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_date(d: date) -> str:
    """Cross-platform date format: 'Mar 5, 2026' (no zero-padded day)."""
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def parse_date(iso_str, fallback: str = "unknown") -> str:
    """Safely parse an ISO date string and return a formatted label."""
    if not iso_str:
        return fallback
    try:
        return fmt_date(date.fromisoformat(iso_str))
    except (ValueError, TypeError):
        return fallback


def calc_height(text: str, min_h: int = 120) -> int:
    """Approximate a comfortable text area height based on content length."""
    if not text:
        return min_h
    lines = sum(len(line) // 72 + 1 for line in text.split("\n"))
    return max(min_h, lines * 22 + 32)


def get_cycle_label(for_date: date = None) -> str:
    """Return the 90-day cycle label for a given date (defaults to today)."""
    if for_date is None:
        for_date = date.today()
    if for_date < CYCLE_START:
        cycle_num = 1
    else:
        cycle_num = (for_date - CYCLE_START).days // CYCLE_DAYS + 1
    start = CYCLE_START + timedelta(days=(cycle_num - 1) * CYCLE_DAYS)
    end   = start + timedelta(days=CYCLE_DAYS - 1)
    return f"Cycle {cycle_num}  ·  {fmt_date(start).rsplit(',', 1)[0]} – {fmt_date(end)}"


# ── Data I/O ──────────────────────────────────────────────────────────────────

def save_data(data: dict) -> None:
    """Atomically write data to disk to prevent corruption on crash."""
    dir_ = os.path.dirname(DATA_FILE)
    os.makedirs(dir_, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False, suffix=".tmp", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        tmp_path = f.name
    os.replace(tmp_path, DATA_FILE)


def _migrate(data: dict) -> bool:
    """Ensure all expected keys exist and old formats are upgraded. Returns True if changes were made."""
    changed = False

    # Vision sub-keys
    data.setdefault("vision", {})
    for key in ("three_year", "one_year", "ten_year"):
        if key not in data["vision"]:
            data["vision"][key] = ""
            changed = True

    # Rocks: ensure required fields and migrate old quarter labels
    data.setdefault("rocks", [])
    cycle_1 = get_cycle_label(CYCLE_START)
    for rock in data["rocks"]:
        if rock.setdefault("status", "On Track") != rock.get("status"):
            changed = True
        rock.setdefault("description", "")
        if _OLD_QUARTER_RE.match(rock.get("quarter", "")):
            rock["quarter"] = cycle_1
            changed = True

    # Todos: ensure required fields
    data.setdefault("todos", [])
    for todo in data["todos"]:
        for key, default in [("done", False), ("company", None), ("rock_id", None),
                              ("completed_on", None)]:
            if key not in todo:
                todo[key] = default
                changed = True

    # Issues: ensure required fields
    data.setdefault("issues", [])
    for issue in data["issues"]:
        for key, default in [("description", ""), ("proposed_solution", ""),
                              ("status", "Identified"), ("resolved_on", None)]:
            if key not in issue:
                issue[key] = default
                changed = True
        if "identified_on" not in issue:
            issue["identified_on"] = date.today().isoformat()
            changed = True

    return changed


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    if _migrate(data):
        save_data(data)
    return data


# ── App setup ─────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Traction Tracker", layout="centered")
st.title("Traction Tracker")

data = load_data()

tab_vision, tab_rocks, tab_todos, tab_issues = st.tabs(["Vision", "Rocks", "To-Dos", "Issues"])


# ── VISION ────────────────────────────────────────────────────────────────────

with tab_vision:
    st.subheader("Long-Term Vision")

    has_content = bool(data["vision"]["three_year"] or data["vision"]["one_year"])

    if "vision_edit" not in st.session_state:
        st.session_state.vision_edit = not has_content

    if st.session_state.vision_edit:
        three_year = st.text_area(
            "3-Year Picture",
            value=data["vision"]["three_year"],
            height=calc_height(data["vision"]["three_year"]),
            key="v_3",
        )
        one_year = st.text_area(
            "1-Year Goals",
            value=data["vision"]["one_year"],
            height=calc_height(data["vision"]["one_year"]),
            key="v_1",
        )
        col_save, col_cancel, _ = st.columns([1, 1, 4])
        with col_save:
            if st.button("Save Vision", type="primary"):
                data["vision"].update(three_year=three_year, one_year=one_year)
                save_data(data)
                st.session_state.vision_edit = False
                st.rerun()
        with col_cancel:
            if has_content and st.button("Cancel"):
                st.session_state.vision_edit = False
                st.rerun()
    else:
        for label, key in [("3-Year Picture", "three_year"), ("1-Year Goals", "one_year")]:
            st.markdown(f"**{label}**")
            with st.container(border=True):
                text = data["vision"].get(key, "").strip()
                st.markdown(text if text else "*Not set.*")
        st.write("")
        if st.button("Edit Vision"):
            st.session_state.vision_edit = True
            st.rerun()


# ── ROCKS ─────────────────────────────────────────────────────────────────────

with tab_rocks:
    current_q = get_cycle_label()
    st.subheader(f"Rocks — {current_q}")

    current_rocks = [r for r in data["rocks"] if r.get("quarter") == current_q]
    past_rocks    = [r for r in data["rocks"] if r.get("quarter") != current_q]

    if current_rocks:
        for rock in current_rocks:
            key_status = f"rock_status_{rock['id']}"
            if key_status not in st.session_state:
                st.session_state[key_status] = rock.get("status", "On Track")

            col_title, col_status, col_del = st.columns([5, 2, 1])
            with col_title:
                st.markdown(f"**{rock['title']}**")
                if rock.get("description"):
                    st.caption(rock["description"])
            with col_status:
                chosen = st.selectbox(
                    label="status",
                    options=STATUS_OPTIONS,
                    key=key_status,
                    label_visibility="collapsed",
                )
                if chosen != rock.get("status", "On Track"):
                    rock["status"] = chosen
                    save_data(data)
                    st.rerun()
            with col_del:
                if st.button("✕", key=f"del_rock_{rock['id']}"):
                    data["rocks"] = [r for r in data["rocks"] if r["id"] != rock["id"]]
                    save_data(data)
                    st.rerun()
    else:
        st.info("No rocks set for this cycle yet.")

    st.divider()
    st.markdown("**Add a Rock**")
    with st.form("add_rock_form", clear_on_submit=True):
        title = st.text_input("Title")
        desc  = st.text_area("Description (optional)", height=100)
        if st.form_submit_button("Add Rock") and title.strip():
            data["rocks"].append({
                "id":          str(uuid.uuid4()),
                "title":       title.strip(),
                "description": desc.strip(),
                "quarter":     current_q,
                "status":      "On Track",
            })
            save_data(data)
            st.rerun()

    if past_rocks:
        with st.expander("Past Rocks"):
            grouped_past = groupby(
                sorted(past_rocks, key=lambda x: x.get("quarter", ""), reverse=True),
                key=lambda x: x.get("quarter", ""),
            )
            for cycle_label, group in grouped_past:
                st.markdown(f"**{cycle_label}**")
                for r in group:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;{r['title']} — *{r.get('status', '?')}*")


# ── TO-DOS ────────────────────────────────────────────────────────────────────

with tab_todos:
    st.subheader("To-Dos")

    active_rocks    = {r["title"]: r["id"] for r in data["rocks"] if r.get("status") != "Complete"}
    rock_name_by_id = {r["id"]: r["title"] for r in data["rocks"]}
    known_companies = sorted(set(i["company"] for i in data["issues"] if i.get("company")))

    with st.form("add_todo_form", clear_on_submit=True):
        todo_title = st.text_input("New to-do")
        col_rock, col_company = st.columns(2)
        with col_rock:
            rock_options = ["— none —"] + list(active_rocks.keys())
            linked_rock = st.selectbox("Link to Rock", rock_options)
        with col_company:
            company_options = ["— none —"] + known_companies
            linked_company = st.selectbox("Link to Company", company_options)
        if st.form_submit_button("Add") and todo_title.strip():
            data["todos"].append({
                "id":           str(uuid.uuid4()),
                "title":        todo_title.strip(),
                "rock_id":      active_rocks.get(linked_rock) if linked_rock != "— none —" else None,
                "company":      linked_company if linked_company != "— none —" else None,
                "done":         False,
                "completed_on": None,
            })
            save_data(data)
            st.rerun()

    st.divider()

    open_todos = [t for t in data["todos"] if not t.get("done")]
    done_todos = [t for t in data["todos"] if t.get("done")]

    if open_todos:
        for todo in open_todos:
            key_done = f"todo_done_{todo['id']}"
            col_check, col_label, col_del = st.columns([1, 7, 1])
            with col_check:
                checked = st.checkbox("done", value=False, key=key_done, label_visibility="collapsed")
                if checked:
                    todo["done"]         = True
                    todo["completed_on"] = date.today().isoformat()
                    save_data(data)
                    st.rerun()
            with col_label:
                label = todo["title"]
                tags  = []
                if todo.get("rock_id") and todo["rock_id"] in rock_name_by_id:
                    tags.append(rock_name_by_id[todo["rock_id"]])
                if todo.get("company"):
                    tags.append(todo["company"])
                if tags:
                    label += "  ·  *" + "  ·  ".join(tags) + "*"
                st.write(label)
            with col_del:
                if st.button("✕", key=f"del_todo_{todo['id']}"):
                    data["todos"] = [t for t in data["todos"] if t["id"] != todo["id"]]
                    save_data(data)
                    st.rerun()
    else:
        st.info("No open to-dos.")

    if done_todos:
        # None completed_on sorts to bottom; group label falls back to "Unknown"
        sorted_done = sorted(done_todos, key=lambda t: t.get("completed_on") or "", reverse=True)
        grouped_done = groupby(sorted_done, key=lambda t: t.get("completed_on") or "Unknown")

        with st.expander(f"Completed ({len(done_todos)})"):
            for day, group in grouped_done:
                st.markdown(f"**{parse_date(day, fallback='Unknown date')}**")
                for todo in group:
                    col_label, col_del = st.columns([7, 1])
                    with col_label:
                        st.markdown(f"~~{todo['title']}~~")
                    with col_del:
                        if st.button("✕", key=f"del_dtodo_{todo['id']}"):
                            data["todos"] = [t for t in data["todos"] if t["id"] != todo["id"]]
                            save_data(data)
                            st.rerun()


# ── ISSUES ────────────────────────────────────────────────────────────────────

with tab_issues:
    st.subheader("Issues")

    existing_companies = sorted(set(i["company"] for i in data["issues"] if i.get("company")))

    with st.form("add_issue_form", clear_on_submit=True):
        st.markdown("**Log an Issue**")
        col_co, col_title = st.columns([2, 3])
        with col_co:
            co_options     = existing_companies + ["+ New company"]
            company_choice = st.selectbox("Company", co_options) if existing_companies else None
            use_new        = not existing_companies or company_choice == "+ New company"
            if use_new:
                new_company_name = st.text_input("Company name")
            else:
                new_company_name = ""
        with col_title:
            issue_title = st.text_input("Issue")
        issue_desc     = st.text_area("Description (optional)", height=80)
        issue_solution = st.text_area("Proposed Solution (optional)", height=80)

        if st.form_submit_button("Log Issue"):
            company = new_company_name.strip() if use_new else company_choice
            if company and issue_title.strip():
                data["issues"].append({
                    "id":                str(uuid.uuid4()),
                    "company":           company,
                    "title":             issue_title.strip(),
                    "description":       issue_desc.strip(),
                    "proposed_solution": issue_solution.strip(),
                    "status":            "Identified",
                    "identified_on":     date.today().isoformat(),
                    "resolved_on":       None,
                })
                save_data(data)
                st.rerun()

    st.divider()

    if not data["issues"]:
        st.info("No issues logged yet.")
    else:
        companies = sorted(set(i["company"] for i in data["issues"] if i.get("company")))

        for company in companies:
            company_issues  = [i for i in data["issues"] if i.get("company") == company]
            open_issues     = [i for i in company_issues if i.get("status") != "Resolved"]
            resolved_issues = [i for i in company_issues if i.get("status") == "Resolved"]

            st.markdown(f"### {company}")

            for issue in open_issues:
                key_status = f"issue_status_{issue['id']}"
                key_edit   = f"issue_edit_{issue['id']}"
                if key_status not in st.session_state:
                    st.session_state[key_status] = issue.get("status", "Identified")
                if key_edit not in st.session_state:
                    st.session_state[key_edit] = False

                with st.container(border=True):
                    col_title, col_status, col_del = st.columns([5, 2, 1])
                    with col_title:
                        st.markdown(f"**{issue['title']}**")
                        st.caption(f"Identified: {parse_date(issue.get('identified_on'))}")
                    with col_status:
                        chosen = st.selectbox(
                            "status",
                            ISSUE_STATUSES,
                            key=key_status,
                            label_visibility="collapsed",
                        )
                        if chosen != issue.get("status"):
                            issue["status"]      = chosen
                            issue["resolved_on"] = date.today().isoformat() if chosen == "Resolved" else None
                            save_data(data)
                            st.rerun()
                    with col_del:
                        if st.button("✕", key=f"del_issue_{issue['id']}"):
                            data["issues"] = [i for i in data["issues"] if i["id"] != issue["id"]]
                            save_data(data)
                            st.rerun()

                    if st.session_state[key_edit]:
                        new_desc = st.text_area(
                            "Description",
                            value=issue.get("description", ""),
                            height=calc_height(issue.get("description", ""), min_h=80),
                            key=f"issue_desc_{issue['id']}",
                        )
                        new_sol = st.text_area(
                            "Proposed Solution",
                            value=issue.get("proposed_solution", ""),
                            height=calc_height(issue.get("proposed_solution", ""), min_h=80),
                            key=f"issue_sol_{issue['id']}",
                        )
                        col_save, col_cancel, _ = st.columns([1, 1, 4])
                        with col_save:
                            if st.button("Save", key=f"save_issue_{issue['id']}", type="primary"):
                                issue["description"]       = new_desc.strip()
                                issue["proposed_solution"] = new_sol.strip()
                                save_data(data)
                                st.session_state[key_edit] = False
                                st.rerun()
                        with col_cancel:
                            if st.button("Cancel", key=f"cancel_issue_{issue['id']}"):
                                st.session_state[key_edit] = False
                                st.rerun()
                    else:
                        if issue.get("description"):
                            st.markdown(f"**Description:** {issue['description']}")
                        if issue.get("proposed_solution"):
                            st.markdown(f"**Proposed Solution:** {issue['proposed_solution']}")
                        if st.button("Edit Details", key=f"edit_issue_{issue['id']}"):
                            st.session_state[key_edit] = True
                            st.rerun()

            if resolved_issues:
                resolved_sorted = sorted(
                    resolved_issues,
                    key=lambda i: i.get("resolved_on") or "",
                    reverse=True,
                )
                with st.expander(f"Resolved ({len(resolved_issues)})"):
                    for issue in resolved_sorted:
                        col_info, col_del = st.columns([8, 1])
                        with col_info:
                            st.markdown(f"~~**{issue['title']}**~~")
                            st.caption(
                                f"Identified: {parse_date(issue.get('identified_on'))}"
                                f"  ·  Resolved: {parse_date(issue.get('resolved_on'))}"
                            )
                            if issue.get("proposed_solution"):
                                st.caption(f"Solution: {issue['proposed_solution']}")
                        with col_del:
                            if st.button("✕", key=f"del_rissue_{issue['id']}"):
                                data["issues"] = [i for i in data["issues"] if i["id"] != issue["id"]]
                                save_data(data)
                                st.rerun()
