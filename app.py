import streamlit as st
import json
import os
import uuid
from datetime import date

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "data.json")

STATUS_OPTIONS = ["On Track", "Off Track", "Complete"]


def get_current_quarter() -> str:
    today = date.today()
    q = (today.month - 1) // 3 + 1
    return f"Q{q} {today.year}"


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {
        "vision": {"ten_year": "", "three_year": "", "one_year": ""},
        "rocks": [],
        "todos": [],
    }


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── App setup ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Traction Tracker", layout="centered")
st.title("Traction Tracker")

data = load_data()

tab_vision, tab_rocks, tab_todos = st.tabs(["Vision", "Rocks", "To-Dos"])


# ── VISION ───────────────────────────────────────────────────────────────────

with tab_vision:
    st.subheader("Long-Term Vision")

    ten_year   = st.text_area("10-Year Target",  value=data["vision"]["ten_year"],   height=120, key="v_10")
    three_year = st.text_area("3-Year Picture",  value=data["vision"]["three_year"], height=120, key="v_3")
    one_year   = st.text_area("1-Year Goals",    value=data["vision"]["one_year"],   height=120, key="v_1")

    if st.button("Save Vision"):
        data["vision"].update(ten_year=ten_year, three_year=three_year, one_year=one_year)
        save_data(data)
        st.success("Vision saved.")


# ── ROCKS ────────────────────────────────────────────────────────────────────

with tab_rocks:
    current_q = get_current_quarter()
    st.subheader(f"Rocks — {current_q}")

    current_rocks = [r for r in data["rocks"] if r["quarter"] == current_q]
    past_rocks    = [r for r in data["rocks"] if r["quarter"] != current_q]

    if current_rocks:
        for rock in current_rocks:
            key_status = f"rock_status_{rock['id']}"

            # Seed session state from persisted data on first render
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

            with col_del:
                if st.button("✕", key=f"del_rock_{rock['id']}"):
                    data["rocks"] = [r for r in data["rocks"] if r["id"] != rock["id"]]
                    save_data(data)
                    st.rerun()
    else:
        st.info("No rocks set for this quarter yet.")

    st.divider()
    st.markdown("**Add a Rock**")

    with st.form("add_rock_form", clear_on_submit=True):
        title = st.text_input("Title")
        desc  = st.text_input("Description (optional)")
        if st.form_submit_button("Add Rock") and title.strip():
            data["rocks"].append({
                "id": str(uuid.uuid4()),
                "title": title.strip(),
                "description": desc.strip(),
                "quarter": current_q,
                "status": "On Track",
            })
            save_data(data)
            st.rerun()

    if past_rocks:
        with st.expander("Past Rocks"):
            for r in sorted(past_rocks, key=lambda x: x["quarter"], reverse=True):
                st.markdown(f"**{r['title']}** — {r['quarter']} — *{r.get('status', '?')}*")


# ── TO-DOS ───────────────────────────────────────────────────────────────────

with tab_todos:
    st.subheader("To-Dos")

    active_rocks    = {r["title"]: r["id"] for r in data["rocks"] if r.get("status") != "Complete"}
    rock_name_by_id = {r["id"]: r["title"] for r in data["rocks"]}

    with st.form("add_todo_form", clear_on_submit=True):
        col_input, col_link = st.columns([3, 2])
        with col_input:
            todo_title = st.text_input("New to-do")
        with col_link:
            link_options = ["— none —"] + list(active_rocks.keys())
            linked = st.selectbox("Link to Rock", link_options)
        if st.form_submit_button("Add") and todo_title.strip():
            data["todos"].append({
                "id": str(uuid.uuid4()),
                "title": todo_title.strip(),
                "rock_id": active_rocks.get(linked) if linked != "— none —" else None,
                "done": False,
            })
            save_data(data)
            st.rerun()

    st.divider()

    open_todos = [t for t in data["todos"] if not t["done"]]
    done_todos = [t for t in data["todos"] if t["done"]]

    if open_todos:
        for todo in open_todos:
            key_done = f"todo_done_{todo['id']}"
            col_check, col_label, col_del = st.columns([1, 7, 1])

            with col_check:
                checked = st.checkbox("done", value=False, key=key_done, label_visibility="collapsed")
                if checked:
                    todo["done"] = True
                    save_data(data)
                    st.rerun()

            with col_label:
                label = todo["title"]
                if todo.get("rock_id") and todo["rock_id"] in rock_name_by_id:
                    label += f"  ·  *{rock_name_by_id[todo['rock_id']]}*"
                st.write(label)

            with col_del:
                if st.button("✕", key=f"del_todo_{todo['id']}"):
                    data["todos"] = [t for t in data["todos"] if t["id"] != todo["id"]]
                    save_data(data)
                    st.rerun()
    else:
        st.info("No open to-dos.")

    if done_todos:
        with st.expander(f"Completed ({len(done_todos)})"):
            for todo in done_todos:
                col_label, col_del = st.columns([7, 1])
                with col_label:
                    st.markdown(f"~~{todo['title']}~~")
                with col_del:
                    if st.button("✕", key=f"del_dtodo_{todo['id']}"):
                        data["todos"] = [t for t in data["todos"] if t["id"] != todo["id"]]
                        save_data(data)
                        st.rerun()
