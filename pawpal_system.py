"""PawPal+ core domain model and scheduler.

Implements the classes in diagrams/uml_draft.mmd. Attribute and method names
follow Python's snake_case convention (e.g. availableMinutes -> available_minutes).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Optional


def _minutes(t: time) -> int:
    """Minutes since midnight for a time of day."""
    return t.hour * 60 + t.minute


def _to_time(minutes: int) -> time:
    return time(minutes // 60, minutes % 60)


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


class TaskType(Enum):
    WALK = "walk"
    FEEDING = "feeding"
    MEDS = "meds"
    ENRICHMENT = "enrichment"
    GROOMING = "grooming"
    OTHER = "other"


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Recurrence(Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class TimeWindow:
    start: time
    end: time

    def overlaps(self, other: TimeWindow) -> bool:
        """True if the two windows share any time (touching edges don't count)."""
        return self.start < other.end and other.start < self.end


@dataclass
class Task:
    title: str
    type: TaskType = TaskType.OTHER
    duration_minutes: int = 15
    priority: Priority = Priority.MEDIUM
    # Preferred start. With no due_time the task is "floating": any time of day.
    due_time: Optional[datetime] = None
    recurrence: Recurrence = Recurrence.NONE
    # Day a floating (no due_time) task is due; set on auto-created recurrences.
    due_date: Optional[date] = None
    completed: bool = False
    task_id: str = field(default_factory=_new_id)

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")

    def _base_date(self) -> Optional[date]:
        """The day this task is (first) due, or None if it has no date at all."""
        if self.due_date is not None:
            return self.due_date
        return self.due_time.date() if self.due_time else None

    def mark_complete(self, on: Optional[date] = None) -> Optional[Task]:
        """Mark the task done; for a daily/weekly task, return its next occurrence.

        The next occurrence is a new Task due `on` (default today) plus one day
        (daily) or seven days (weekly), keeping the same time of day. The caller is
        responsible for storing it (see Pet.complete_task). One-off tasks, and tasks
        that were already complete, return None.
        """
        if self.completed:
            return None
        self.completed = True
        if self.recurrence is Recurrence.NONE:
            return None
        step = timedelta(days=1 if self.recurrence is Recurrence.DAILY else 7)
        next_day = (on or date.today()) + step
        if self.due_time:
            return replace(
                self, task_id=_new_id(), completed=False, due_date=None,
                due_time=datetime.combine(next_day, self.due_time.time()),
            )
        return replace(self, task_id=_new_id(), completed=False, due_date=next_day)

    def is_due_on(self, day: date) -> bool:
        """Whether the task still needs doing on `day`.

        Completed tasks never are. A one-off dated task is due only on its date; an
        open recurring task is due from its date onward (so a missed one carries
        over); a task with no date is due every day until completed.
        """
        if self.completed:
            return False
        base = self._base_date()
        if base is None:
            return True
        if self.recurrence is Recurrence.NONE:
            return base == day
        return day >= base

    def reschedule(self, new_time: datetime) -> None:
        """Change the task's preferred start time."""
        self.due_time = new_time


@dataclass
class Pet:
    name: str
    species: str = "dog"
    age: int = 0
    notes: str = ""
    tasks: List[Task] = field(default_factory=list)
    pet_id: str = field(default_factory=_new_id)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove the task with the given id, if present."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def get_tasks(self, day: Optional[date] = None) -> List[Task]:
        """All tasks, or only those due on `day`."""
        if day is None:
            return list(self.tasks)
        return [t for t in self.tasks if t.is_due_on(day)]

    def complete_task(self, task_id: str, on: Optional[date] = None) -> Optional[Task]:
        """Complete one of this pet's tasks and add its next occurrence, if any.

        Returns the newly created task for recurring tasks, otherwise None.
        Raises KeyError if the pet has no task with that id.
        """
        task = next((t for t in self.tasks if t.task_id == task_id), None)
        if task is None:
            raise KeyError(f"{self.name} has no task {task_id!r}")
        following = task.mark_complete(on)
        if following is not None:
            self.add_task(following)
        return following


@dataclass
class Preferences:
    day_start: time = time(8, 0)
    day_end: time = time(20, 0)
    preferred_types: List[TaskType] = field(default_factory=list)
    blocked_windows: List[TimeWindow] = field(default_factory=list)

    def is_allowed(self, task: Task, slot: TimeWindow) -> bool:
        """A slot is allowed if it lies inside the owner's day and avoids blocked windows."""
        if slot.start < self.day_start or slot.end > self.day_end:
            return False
        return not any(slot.overlaps(w) for w in self.blocked_windows)


@dataclass
class Owner:
    name: str
    available_minutes: int = 120
    preferences: Preferences = field(default_factory=Preferences)
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        """Remove the pet with the given id, if present."""
        self.pets = [p for p in self.pets if p.pet_id != pet_id]

    def get_pet(self, name: str) -> Optional[Pet]:
        """Find a pet by name (case-insensitive), or None."""
        return next((p for p in self.pets if p.name.lower() == name.lower()), None)

    def get_all_tasks(self) -> List[Task]:
        """Every task from every pet, combined into one list."""
        return [t for p in self.pets for t in p.tasks]

    def get_todays_tasks(self, day: Optional[date] = None) -> List[Task]:
        """All pets' tasks that are due on `day` (default today)."""
        day = day or date.today()
        return [t for t in self.get_all_tasks() if t.is_due_on(day)]


@dataclass
class ScheduledItem:
    task: Task
    start: time
    end: time
    reason: str = ""
    pet_name: str = ""


@dataclass
class Conflict:
    first: Task
    second: Task
    description: str


@dataclass
class DailyPlan:
    date: date
    items: List[ScheduledItem] = field(default_factory=list)
    skipped: List[tuple] = field(default_factory=list)  # (Task, reason) pairs

    @property
    def total_minutes(self) -> int:
        """Total duration of all scheduled items."""
        return sum(i.task.duration_minutes for i in self.items)

    def add_item(self, item: ScheduledItem) -> None:
        """Add an item to the plan, keeping items ordered by start time."""
        self.items.append(item)
        self.items.sort(key=lambda i: i.start)

    def summary(self) -> str:
        """One-line count of scheduled and skipped tasks."""
        return (
            f"{len(self.items)} task(s) scheduled for {self.date:%A, %b %d} "
            f"({self.total_minutes} min), {len(self.skipped)} skipped."
        )

    def explain(self) -> str:
        """Multi-line plan with a reason for each task and why others were skipped."""
        lines = [self.summary(), ""]
        for i in self.items:
            who = f" [{i.pet_name}]" if i.pet_name else ""
            lines.append(f"{i.start:%H:%M}-{i.end:%H:%M} {i.task.title}{who}: {i.reason}")
        if self.skipped:
            lines += ["", "Not scheduled:"]
            lines += [f"- {t.title}: {why}" for t, why in self.skipped]
        return "\n".join(lines)


class Scheduler:
    def __init__(self, owner: Owner) -> None:
        """Create a scheduler that plans for all of `owner`'s pets."""
        self.owner = owner

    # ------------------------------------------------------- organizing tasks
    def sort_by_time(self, tasks: List[Task]) -> List[Task]:
        """Return `tasks` ordered by time of day, earliest first.

        The sort key is the "HH:MM" string of each task's due_time; zero-padded
        24-hour strings sort chronologically as plain text. Only the time of day
        is used, not the date. Tasks with no time ("flexible") go last, and ties
        keep their original order because sorted() is stable.
        """
        return sorted(
            tasks,
            key=lambda t: (t.due_time is None, t.due_time.strftime("%H:%M") if t.due_time else ""),
        )

    def filter_tasks(
        self, pet_name: Optional[str] = None, completed: Optional[bool] = None
    ) -> List[Task]:
        """Tasks across the owner's pets, optionally narrowed by pet and/or status.

        pet_name: only that pet's tasks (case-insensitive; unknown name -> empty list).
        completed: True for finished tasks, False for open ones, None for both.
        """
        if pet_name is None:
            tasks = self.owner.get_all_tasks()
        else:
            pet = self.owner.get_pet(pet_name)
            tasks = pet.get_tasks() if pet else []
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        return tasks

    def mark_task_complete(self, task_id: str, on: Optional[date] = None) -> Optional[Task]:
        """Complete a task on whichever pet owns it; return the next occurrence if recurring.

        Raises KeyError if no pet has a task with that id.
        """
        for pet in self.owner.pets:
            if any(t.task_id == task_id for t in pet.tasks):
                return pet.complete_task(task_id, on)
        raise KeyError(f"No task with id {task_id!r}")

    def rank_tasks(self, tasks: List[Task]) -> List[Task]:
        """Order by priority (high first), then preferred types, timed tasks, shorter first."""
        preferred = set(self.owner.preferences.preferred_types)
        return sorted(
            tasks,
            key=lambda t: (
                -t.priority.value,
                t.type not in preferred,
                t.due_time is None,
                _minutes(t.due_time.time()) if t.due_time else 0,
                t.duration_minutes,
            ),
        )

    # ------------------------------------------------------------- conflicts
    def check_conflicts(self, day: Optional[date] = None) -> List[str]:
        """Warn about tasks whose *requested* times overlap on `day`.

        A lightweight check: it never raises or changes anything, it just returns
        human-readable warnings (an empty list means no conflicts). It looks at
        every pet's tasks, so it catches clashes within a pet and between pets.
        Tasks without a requested time can always be moved, so they are ignored.
        """
        day = day or date.today()
        pet_of = self._pet_names()
        timed = self.sort_by_time(
            [t for t in self.owner.get_all_tasks() if t.due_time and t.is_due_on(day)]
        )
        warnings = []
        for n, a in enumerate(timed):
            for b in timed[n + 1:]:
                if self._requested_window(a).overlaps(self._requested_window(b)):
                    warnings.append(
                        f"Warning: {self._describe(a, pet_of)} overlaps {self._describe(b, pet_of)}"
                    )
        return warnings

    def detect_conflicts(self, plan: DailyPlan) -> List[Conflict]:
        """Pairs of scheduled items in a plan whose times overlap."""
        conflicts = []
        items = sorted(plan.items, key=lambda i: i.start)
        for n, a in enumerate(items):
            for b in items[n + 1:]:
                if TimeWindow(a.start, a.end).overlaps(TimeWindow(b.start, b.end)):
                    conflicts.append(Conflict(
                        a.task, b.task,
                        f"'{a.task.title}' ({a.start:%H:%M}-{a.end:%H:%M}) overlaps "
                        f"'{b.task.title}' ({b.start:%H:%M}-{b.end:%H:%M})",
                    ))
        return conflicts

    def _pet_names(self) -> Dict[str, str]:
        """Map task id -> name of the pet that owns it."""
        return {t.task_id: p.name for p in self.owner.pets for t in p.tasks}

    @staticmethod
    def _requested_window(task: Task) -> TimeWindow:
        start = _minutes(task.due_time.time())
        return TimeWindow(_to_time(start), _to_time(min(start + task.duration_minutes, 1439)))

    @staticmethod
    def _describe(task: Task, pet_of: Dict[str, str]) -> str:
        w = Scheduler._requested_window(task)
        return f"'{task.title}' ({pet_of.get(task.task_id, '?')}, {w.start:%H:%M}-{w.end:%H:%M})"

    # -------------------------------------------------------------- planning
    def fits_constraints(self, task: Task, slot: TimeWindow) -> bool:
        """Slot is long enough for the task and allowed by the owner's preferences."""
        length = _minutes(slot.end) - _minutes(slot.start)
        return length >= task.duration_minutes and self.owner.preferences.is_allowed(task, slot)

    def generate_plan(self, day: Optional[date] = None) -> DailyPlan:
        """Greedily place the highest-ranked tasks that fit the time budget and constraints."""
        day = day or date.today()
        plan = DailyPlan(date=day)
        pet_of = self._pet_names()
        budget = self.owner.available_minutes

        # Read tasks for all pets through the Owner, then keep only those due today.
        due_today = [t for t in self.owner.get_all_tasks() if t.is_due_on(day)]
        for task in self.rank_tasks(due_today):
            if task.duration_minutes > budget:
                plan.skipped.append((
                    task,
                    f"needs {task.duration_minutes} min but only {budget} min of the "
                    f"owner's time remained",
                ))
                continue
            slot = self._find_slot(task, plan)
            if slot is None:
                plan.skipped.append((task, "no free slot within the owner's day and preferences"))
                continue
            budget -= task.duration_minutes
            plan.add_item(ScheduledItem(
                task=task,
                start=slot.start,
                end=slot.end,
                reason=self._reason(task, slot),
                pet_name=pet_of.get(task.task_id, ""),
            ))
        return plan

    def _find_slot(self, task: Task, plan: DailyPlan) -> Optional[TimeWindow]:
        """Earliest allowed gap at or after the task's preferred start (or day start)."""
        prefs = self.owner.preferences
        start = _minutes(task.due_time.time()) if task.due_time else _minutes(prefs.day_start)
        start = max(start, _minutes(prefs.day_start))
        day_end = _minutes(prefs.day_end)
        busy = [(_minutes(i.start), _minutes(i.end)) for i in plan.items]

        while start + task.duration_minutes <= day_end:
            slot = TimeWindow(_to_time(start), _to_time(start + task.duration_minutes))
            blockers = [(s, e) for s, e in busy if s < start + task.duration_minutes and start < e]
            blockers += [
                (_minutes(w.start), _minutes(w.end))
                for w in prefs.blocked_windows
                if slot.overlaps(w)
            ]
            if not blockers:
                return slot if self.fits_constraints(task, slot) else None
            start = max(e for _, e in blockers)  # jump past whatever is in the way
        return None

    def _reason(self, task: Task, slot: TimeWindow) -> str:
        """Plain-English explanation of why `task` was placed in `slot`."""
        parts = [f"{task.priority.name.lower()} priority"]
        if task.type in self.owner.preferences.preferred_types:
            parts.append("preferred task type")
        if task.due_time is None:
            parts.append("flexible time, placed in the earliest free slot")
        elif _minutes(task.due_time.time()) == _minutes(slot.start):
            parts.append("scheduled at its requested time")
        else:
            parts.append(
                f"requested {task.due_time:%H:%M} was unavailable, moved to next free slot"
            )
        if task.recurrence is not Recurrence.NONE:
            parts.append(f"repeats {task.recurrence.value}")
        return "; ".join(parts)
