from datetime import date, datetime, time

import pytest

from pawpal_system import (
    DailyPlan,
    Owner,
    Pet,
    Preferences,
    Priority,
    Recurrence,
    ScheduledItem,
    Scheduler,
    Task,
    TaskType,
    TimeWindow,
)

DAY = date(2026, 10, 19)  # a Monday


def make_owner(minutes=120, **prefs):
    owner = Owner("Jordan", available_minutes=minutes, preferences=Preferences(**prefs))
    pet = Pet("Mochi")
    owner.add_pet(pet)
    return owner, pet


def test_add_pet_and_task():
    owner, pet = make_owner()
    pet.add_task(Task("Walk", TaskType.WALK))
    assert len(owner.get_all_tasks()) == 1
    owner.remove_pet(pet.pet_id)
    assert owner.get_all_tasks() == []


def test_remove_task():
    _, pet = make_owner()
    t = Task("Walk")
    pet.add_task(t)
    pet.remove_task(t.task_id)
    assert pet.tasks == []


def test_invalid_duration_rejected():
    with pytest.raises(ValueError):
        Task("Bad", duration_minutes=0)


def test_mark_complete_one_off():
    t = Task("Vet call")
    t.mark_complete()
    assert t.completed and not t.is_due_on(DAY)


def test_daily_completion_creates_next_day_task():
    t = Task("Meds", recurrence=Recurrence.DAILY)
    nxt = t.mark_complete(on=DAY)
    assert t.completed and not t.is_due_on(DAY)
    assert nxt is not None and nxt is not t and nxt.task_id != t.task_id
    assert not nxt.completed and nxt.title == "Meds"
    assert nxt.due_date == date(2026, 10, 20)  # today + timedelta(days=1)
    assert not nxt.is_due_on(DAY) and nxt.is_due_on(date(2026, 10, 20))


def test_weekly_completion_creates_task_seven_days_later():
    t = Task("Bath", due_time=datetime(2026, 10, 19, 9, 30), recurrence=Recurrence.WEEKLY)
    nxt = t.mark_complete(on=DAY)
    assert nxt.due_time == datetime(2026, 10, 26, 9, 30)  # same time of day


def test_daily_recurrence_rolls_over_month_end():
    t = Task("Meds", recurrence=Recurrence.DAILY)
    assert t.mark_complete(on=date(2026, 10, 31)).due_date == date(2026, 11, 1)


def test_one_off_completion_creates_no_next_task():
    assert Task("Vet").mark_complete(on=DAY) is None


def test_completing_twice_does_not_duplicate():
    t = Task("Meds", recurrence=Recurrence.DAILY)
    assert t.mark_complete(on=DAY) is not None
    assert t.mark_complete(on=DAY) is None


def test_open_recurring_task_carries_over_when_missed():
    t = Task("Bath", due_time=datetime(2026, 10, 12, 9, 0), recurrence=Recurrence.WEEKLY)
    assert t.is_due_on(DAY) and not t.is_due_on(date(2026, 10, 5))  # not before its start


def test_pet_complete_task_adds_next_occurrence():
    _, pet = make_owner()
    t = Task("Meds", recurrence=Recurrence.DAILY)
    pet.add_task(t)
    nxt = pet.complete_task(t.task_id, on=DAY)
    assert nxt in pet.tasks and len(pet.tasks) == 2
    with pytest.raises(KeyError):
        pet.complete_task("nope")


def test_scheduler_mark_task_complete_finds_owning_pet():
    owner, mochi = make_owner()
    biscuit = Pet("Biscuit")
    owner.add_pet(biscuit)
    t = Task("Feed", recurrence=Recurrence.DAILY)
    biscuit.add_task(t)
    nxt = Scheduler(owner).mark_task_complete(t.task_id, on=DAY)
    assert nxt in biscuit.tasks and mochi.tasks == []
    with pytest.raises(KeyError):
        Scheduler(owner).mark_task_complete("nope")


def test_completed_recurring_task_not_planned_today_but_next_is_tomorrow():
    owner, pet = make_owner()
    t = Task("Meds", recurrence=Recurrence.DAILY)
    pet.add_task(t)
    sched = Scheduler(owner)
    sched.mark_task_complete(t.task_id, on=DAY)
    assert sched.generate_plan(DAY).items == []
    assert len(sched.generate_plan(date(2026, 10, 20)).items) == 1


def test_one_off_timed_task_only_due_that_day():
    t = Task("Vet", due_time=datetime(2026, 10, 19, 10, 0))
    assert t.is_due_on(DAY) and not t.is_due_on(date(2026, 10, 20))


def test_reschedule():
    t = Task("Walk")
    t.reschedule(datetime(2026, 10, 19, 7, 0))
    assert t.due_time.hour == 7


def test_timewindow_overlap():
    a = TimeWindow(time(9), time(10))
    assert a.overlaps(TimeWindow(time(9, 30), time(11)))
    assert not a.overlaps(TimeWindow(time(10), time(11)))  # touching edges


def test_get_todays_tasks_filters():
    owner, pet = make_owner()
    pet.add_task(Task("Today", due_time=datetime(2026, 10, 19, 9)))
    pet.add_task(Task("Tomorrow", due_time=datetime(2026, 10, 20, 9)))
    assert [t.title for t in owner.get_todays_tasks(DAY)] == ["Today"]


def test_rank_by_priority_then_duration():
    owner, _ = make_owner()
    low = Task("low", priority=Priority.LOW)
    high_long = Task("high_long", priority=Priority.HIGH, duration_minutes=40)
    high_short = Task("high_short", priority=Priority.HIGH, duration_minutes=10)
    ranked = Scheduler(owner).rank_tasks([low, high_long, high_short])
    assert [t.title for t in ranked] == ["high_short", "high_long", "low"]


def test_preferred_type_breaks_priority_tie():
    owner, _ = make_owner(preferred_types=[TaskType.WALK])
    groom = Task("groom", TaskType.GROOMING, duration_minutes=5)
    walk = Task("walk", TaskType.WALK, duration_minutes=30)
    assert Scheduler(owner).rank_tasks([groom, walk])[0] is walk


def test_plan_respects_time_budget_and_skips_lowest_priority():
    owner, pet = make_owner(minutes=45)
    pet.add_task(Task("walk", duration_minutes=30, priority=Priority.HIGH))
    pet.add_task(Task("groom", duration_minutes=30, priority=Priority.LOW))
    plan = Scheduler(owner).generate_plan(DAY)
    assert [i.task.title for i in plan.items] == ["walk"]
    assert plan.skipped[0][0].title == "groom"
    assert plan.total_minutes <= 45


def test_timed_task_gets_requested_time():
    owner, pet = make_owner()
    pet.add_task(Task("meds", due_time=datetime(2026, 10, 19, 12, 0), duration_minutes=10))
    item = Scheduler(owner).generate_plan(DAY).items[0]
    assert item.start == time(12, 0) and item.end == time(12, 10)


def test_clashing_timed_task_is_moved_not_overlapped():
    owner, pet = make_owner()
    pet.add_task(Task("a", due_time=datetime(2026, 10, 19, 9), duration_minutes=30,
                      priority=Priority.HIGH))
    pet.add_task(Task("b", due_time=datetime(2026, 10, 19, 9, 15), duration_minutes=30))
    sched = Scheduler(owner)
    plan = sched.generate_plan(DAY)
    assert sched.detect_conflicts(plan) == []
    assert plan.items[1].start == time(9, 30)
    assert "unavailable" in plan.items[1].reason


def test_blocked_window_is_avoided():
    owner, pet = make_owner(blocked_windows=[TimeWindow(time(8), time(9))])
    pet.add_task(Task("walk", duration_minutes=30))
    assert Scheduler(owner).generate_plan(DAY).items[0].start == time(9, 0)


def test_task_skipped_when_day_too_short():
    owner, pet = make_owner(day_start=time(8), day_end=time(8, 20))
    pet.add_task(Task("walk", duration_minutes=30))
    plan = Scheduler(owner).generate_plan(DAY)
    assert plan.items == [] and "no free slot" in plan.skipped[0][1]


def test_completed_tasks_not_planned():
    owner, pet = make_owner()
    t = Task("done")
    t.mark_complete()
    pet.add_task(t)
    assert Scheduler(owner).generate_plan(DAY).items == []


def test_detect_conflicts_flags_overlap():
    owner, _ = make_owner()
    plan = DailyPlan(DAY)
    plan.add_item(ScheduledItem(Task("a"), time(9), time(10)))
    plan.add_item(ScheduledItem(Task("b"), time(9, 30), time(10, 30)))
    assert len(Scheduler(owner).detect_conflicts(plan)) == 1


def test_explain_mentions_scheduled_and_skipped():
    owner, pet = make_owner(minutes=20)
    pet.add_task(Task("walk", duration_minutes=20, priority=Priority.HIGH))
    pet.add_task(Task("groom", duration_minutes=20, priority=Priority.LOW))
    text = Scheduler(owner).generate_plan(DAY).explain()
    assert "walk" in text and "Not scheduled" in text and "groom" in text


def test_scheduler_plans_tasks_from_all_pets():
    owner, mochi = make_owner()
    biscuit = Pet("Biscuit", species="cat")
    owner.add_pet(biscuit)
    mochi.add_task(Task("walk", duration_minutes=20))
    biscuit.add_task(Task("feed", duration_minutes=10))
    plan = Scheduler(owner).generate_plan(DAY)
    assert {(i.pet_name, i.task.title) for i in plan.items} == {("Mochi", "walk"), ("Biscuit", "feed")}


def at(hour, minute=0):
    return datetime(2026, 10, 19, hour, minute)


def test_sort_by_time_orders_hhmm_and_puts_flexible_last():
    owner, _ = make_owner()
    tasks = [
        Task("late", due_time=at(18, 5)),
        Task("flex"),
        Task("early", due_time=at(7, 45)),
        Task("noon", due_time=at(12, 0)),
    ]
    assert [t.title for t in Scheduler(owner).sort_by_time(tasks)] == [
        "early", "noon", "late", "flex",
    ]


def test_sort_by_time_is_stable_for_equal_times():
    owner, _ = make_owner()
    a, b = Task("a", due_time=at(9)), Task("b", due_time=at(9))
    assert Scheduler(owner).sort_by_time([a, b]) == [a, b]


def test_sort_by_time_does_not_mutate_input():
    owner, _ = make_owner()
    tasks = [Task("b", due_time=at(10)), Task("a", due_time=at(8))]
    Scheduler(owner).sort_by_time(tasks)
    assert tasks[0].title == "b"


def _two_pets():
    owner, mochi = make_owner()
    biscuit = Pet("Biscuit", species="cat")
    owner.add_pet(biscuit)
    done = Task("done")
    done.mark_complete()
    mochi.add_task(Task("walk"))
    mochi.add_task(done)
    biscuit.add_task(Task("feed"))
    return owner, Scheduler(owner)


def test_filter_by_pet_name_is_case_insensitive():
    _, sched = _two_pets()
    assert {t.title for t in sched.filter_tasks(pet_name="mochi")} == {"walk", "done"}
    assert sched.filter_tasks(pet_name="Ghost") == []


def test_filter_by_completion_status():
    _, sched = _two_pets()
    assert [t.title for t in sched.filter_tasks(completed=True)] == ["done"]
    assert {t.title for t in sched.filter_tasks(completed=False)} == {"walk", "feed"}


def test_filter_by_pet_and_status_and_no_filters():
    _, sched = _two_pets()
    assert [t.title for t in sched.filter_tasks("Mochi", completed=False)] == ["walk"]
    assert len(sched.filter_tasks()) == 3


def test_check_conflicts_same_time_same_pet():
    owner, pet = make_owner()
    pet.add_task(Task("walk", due_time=at(9)))
    pet.add_task(Task("groom", due_time=at(9)))
    warnings = Scheduler(owner).check_conflicts(DAY)
    assert len(warnings) == 1 and "walk" in warnings[0] and "groom" in warnings[0]


def test_check_conflicts_across_different_pets():
    owner, mochi = make_owner()
    biscuit = Pet("Biscuit")
    owner.add_pet(biscuit)
    mochi.add_task(Task("walk", duration_minutes=30, due_time=at(9)))
    biscuit.add_task(Task("feed", duration_minutes=10, due_time=at(9, 20)))  # overlaps, not equal
    (warning,) = Scheduler(owner).check_conflicts(DAY)
    assert "Mochi" in warning and "Biscuit" in warning and warning.startswith("Warning")


def test_check_conflicts_none_when_back_to_back_flexible_or_other_day():
    owner, pet = make_owner()
    pet.add_task(Task("a", duration_minutes=30, due_time=at(9)))
    pet.add_task(Task("b", duration_minutes=30, due_time=at(9, 30)))  # touches only
    pet.add_task(Task("flex"))
    pet.add_task(Task("other day", due_time=datetime(2026, 10, 20, 9)))
    assert Scheduler(owner).check_conflicts(DAY) == []


def test_check_conflicts_does_not_raise_on_empty_owner():
    assert Scheduler(Owner("Nobody")).check_conflicts(DAY) == []


def test_adding_task_increases_pet_task_count():
    _, pet = make_owner()
    assert len(pet.tasks) == 0
    pet.add_task(Task("Walk"))
    assert len(pet.tasks) == 1
    pet.add_task(Task("Feed"))
    assert len(pet.tasks) == 2


def test_pet_with_no_tasks_gives_empty_plan():
    owner, pet = make_owner()
    plan = Scheduler(owner).generate_plan(DAY)
    assert pet.tasks == [] and plan.items == [] and plan.skipped == []
    assert "0 task(s)" in plan.summary()
