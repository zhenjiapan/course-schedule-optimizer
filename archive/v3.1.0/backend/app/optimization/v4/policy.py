"""Versioned V4 request data. Minutes are local campus time."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Day = Annotated[int, Field(ge=1, le=7)]
Rating = Annotated[int, Field(strict=True, ge=1, le=5)]
Minute = Annotated[int, Field(ge=0, le=1440)]
Period = Literal["morning", "afternoon", "evening"]
Category = Literal["T", "W", "H", "D", "B"]
Selection = tuple[str, str]
PERIODS = {"morning": (0, 720), "afternoon": (720, 1080), "evening": (1080, 1440)}
VERSION = "v4.1"
HALF = 30
GAP_TOLERANCE = 10
BALANCED_GAP = (10, 40)
GAP_SCALE = 60


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Boundary(Input):
    minute: Minute
    mode: Literal["hard", "soft"]


class CountRule(Input):
    target: int = Field(ge=0, le=48)
    comparison: Literal["exactly", "at_most", "at_least"]
    tolerance: int = Field(default=2, ge=1, le=48)


class FreeDays(Input):
    minimum: int = Field(ge=0, le=5)
    mode: Literal["hard", "soft"]


class Policy(Input):
    credit_min: Decimal = Field(default=12, ge=0, allow_inf_nan=False)
    credit_max: Decimal = Field(default=18, ge=0, allow_inf_nan=False)
    required: list[Selection] = Field(default_factory=list, max_length=500)
    locked: list[Selection] = Field(default_factory=list, max_length=500)
    excluded: list[Selection] = Field(default_factory=list, max_length=500)
    banned_days: set[Day] = Field(default_factory=set)
    blocked: list[tuple[Day, Minute, Minute]] = Field(default_factory=list, max_length=100)
    earliest: Boundary | None = None
    latest: Boundary | None = None
    early: Rating | None = None
    ban_early: bool = False
    weekdays: dict[Day, Rating] = Field(default_factory=dict)
    periods: dict[Period, Rating] = Field(default_factory=dict)
    teachers: dict[str, Rating] = Field(default_factory=dict, max_length=500)
    gaps: Literal["compact", "balanced", "spacious"] | None = None
    counts: dict[Period, CountRule] = Field(default_factory=dict)
    distribution: Literal["concentrated", "distributed"] | None = None
    free_days: FreeDays | None = None
    weights: dict[Category, Rating] = Field(default_factory=dict)
    disabled: set[Category] = Field(default_factory=set)
    evaluation_days: set[date] = Field(default_factory=set, max_length=366)
    teaching_weeks: set[date] = Field(default_factory=set, max_length=53)

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.credit_min > self.credit_max:
            raise ValueError("Minimum credits exceed maximum credits.")
        if any(start == end or start == 1440 for _, start, end in self.blocked):
            raise ValueError("Blocked intervals must be nonempty.")
        if any(d.isoweekday() != 1 for d in self.teaching_weeks):
            raise ValueError("Teaching weeks must be identified by their Monday.")
        if self.earliest and self.latest and self.earliest.mode == self.latest.mode == "hard":
            if self.earliest.minute >= self.latest.minute:
                raise ValueError("Hard earliest time must precede hard latest time.")
        return self

    def blocks(self):
        intervals = []
        for weekday, start, end in self.blocked:
            if end > start:
                intervals.append((weekday, start, end))
            else:
                intervals.append((weekday, start, 1440))
                if end:
                    intervals.append((weekday % 7 + 1, 0, end))
        merged = []
        for day, start, end in sorted(intervals):
            if merged and day == merged[-1][0] and start <= merged[-1][2]:
                previous = merged.pop()
                merged.append((day, previous[1], max(previous[2], end)))
            else:
                merged.append((day, start, end))
        return merged
