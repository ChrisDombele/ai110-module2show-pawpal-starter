"""PawPal+ core domain model and scheduler.

Implements the classes in diagrams/uml_draft.mmd. Attribute and method names
follow Python's snake_case convention (e.g. availableMinutes -> available_minutes).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import List, Optional


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
    completed: bool = False
    # Recurring tasks stay open; this records the last day one was done.
    last_completed: Optional[date] = None
    task_id: str = field(default_factory=_new_id)

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")

    def mark_complete(self, on: Optional[date] = None) -> None:
        """Complete the task. Recurring tasks only complete the given day (default today)."""
        if self.recurrence is Recurrence.NONE:
            self.completed = True
        else:
            self.last_completed = on or date.today()

    def is_due_on(self, day: date) -> bool:
        """Whether the task still needs doing on `day`."""
        if self.recurrence is Recurrence.NONE:
            if self.completed:
                return False
            return self.due_time is None or self.due_time.date() == day
        if self.last_completed == day:
            return False
        if self.due_time is None:
            return True
        start = self.due_time.date()
        if day < start:
            return False
        if self.recurrence is Recurrence.DAILY:
            return True
        return (day - start).days % 7 == 0  # weekly

    def reschedule(self, new_time: datetime) -> None:
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
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def get_tasks(self, day: Optional[date] = None) -> List[Task]:
        """All tasks, or only those due on `day`."""
        if day is None:
            return list(self.tasks)
        return [t for t in self.tasks if t.is_due_on(day)]


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
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        self.pets = [p for p in self.pets if p.pet_id != pet_id]

    def get_all_tasks(self) -> List[Task]:
        return [t for p in self.pets for t in p.tasks]

    def get_todays_tasks(self, day: Optional[date] = None) -> List[Task]:
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
        return sum(i.task.duration_minutes for i in self.items)

    def add_item(self, item: ScheduledItem) -> None:
        self.items.append(item)
        self.items.sort(key=lambda i: i.start)

    def summary(self) -> str:
        return (
            f"{len(self.items)} task(s) scheduled for {self.date:%A, %b %d} "
            f"({self.total_minutes} min), {len(self.skipped)} skipped."
        )

    def explain(self) -> str:
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
        self.owner = owner

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

    def fits_constraints(self, task: Task, slot: TimeWindow) -> bool:
        """Slot is long enough for the task and allowed by the owner's preferences."""
        length = _minutes(slot.end) - _minutes(slot.start)
        return length >= task.duration_minutes and self.owner.preferences.is_allowed(task, slot)

    def detect_conflicts(self, plan: DailyPlan) -> List[Conflict]:
        """Pairs of scheduled items whose times overlap."""
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

    def generate_plan(self, day: Optional[date] = None) -> DailyPlan:
        """Greedily place the highest-ranked tasks that fit the time budget and constraints."""
        day = day or date.today()
        plan = DailyPlan(date=day)
        owner_of = {t.task_id: p.name for p in self.owner.pets for t in p.tasks}
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
                pet_name=owner_of.get(task.task_id, ""),
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
