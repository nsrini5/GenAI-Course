"""
grade_app.py - Week 1 · Day 4: Student Grade Manager in Streamlit

Run with:   streamlit run grade_app.py      (not python grade_app.py)
"""
import pandas as pd            # installed together with streamlit
import streamlit as st


# --- Same grading scale as Day 2, unchanged --------------------------------
def get_grade(mark):
    """90-100 A, 80-89 B, 70-79 C, 60-69 D, below 60 E (boundaries inclusive)."""
    if mark >= 90:
        return "A"
    if mark >= 80:
        return "B"
    if mark >= 70:
        return "C"
    if mark >= 60:
        return "D"
    return "E"


st.set_page_config(page_title="Student Grade Manager", page_icon="🎓")
st.title("🎓 Student Grade Manager")

# --- The experiment from "Think it through" ---------------------------------
# Streamlit re-runs this WHOLE file from the top every time you click anything.
# A plain list created here is therefore rebuilt empty on every click.
plain_list_mode = st.sidebar.toggle(
    "Experiment: plain `students = []` (no session_state)", value=False)
st.sidebar.caption(
    "Turn this on and add two students: the first one disappears, because "
    "Streamlit re-runs the script and `students = []` starts empty again. "
    "Turn it off to use `st.session_state`, which survives the reruns.")

if plain_list_mode:
    students = []                                   # wiped on every rerun
else:
    if "students" not in st.session_state:          # created once per browser session
        st.session_state.students = []
    students = st.session_state.students

# --- Form to add a student ---------------------------------------------------
with st.form("add", clear_on_submit=True):
    col_name, col_mark = st.columns([2, 1])
    name = col_name.text_input("Name")
    # min/max make the box itself refuse anything outside 0-100
    mark = col_mark.number_input("Mark", min_value=0, max_value=100, step=1, value=None,
                                 placeholder="0 - 100")
    submitted = st.form_submit_button("Add")

if submitted:
    name = name.strip()
    if not name:
        st.error("Please enter a name.")
    elif mark is None:
        st.error("Please enter a mark between 0 and 100.")
    else:
        if any(s["Name"].lower() == name.lower() for s in students):
            st.info(f"There is already a student called {name}; added as a separate entry.")
        students.append({"Name": name, "Mark": int(mark), "Grade": get_grade(mark)})
        st.success(f"Added {name}: {int(mark)} → grade {get_grade(mark)}")

# --- Results table and class figures ----------------------------------------
if students:
    marks = [s["Mark"] for s in students]
    c1, c2, c3 = st.columns(3)
    c1.metric("Average", f"{sum(marks) / len(marks):.1f}")
    c2.metric("Highest", max(marks))
    c3.metric("Lowest", min(marks))

    st.subheader(f"Results ({len(students)} student{'s' if len(students) != 1 else ''})")
    table = pd.DataFrame(students, columns=["Name", "Mark", "Grade"])
    table.index = range(1, len(table) + 1)        # number rows 1, 2, 3 ...
    st.table(table)

    if not plain_list_mode and st.button("Clear all students"):
        st.session_state.students = []
        st.rerun()
else:
    st.info("No students yet. Add one using the form above.")

if plain_list_mode:
    st.warning("Plain-list mode: only the student you just added is shown. "
               "Everyone added before was lost when the script re-ran.")
