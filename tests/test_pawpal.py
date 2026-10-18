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


def test_recurring_task_due_again_next_day():
    t = Task("Meds", recurrence=Recurrence.DAILY)
    t.mark_complete(on=DAY)
    assert not t.is_due_on(DAY)
    assert t.is_due_on(date(2026, 10, 20))


def test_weekly_recurrence():
    t = Task("Bath", due_time=datetime(2026, 10, 12, 9, 0), recurrence=Recurrence.WEEKLY)
    assert t.is_due_on(DAY)
    assert not t.is_due_on(date(2026, 10, 20))
    assert not t.is_due_on(date(2026, 10, 5))  # before start


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
