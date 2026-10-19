# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🧩 Implementation Summary

The logic lives in [`pawpal_system.py`](pawpal_system.py); [`app.py`](app.py) (Streamlit) and
[`main.py`](main.py) (terminal demo) both sit on top of it. The class diagram is in
[`diagrams/uml_draft.mmd`](diagrams/uml_draft.mmd).

- **`Task`**: one activity: title, type, duration, priority, optional preferred time, recurrence, completion status.
- **`Pet`**: pet details plus its list of tasks (`add_task`, `remove_task`, `complete_task`).
- **`Owner`**: holds several pets, the owner's available minutes and `Preferences`
  (day window, blocked times, preferred task types). `Owner.get_all_tasks()` returns every pet's tasks together.
- **`Scheduler`**: the "brain". It reads tasks through `Owner.get_all_tasks()` (never from a single pet),
  then sorts, filters, checks conflicts and builds a `DailyPlan`.
- **`DailyPlan` / `ScheduledItem`**: the result. Each item records its time slot and *why* it was placed;
  skipped tasks record why they were left out. `DailyPlan.explain()` prints it all.

**How the plan is built:** due-today tasks are ranked by priority (then preferred type, requested time, shorter first),
then placed greedily into the earliest free slot that fits the owner's time budget, day window and blocked times.

## 🖥️ Sample Output

Output of `python main.py` (tasks are added out of order on purpose):

```
=== Sorting ===

As added:
  10-18 18:00  Evening walk     Mochi    none    open
  flexible     Flea meds        Mochi    weekly  open
  10-18 07:30  Morning walk     Mochi    daily   open
  10-18 07:45  Breakfast        Biscuit  none    open
  flexible     Brush fur        Biscuit  none    open
  10-18 12:00  Play with wand   Biscuit  none    open

Sorted by time (flexible tasks last):
  10-18 07:30  Morning walk     Mochi    daily   open
  10-18 07:45  Breakfast        Biscuit  none    open
  10-18 12:00  Play with wand   Biscuit  none    open
  10-18 18:00  Evening walk     Mochi    none    open
  flexible     Flea meds        Mochi    weekly  open
  flexible     Brush fur        Biscuit  none    open

=== Filtering ===

Mochi's tasks:
  10-18 18:00  Evening walk     Mochi    none    open
  flexible     Flea meds        Mochi    weekly  open
  10-18 07:30  Morning walk     Mochi    daily   open

=== Recurring tasks ===
Completing 'Morning walk' (daily, due 2026-10-18 07:30)...
  -> new task created for 2026-10-19 07:30

Completed tasks:
  10-18 07:30  Morning walk     Mochi    daily   done

Open tasks for Mochi:
  10-18 18:00  Evening walk     Mochi    none    open
  flexible     Flea meds        Mochi    weekly  open
  10-19 07:30  Morning walk     Mochi    daily   open

=== Conflict detection ===
No conflicts yet: none
  Warning: 'Play with wand' (Biscuit, 12:00-12:20) overlaps 'Vet call' (Mochi, 12:10-12:30)
  Warning: 'Evening walk' (Mochi, 18:00-18:30) overlaps 'Evening meds' (Biscuit, 18:00-18:05)

=== Today's plan ===
7 task(s) scheduled for Sunday, Oct 18 (105 min), 0 skipped.

07:00-07:05 Flea meds [Mochi]: high priority; flexible time, placed in the earliest free slot; repeats weekly
07:05-07:20 Brush fur [Biscuit]: low priority; flexible time, placed in the earliest free slot
07:45-07:55 Breakfast [Biscuit]: high priority; scheduled at its requested time
12:10-12:30 Vet call [Mochi]: high priority; scheduled at its requested time
12:30-12:50 Play with wand [Biscuit]: medium priority; requested 12:00 was unavailable, moved to next free slot
18:00-18:05 Evening meds [Biscuit]: high priority; scheduled at its requested time
18:05-18:35 Evening walk [Mochi]: medium priority; requested 18:00 was unavailable, moved to next free slot
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
python -m pytest

# Run with coverage:
pytest --cov
```

The tests in [`tests/test_pawpal.py`](tests/test_pawpal.py) cover task completion and recurrence, adding/removing
pets and tasks, ranking, sorting, filtering, the time budget, blocked windows, conflict warnings and plan explanations.

Sample test output:

```
.......................................                                  [100%]
39 passed in 0.04s
```

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `Scheduler.rank_tasks()` | `sort_by_time` orders by `"HH:MM"` (flexible tasks last, stable for ties). `rank_tasks` orders by priority, then preferred type, requested time, shorter duration. |
| Filtering | `Scheduler.filter_tasks(pet_name, completed)`, `Pet.get_tasks(day)`, `Owner.get_todays_tasks(day)` | Filter by pet name (case-insensitive), by completion status, or by what is due on a given day. |
| Conflict handling | `Scheduler.check_conflicts()`, `Scheduler.detect_conflicts()` | `check_conflicts` returns warning strings (never raises) when requested times overlap, within or across pets. `detect_conflicts` checks a finished plan. `generate_plan` itself moves a clashing task to the next free slot. |
| Recurring tasks | `Task.mark_complete()`, `Pet.complete_task()`, `Scheduler.mark_task_complete()` | Completing a daily/weekly task creates the next one (today + 1 or + 7 days via `timedelta`, same time of day). An open recurring task carries over if missed. |
| Time budget | `Scheduler.generate_plan()` | Skips lower-priority tasks that no longer fit, and explains why. |

**Tradeoff:** the planner is greedy (highest priority first, earliest slot, no backtracking), so it is fast and easy
to explain but not guaranteed to fit the maximum number of minutes. Conflict warnings compare *requested* times only.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. Install requirements and run streamlit run app.py
2. Enter a name, minutes available, and the start and end of the day
3. Add a windows like lunch when ther is nothing to schedule
4. Enter a name for a pet along with species and age
5. Choose the pet and set the title, type duration, priority and a repeat rule
6. Review the task list across all of the pets. There will be a warning if there is a time overlap
7. Read the summary plan table along with the summary line
8. Each skipped task that appears will show a reason if there is one
9. Change the minutes, day window, add more pets, tasks, and blocked times if needed

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
