"""Terminal demo of PawPal+ scheduling: sorting, filtering, recurrence, conflicts."""

from datetime import date, datetime, time

from pawpal_system import (
    Owner,
    Pet,
    Preferences,
    Priority,
    Recurrence,
    Scheduler,
    Task,
    TaskType,
)

today = date.today()


def at(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(today, time(hour, minute))


def show(title: str, tasks, scheduler: Scheduler) -> None:
    print(f"\n{title}")
    pet_of = scheduler._pet_names()
    if not tasks:
        print("  (none)")
    for t in tasks:
        when = f"{t.due_time:%m-%d %H:%M}" if t.due_time else "flexible   "
        status = "done" if t.completed else "open"
        print(f"  {when}  {t.title:<16} {pet_of.get(t.task_id, '?'):<8} {t.recurrence.value:<7} {status}")


owner = Owner("Jordan", available_minutes=150, preferences=Preferences(day_start=time(7), day_end=time(21)))
mochi, biscuit = Pet("Mochi", "dog", 4), Pet("Biscuit", "cat", 2)
owner.add_pet(mochi)
owner.add_pet(biscuit)
scheduler = Scheduler(owner)

# Added deliberately out of time order.
mochi.add_task(Task("Evening walk", TaskType.WALK, 30, Priority.MEDIUM, at(18)))
mochi.add_task(Task("Flea meds", TaskType.MEDS, 5, Priority.HIGH, recurrence=Recurrence.WEEKLY))
mochi.add_task(Task("Morning walk", TaskType.WALK, 30, Priority.HIGH, at(7, 30), Recurrence.DAILY))
biscuit.add_task(Task("Breakfast", TaskType.FEEDING, 10, Priority.HIGH, at(7, 45)))
biscuit.add_task(Task("Brush fur", TaskType.GROOMING, 15, Priority.LOW))
biscuit.add_task(Task("Play with wand", TaskType.ENRICHMENT, 20, Priority.MEDIUM, at(12)))

print("=== Sorting ===")
show("As added:", owner.get_all_tasks(), scheduler)
show("Sorted by time (flexible tasks last):", scheduler.sort_by_time(owner.get_all_tasks()), scheduler)

print("\n=== Filtering ===")
show("Mochi's tasks:", scheduler.filter_tasks(pet_name="Mochi"), scheduler)

print("\n=== Recurring tasks ===")
morning = next(t for t in mochi.tasks if t.title == "Morning walk")
print(f"Completing '{morning.title}' (daily, due {morning.due_time:%Y-%m-%d %H:%M})...")
following = scheduler.mark_task_complete(morning.task_id, on=today)
print(f"  -> new task created for {following.due_time:%Y-%m-%d %H:%M}")
show("Completed tasks:", scheduler.filter_tasks(completed=True), scheduler)
show("Open tasks for Mochi:", scheduler.filter_tasks("Mochi", completed=False), scheduler)

print("\n=== Conflict detection ===")
print("No conflicts yet:", scheduler.check_conflicts(today) or "none")
mochi.add_task(Task("Vet call", TaskType.OTHER, 20, Priority.HIGH, at(12, 10)))  # overlaps play time
biscuit.add_task(Task("Evening meds", TaskType.MEDS, 5, Priority.HIGH, at(18)))  # same time as walk
for warning in scheduler.check_conflicts(today):
    print(" ", warning)

print("\n=== Today's plan ===")
print(scheduler.generate_plan(today).explain())
