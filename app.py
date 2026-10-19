from datetime import date, datetime, time

import streamlit as st

from pawpal_system import (
    Owner,
    Pet,
    Priority,
    Recurrence,
    Scheduler,
    Task,
    TaskType,
    TimeWindow,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Plan your pets' day around your time, priorities, and preferences.")

if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")
owner: Owner = st.session_state.owner

# ---------------------------------------------------------------- Owner
st.subheader("Owner & preferences")
c1, c2, c3, c4 = st.columns(4)
owner.name = c1.text_input("Name", value=owner.name)
owner.available_minutes = int(c2.number_input(
    "Minutes available", min_value=5, max_value=1440, value=owner.available_minutes, step=5))
owner.preferences.day_start = c3.time_input("Day starts", value=owner.preferences.day_start)
owner.preferences.day_end = c4.time_input("Day ends", value=owner.preferences.day_end)

owner.preferences.preferred_types = [
    TaskType(v) for v in st.multiselect(
        "Preferred task types (win ties between equal priorities)",
        [t.value for t in TaskType],
        default=[t.value for t in owner.preferences.preferred_types],
    )
]

with st.expander("Blocked times (when you're unavailable)"):
    b1, b2, b3 = st.columns([2, 2, 1])
    block_start = b1.time_input("From", value=time(12, 0), key="block_start")
    block_end = b2.time_input("To", value=time(13, 0), key="block_end")
    if b3.button("Block", width="stretch"):
        if block_start < block_end:
            owner.preferences.blocked_windows.append(TimeWindow(block_start, block_end))
        else:
            st.error("'From' must be before 'To'.")
    for n, w in enumerate(list(owner.preferences.blocked_windows)):
        col_a, col_b = st.columns([4, 1])
        col_a.write(f"{w.start:%H:%M} – {w.end:%H:%M}")
        if col_b.button("Remove", key=f"unblock_{n}"):
            owner.preferences.blocked_windows.pop(n)
            st.rerun()

st.divider()

# ----------------------------------------------------------------- Pets
st.subheader("Pets")
with st.form("add_pet", clear_on_submit=True):
    p1, p2, p3 = st.columns(3)
    pet_name = p1.text_input("Pet name")
    species = p2.selectbox("Species", ["dog", "cat", "other"])
    age = p3.number_input("Age", min_value=0, max_value=40, value=1)
    if st.form_submit_button("Add pet") and pet_name.strip():
        owner.add_pet(Pet(name=pet_name.strip(), species=species, age=int(age)))
        st.rerun()

if not owner.pets:
    st.info("Add a pet to get started.")
for pet in owner.pets:
    st.write(f"**{pet.name}** ({pet.species}, {pet.age}) — {len(pet.tasks)} task(s)")

st.divider()

# ---------------------------------------------------------------- Tasks
st.subheader("Tasks")
if owner.pets:
    with st.form("add_task", clear_on_submit=False):
        target = st.selectbox("For pet", [p.name for p in owner.pets])
        t1, t2 = st.columns([2, 1])
        title = t1.text_input("Task title", value="Morning walk")
        task_type = t2.selectbox("Type", [t.value for t in TaskType])
        t3, t4, t5 = st.columns(3)
        duration = t3.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        priority = t4.selectbox("Priority", [p.name.lower() for p in Priority], index=2)
        recurrence = t5.selectbox("Repeats", [r.value for r in Recurrence])
        t6, t7 = st.columns(2)
        use_time = t6.checkbox("Needs a specific time")
        pref_time = t7.time_input("Preferred start", value=time(8, 0))
        if st.form_submit_button("Add task") and title.strip():
            due = datetime.combine(date.today(), pref_time) if use_time else None
            pet = next(p for p in owner.pets if p.name == target)
            pet.add_task(Task(
                title=title.strip(),
                type=TaskType(task_type),
                duration_minutes=int(duration),
                priority=Priority[priority.upper()],
                due_time=due,
                recurrence=Recurrence(recurrence),
            ))
            st.rerun()

today = date.today()
scheduler = Scheduler(owner)
pet_of = {t.task_id: p.name for p in owner.pets for t in p.tasks}

flash = st.session_state.pop("flash", None)
if flash:
    st.success(flash)

if any(p.tasks for p in owner.pets):
    f1, f2 = st.columns(2)
    pet_filter = f1.selectbox("Show pet", ["All pets"] + [p.name for p in owner.pets])
    status_filter = f2.selectbox("Show status", ["All", "Open", "Done"])
    shown = scheduler.sort_by_time(scheduler.filter_tasks(
        pet_name=None if pet_filter == "All pets" else pet_filter,
        completed={"All": None, "Open": False, "Done": True}[status_filter],
    ))
    st.caption("Sorted by time of day; tasks without a set time are listed last.")
    if shown:
        st.dataframe(
            [
                {
                    "Pet": pet_of[t.task_id],
                    "Task": t.title,
                    "Type": t.type.value,
                    "Min": t.duration_minutes,
                    "Priority": t.priority.name.lower(),
                    "Time": f"{t.due_time:%H:%M}" if t.due_time else "flexible",
                    "Date": (
                        f"{(t.due_time or t.due_date):%a %b %d}" if (t.due_time or t.due_date)
                        else "any day"
                    ),
                    "Repeats": t.recurrence.value,
                    "Status": "done" if t.completed else "open",
                    "Due today": t.is_due_on(today),
                }
                for t in shown
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No tasks match these filters.")

    open_tasks = scheduler.sort_by_time(scheduler.filter_tasks(completed=False))
    if open_tasks:
        d1, d2 = st.columns([3, 1])
        chosen = d1.selectbox(
            "Mark a task done",
            open_tasks,
            format_func=lambda t: f"{pet_of[t.task_id]}: {t.title}"
            + (f" ({t.due_time:%H:%M})" if t.due_time else ""),
        )
        d2.write("")
        if d2.button("Mark done", width="stretch"):
            following = scheduler.mark_task_complete(chosen.task_id, today)
            msg = f"Marked '{chosen.title}' done."
            if following:
                nxt = following.due_time or following.due_date
                msg += f" Next {following.recurrence.value} task created for {nxt:%a %b %d}."
            st.session_state.flash = msg
            st.rerun()
elif owner.pets:
    st.info("No tasks yet. Add one above.")

for warning in scheduler.check_conflicts(today):
    st.warning(
        f"{warning}\n\nThe planner keeps the higher-priority task at its requested time and "
        "moves the other to the next free slot. Change one task's time if you want both exactly as asked."
    )

st.divider()

# ------------------------------------------------------------- Schedule
st.subheader("Today's plan")
if st.button("Generate schedule", type="primary"):
    st.session_state.plan = Scheduler(owner).generate_plan(today)

plan = st.session_state.get("plan")
if plan is not None:
    st.success(plan.summary())
    if plan.items:
        st.table([
            {
                "Time": f"{i.start:%H:%M}–{i.end:%H:%M}",
                "Pet": i.pet_name,
                "Task": i.task.title,
                "Priority": i.task.priority.name.lower(),
                "Why": i.reason,
            }
            for i in plan.items
        ])
    for task, why in plan.skipped:
        st.warning(f"Skipped **{task.title}**: {why}")
    for conflict in Scheduler(owner).detect_conflicts(plan):
        st.error(conflict.description)
