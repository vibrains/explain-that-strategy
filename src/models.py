"""Data models for F1 strategy simulation.

This module defines dataclasses for type-safe representation of
stints, pit stops, strategies, and simulation results.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Stint:
    """A single tire stint during a race.

    Attributes:
        compound: Tire compound (SOFT, MEDIUM, HARD, INTERMEDIATE, WET).
        start_lap: First lap of the stint (1-indexed).
        end_lap: Last lap of the stint (inclusive).
    """
    compound: str
    start_lap: int
    end_lap: int

    def __post_init__(self):
        """Validate stint data."""
        if self.start_lap < 1:
            raise ValueError(f"start_lap must be >= 1, got {self.start_lap}")
        if self.end_lap < self.start_lap:
            raise ValueError(
                f"end_lap ({self.end_lap}) must be >= start_lap ({self.start_lap})"
            )
        if not self.compound:
            raise ValueError("compound cannot be empty")

    @property
    def length(self) -> int:
        """Return the number of laps in this stint."""
        return self.end_lap - self.start_lap + 1


@dataclass(frozen=True)
class PitStop:
    """A pit stop event.

    Attributes:
        lap: The lap number where the pit stop occurs.
        from_compound: The tire compound before the stop.
        to_compound: The tire compound after the stop.
        under_sc: Whether the stop was under SC/VSC ('SC', 'VSC', or None).
    """
    lap: int
    from_compound: str
    to_compound: str
    under_sc: Optional[str] = None

    def __post_init__(self):
        """Validate pit stop data."""
        if self.lap < 1:
            raise ValueError(f"lap must be >= 1, got {self.lap}")
        if not self.from_compound:
            raise ValueError("from_compound cannot be empty")
        if not self.to_compound:
            raise ValueError("to_compound cannot be empty")
        if self.under_sc not in (None, "SC", "VSC"):
            raise ValueError(f"under_sc must be 'SC', 'VSC', or None, got {self.under_sc}")

    @property
    def time_saved_vs_normal(self) -> float:
        """Calculate time saved compared to a normal pit stop."""
        from src.config import PIT_STOP_LOSS_NORMAL, PIT_STOP_LOSS_SC, PIT_STOP_LOSS_VSC

        if self.under_sc == "SC":
            return PIT_STOP_LOSS_NORMAL - PIT_STOP_LOSS_SC
        elif self.under_sc == "VSC":
            return PIT_STOP_LOSS_NORMAL - PIT_STOP_LOSS_VSC
        return 0.0


@dataclass
class Strategy:
    """A complete race strategy.

    Attributes:
        name: Human-readable description of the strategy.
        stops: Ordered list of pit stops.
        first_compound: Starting tire compound.
        sc_opportunistic: Whether this strategy exploits SC/VSC periods.
        weather_aware: Whether this strategy responds to weather changes.
    """
    name: str
    stops: List[PitStop] = field(default_factory=list)
    first_compound: str = "MEDIUM"
    sc_opportunistic: bool = False
    weather_aware: bool = False

    def __post_init__(self):
        """Validate strategy data."""
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.first_compound:
            raise ValueError("first_compound cannot be empty")

    @property
    def num_stops(self) -> int:
        """Return the number of pit stops in this strategy."""
        return len(self.stops)

    @property
    def compounds(self) -> List[str]:
        """Return the sequence of compounds used (including start compound)."""
        compounds = [self.first_compound]
        for stop in self.stops:
            compounds.append(stop.to_compound)
        return compounds

    def to_sim_format(self) -> Tuple[List[Dict[str, Any]], str]:
        """Convert to format expected by simulate_strategy()."""
        stops_dict = [
            {
                "lap": stop.lap,
                "compound": self.first_compound if i == 0 else self.stops[i - 1].to_compound,
                "next_compound": stop.to_compound,
            }
            for i, stop in enumerate(self.stops)
        ]
        return stops_dict, self.first_compound


@dataclass
class LapTime:
    """A single lap time with context.

    Attributes:
        lap: Lap number.
        time: Lap time in seconds.
        compound: Tire compound used.
        tire_age: Number of laps on current tires.
        sc_type: Safety car type ('SC', 'VSC', or None).
        rainfall: Whether it was raining.
    """
    lap: int
    time: float
    compound: str
    tire_age: int
    sc_type: Optional[str] = None
    rainfall: bool = False

    def __post_init__(self):
        """Validate lap time data."""
        if self.lap < 1:
            raise ValueError(f"lap must be >= 1, got {self.lap}")
        if self.time <= 0:
            raise ValueError(f"time must be positive, got {self.time}")
        if self.tire_age < 0:
            raise ValueError(f"tire_age must be non-negative, got {self.tire_age}")
        if self.sc_type not in (None, "SC", "VSC"):
            raise ValueError(f"sc_type must be 'SC', 'VSC', or None, got {self.sc_type}")


@dataclass
class SimulationResult:
    """Result of a strategy simulation.

    Attributes:
        total_time: Total race time in seconds.
        lap_times: List of lap time data.
        stints: List of stints.
        strategy: The strategy that was simulated.
    """
    total_time: float
    lap_times: List[LapTime]
    stints: List[Stint]
    strategy: Optional[Strategy] = None

    def __post_init__(self):
        """Validate simulation result."""
        if self.total_time <= 0:
            raise ValueError(f"total_time must be positive, got {self.total_time}")

    @property
    def average_lap_time(self) -> float:
        """Calculate average lap time."""
        if not self.lap_times:
            return 0.0
        return self.total_time / len(self.lap_times)


@dataclass
class SCPeriod:
    """A Safety Car or Virtual Safety Car period.

    Attributes:
        type: 'SC' or 'VSC'.
        start_lap: First lap of the period.
        end_lap: Last lap of the period (inclusive).
    """
    type: str
    start_lap: int
    end_lap: int

    def __post_init__(self):
        """Validate SC period data."""
        if self.type not in ("SC", "VSC"):
            raise ValueError(f"type must be 'SC' or 'VSC', got {self.type}")
        if self.start_lap < 1:
            raise ValueError(f"start_lap must be >= 1, got {self.start_lap}")
        if self.end_lap < self.start_lap:
            raise ValueError(
                f"end_lap ({self.end_lap}) must be >= start_lap ({self.start_lap})"
            )

    @property
    def duration_laps(self) -> int:
        """Return the number of laps this period covers."""
        return self.end_lap - self.start_lap + 1

    def covers_lap(self, lap: int) -> bool:
        """Check if this period covers a specific lap."""
        return self.start_lap <= lap <= self.end_lap


@dataclass
class WeatherWindow:
    """A period of specific weather conditions.

    Attributes:
        start_lap: First lap with this weather.
        end_lap: Last lap with this weather (inclusive).
        rainfall: Amount of rainfall in mm.
        track_temp: Track temperature in Celsius.
        air_temp: Air temperature in Celsius.
    """
    start_lap: int
    end_lap: int
    rainfall: float = 0.0
    track_temp: Optional[float] = None
    air_temp: Optional[float] = None

    def __post_init__(self):
        """Validate weather window data."""
        if self.start_lap < 1:
            raise ValueError(f"start_lap must be >= 1, got {self.start_lap}")
        if self.end_lap < self.start_lap:
            raise ValueError(
                f"end_lap ({self.end_lap}) must be >= start_lap ({self.start_lap})"
            )
        if self.rainfall < 0:
            raise ValueError(f"rainfall must be non-negative, got {self.rainfall}")

    @property
    def is_wet(self) -> bool:
        """Check if this window has significant rain."""
        from src.config import RAIN_THRESHOLD_MM
        return self.rainfall >= RAIN_THRESHOLD_MM

    @property
    def duration_laps(self) -> int:
        """Return the number of laps this window covers."""
        return self.end_lap - self.start_lap + 1
