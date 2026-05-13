"""Lap-time simulation + alternative-strategy generation."""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.config import (
    DRY_PENALTY,
    FUEL_EFFECT_PER_LAP,
    MIN_DEGRADATION_RATE,
    PIT_LAP_DIVISOR_1STOP,
    PIT_LAP_DIVISOR_2STOP_1,
    PIT_LAP_DIVISOR_2STOP_2,
    PIT_LAP_DIVISOR_3STOP_1,
    PIT_LAP_DIVISOR_3STOP_2,
    PIT_LAP_DIVISOR_3STOP_3,
    PIT_STOP_LOSS_NORMAL,
    PIT_STOP_LOSS_SC,
    PIT_STOP_LOSS_VSC,
    RAIN_THRESHOLD_MM,
    REF_TRACK_TEMP,
    SC_LAP_TIME_FACTOR,
    TIRE_DATA,
    TRACK_TEMP_DEG_COEFF,
    VALID_COMPOUNDS,
    VSC_LAP_TIME_FACTOR,
    WET_PENALTY,
)
from src.models import LapTime, PitStop, SCPeriod, SimulationResult, Stint, Strategy, WeatherWindow

logger = logging.getLogger(__name__)


def _validate_compound(compound: str) -> None:
    """Validate that a compound is supported.

    Args:
        compound: Tire compound name to validate.

    Raises:
        ValueError: If compound is not in VALID_COMPOUNDS.
    """
    if compound not in VALID_COMPOUNDS:
        raise ValueError(
            f"Unknown compound: {compound}. Valid compounds: {sorted(VALID_COMPOUNDS)}"
        )


def estimate_lap_time(
    base_time: float,
    compound: str,
    tire_age: int,
    fuel_effect: float = 0,
    sc_type: Optional[str] = None,
    weather: Optional[Dict[str, Any]] = None,
) -> float:
    """Estimate a single lap time given compound, tire age, SC, and weather.

    Args:
        base_time: Base lap time in seconds (clean, reference pace).
        compound: Tire compound (must be in VALID_COMPOUNDS).
        tire_age: Number of laps on current tires (>= 0).
        fuel_effect: Fuel effect adjustment in seconds (typically negative as fuel burns).
        sc_type: Optional safety car type ('SC', 'VSC', or None).
        weather: Optional weather dict with 'track_temp' and 'rainfall' keys.

    Returns:
        Estimated lap time in seconds.

    Raises:
        ValueError: If compound is invalid or tire_age is negative.
    """
    # Input validation
    _validate_compound(compound)
    if tire_age < 0:
        raise ValueError(f"tire_age must be non-negative, got {tire_age}")
    if sc_type not in (None, "SC", "VSC"):
        raise ValueError(f"sc_type must be 'SC', 'VSC', or None, got {sc_type}")

    td = TIRE_DATA.get(compound, TIRE_DATA["MEDIUM"])

    # Track-temp-dependent degradation.
    deg_rate = td["deg_per_lap"]
    if weather and weather.get("track_temp") is not None:
        delta_t = weather["track_temp"] - REF_TRACK_TEMP
        deg_rate = max(MIN_DEGRADATION_RATE, deg_rate + TRACK_TEMP_DEG_COEFF * delta_t)

    lap_time = base_time + td["base_delta"] + deg_rate * tire_age + fuel_effect

    # Wet vs dry compound mismatch.
    if weather is not None:
        if weather.get("rainfall"):
            lap_time += WET_PENALTY.get(compound, 10.0)
        else:
            lap_time += DRY_PENALTY.get(compound, 0.0)

    if sc_type == "SC":
        lap_time *= SC_LAP_TIME_FACTOR
    elif sc_type == "VSC":
        lap_time *= VSC_LAP_TIME_FACTOR

    return lap_time


def simulate_strategy(
    total_laps: int,
    base_time: float,
    pit_stops: List[Dict[str, Any]],
    sc_laps: Optional[Dict[int, str]] = None,
    lap_weather: Optional[Dict[int, Dict[str, Any]]] = None,
) -> Tuple[float, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Simulate a race given a pit-stop schedule.

    Args:
        total_laps: Total number of laps in the race (> 0).
        base_time: Base lap time in seconds.
        pit_stops: List of stop dictionaries with 'lap', 'compound', 'next_compound'.
        sc_laps: Optional dict mapping lap number to 'SC' or 'VSC'.
        lap_weather: Optional dict mapping lap number to weather dict.

    Returns:
        Tuple of (total_time, lap_times, stints).
        - total_time: Total race time in seconds.
        - lap_times: List of lap time dictionaries.
        - stints: List of stint dictionaries with 'start', 'end', 'compound'.

    Raises:
        ValueError: If inputs are invalid (negative values, unknown compounds, etc.).
    """
    # Input validation
    if total_laps <= 0:
        raise ValueError(f"total_laps must be positive, got {total_laps}")
    if base_time <= 0:
        raise ValueError(f"base_time must be positive, got {base_time}")

    sc_laps = sc_laps or {}
    lap_weather = lap_weather or {}

    stops = sorted(pit_stops, key=lambda x: x["lap"])

    # Validate all compounds in pit stops
    for stop in stops:
        _validate_compound(stop["compound"])
        if stop.get("next_compound"):
            _validate_compound(stop["next_compound"])

    stints: List[Dict[str, Any]] = []
    first_compound = stops[0]["compound"] if stops else "MEDIUM"
    prev_lap = 1
    for stop in stops:
        stints.append({"start": prev_lap, "end": stop["lap"], "compound": first_compound})
        first_compound = stop.get("next_compound", "HARD")
        prev_lap = stop["lap"] + 1
    stints.append({"start": prev_lap, "end": total_laps, "compound": first_compound})

    lap_times: List[Dict[str, Any]] = []
    total_time = 0.0
    for stint in stints:
        tire_age = 0
        for lap in range(stint["start"], stint["end"] + 1):
            fuel_effect = FUEL_EFFECT_PER_LAP * (lap - 1)
            sc_type = sc_laps.get(lap, None)
            weather = lap_weather.get(lap)
            lt = estimate_lap_time(
                base_time, stint["compound"], tire_age, fuel_effect, sc_type, weather
            )
            lap_times.append({
                "lap": lap,
                "time": lt,
                "compound": stint["compound"],
                "tire_age": tire_age,
                "sc_type": sc_type,
                "rainfall": bool(weather and weather.get("rainfall")),
            })
            total_time += lt
            tire_age += 1

    # Pit stop time losses — cheaper under SC/VSC.
    for stop in stops:
        sc_at_pit = sc_laps.get(stop["lap"], None)
        if sc_at_pit == "SC":
            total_time += PIT_STOP_LOSS_SC
        elif sc_at_pit == "VSC":
            total_time += PIT_STOP_LOSS_VSC
        else:
            total_time += PIT_STOP_LOSS_NORMAL

    return total_time, lap_times, stints


def _detect_rain_windows(
    lap_weather: Dict[int, Dict[str, Any]], total_laps: int
) -> List[WeatherWindow]:
    """Detect continuous rain windows from lap weather data.

    Args:
        lap_weather: Dict mapping lap number to weather data.
        total_laps: Total number of laps in the race.

    Returns:
        List of WeatherWindow objects representing continuous rain periods.
    """
    rain_laps = sorted([
        lap for lap, w in lap_weather.items()
        if w.get("rainfall", 0) >= RAIN_THRESHOLD_MM
    ])

    if not rain_laps:
        return []

    windows: List[WeatherWindow] = []
    current_start = rain_laps[0]
    current_end = rain_laps[0]

    for lap in rain_laps[1:]:
        if lap == current_end + 1:
            current_end = lap
        else:
            weather = lap_weather.get(current_start, {})
            windows.append(WeatherWindow(
                start_lap=current_start,
                end_lap=current_end,
                rainfall=weather.get("rainfall", RAIN_THRESHOLD_MM),
                track_temp=weather.get("track_temp"),
                air_temp=weather.get("air_temp"),
            ))
            current_start = lap
            current_end = lap

    # Add the last window
    weather = lap_weather.get(current_start, {})
    windows.append(WeatherWindow(
        start_lap=current_start,
        end_lap=current_end,
        rainfall=weather.get("rainfall", RAIN_THRESHOLD_MM),
        track_temp=weather.get("track_temp"),
        air_temp=weather.get("air_temp"),
    ))

    logger.debug(f"Detected {len(windows)} rain windows: {windows}")
    return windows


def _generate_1stop_strategies(total_laps: int) -> List[Strategy]:
    """Generate all valid 1-stop strategy combinations.

    Args:
        total_laps: Total number of laps in the race.

    Returns:
        List of 1-stop Strategy objects.
    """
    strategies: List[Strategy] = []
    compounds = ["SOFT", "MEDIUM", "HARD"]
    pit_lap = total_laps // PIT_LAP_DIVISOR_1STOP

    for c1 in compounds:
        for c2 in compounds:
            if c1 == c2:
                continue
            strategies.append(Strategy(
                name=f"1-stop: {c1[:1]}-{c2[:1]} (lap {pit_lap})",
                stops=[PitStop(lap=pit_lap, from_compound=c1, to_compound=c2)],
                first_compound=c1,
            ))

    logger.debug(f"Generated {len(strategies)} 1-stop strategies")
    return strategies


def _generate_2stop_strategies(total_laps: int) -> List[Strategy]:
    """Generate all valid 2-stop strategy combinations.

    Args:
        total_laps: Total number of laps in the race.

    Returns:
        List of 2-stop Strategy objects.
    """
    strategies: List[Strategy] = []
    compounds = ["SOFT", "MEDIUM", "HARD"]
    p1 = total_laps // PIT_LAP_DIVISOR_2STOP_1
    p2 = PIT_LAP_DIVISOR_2STOP_2 * total_laps // PIT_LAP_DIVISOR_2STOP_1

    for c1 in compounds:
        for c2 in compounds:
            for c3 in compounds:
                if c1 == c2 == c3:
                    continue
                strategies.append(Strategy(
                    name=f"2-stop: {c1[:1]}-{c2[:1]}-{c3[:1]} (laps {p1},{p2})",
                    stops=[
                        PitStop(lap=p1, from_compound=c1, to_compound=c2),
                        PitStop(lap=p2, from_compound=c2, to_compound=c3),
                    ],
                    first_compound=c1,
                ))

    logger.debug(f"Generated {len(strategies)} 2-stop strategies")
    return strategies


def _generate_3stop_strategies(total_laps: int) -> List[Strategy]:
    """Generate common 3-stop strategy combinations.

    Args:
        total_laps: Total number of laps in the race.

    Returns:
        List of 3-stop Strategy objects.
    """
    strategies: List[Strategy] = []
    three_stop_combos = [
        ("SOFT", "MEDIUM", "MEDIUM", "HARD"),
        ("SOFT", "MEDIUM", "HARD", "MEDIUM"),
        ("SOFT", "SOFT", "MEDIUM", "HARD"),
        ("MEDIUM", "HARD", "MEDIUM", "SOFT"),
        ("SOFT", "MEDIUM", "SOFT", "MEDIUM"),
        ("SOFT", "HARD", "MEDIUM", "SOFT"),
        ("MEDIUM", "SOFT", "MEDIUM", "SOFT"),
    ]
    p1 = total_laps // PIT_LAP_DIVISOR_3STOP_1
    p2 = total_laps // PIT_LAP_DIVISOR_3STOP_2
    p3 = 3 * total_laps // PIT_LAP_DIVISOR_3STOP_3

    for c1, c2, c3, c4 in three_stop_combos:
        strategies.append(Strategy(
            name=f"3-stop: {c1[:1]}-{c2[:1]}-{c3[:1]}-{c4[:1]} (laps {p1},{p2},{p3})",
            stops=[
                PitStop(lap=p1, from_compound=c1, to_compound=c2),
                PitStop(lap=p2, from_compound=c2, to_compound=c3),
                PitStop(lap=p3, from_compound=c3, to_compound=c4),
            ],
            first_compound=c1,
        ))

    logger.debug(f"Generated {len(strategies)} 3-stop strategies")
    return strategies


def _generate_weather_strategies(
    total_laps: int, rain_windows: List[WeatherWindow]
) -> List[Strategy]:
    """Generate weather-aware strategies for rain windows.

    Args:
        total_laps: Total number of laps in the race.
        rain_windows: List of detected rain windows.

    Returns:
        List of weather-aware Strategy objects.
    """
    strategies: List[Strategy] = []

    for window in rain_windows:
        rstart = window.start_lap
        rend = window.end_lap

        # Dry → Intermediate crossover
        if rstart > 1:
            for dry_c in ("MEDIUM", "SOFT"):
                strategies.append(Strategy(
                    name=f"Dry→INT crossover: {dry_c[:1]}-I (lap {rstart})",
                    stops=[PitStop(
                        lap=max(1, rstart - 1),
                        from_compound=dry_c,
                        to_compound="INTERMEDIATE"
                    )],
                    first_compound=dry_c,
                    weather_aware=True,
                ))

        # Intermediate → Dry crossover
        if rend < total_laps:
            for dry_c in ("MEDIUM", "HARD"):
                strategies.append(Strategy(
                    name=f"INT→Dry crossover: I-{dry_c[:1]} (lap {rend + 1})",
                    stops=[PitStop(
                        lap=rend,
                        from_compound="INTERMEDIATE",
                        to_compound=dry_c
                    )],
                    first_compound="INTERMEDIATE",
                    weather_aware=True,
                ))

        # Dry → Intermediate → Dry double crossover
        if rstart > 1 and rend < total_laps:
            for dry_start in ("MEDIUM", "SOFT"):
                for dry_end in ("MEDIUM", "HARD"):
                    strategies.append(Strategy(
                        name=f"Dry→INT→Dry: {dry_start[:1]}-I-{dry_end[:1]} (laps {rstart - 1},{rend})",
                        stops=[
                            PitStop(
                                lap=max(1, rstart - 1),
                                from_compound=dry_start,
                                to_compound="INTERMEDIATE"
                            ),
                            PitStop(
                                lap=rend,
                                from_compound="INTERMEDIATE",
                                to_compound=dry_end
                            ),
                        ],
                        first_compound=dry_start,
                        weather_aware=True,
                    ))

        # Full WET window for long rain periods
        if window.duration_laps >= 5:
            strategies.append(Strategy(
                name=f"Full WET window: M-W-M (laps {max(1, rstart - 1)},{rend})",
                stops=[
                    PitStop(
                        lap=max(1, rstart - 1),
                        from_compound="MEDIUM",
                        to_compound="WET"
                    ),
                    PitStop(
                        lap=rend,
                        from_compound="WET",
                        to_compound="MEDIUM"
                    ),
                ],
                first_compound="MEDIUM",
                weather_aware=True,
            ))

    logger.debug(f"Generated {len(strategies)} weather-aware strategies")
    return strategies


def _generate_sc_strategies(
    total_laps: int, sc_periods: List[SCPeriod]
) -> List[Strategy]:
    """Generate SC-opportunistic strategies.

    Args:
        total_laps: Total number of laps in the race.
        sc_periods: List of SC/VSC periods.

    Returns:
        List of SC-opportunistic Strategy objects.
    """
    strategies: List[Strategy] = []
    compounds = ["SOFT", "MEDIUM", "HARD"]

    for period in sc_periods:
        sc_lap = (period.start_lap + period.end_lap) // 2
        sc_type_label = period.type

        for c1 in compounds:
            for c2 in compounds:
                if c1 == c2:
                    continue

                # 1-stop under SC/VSC
                strategies.append(Strategy(
                    name=f"1-stop under {sc_type_label}: {c1[:1]}-{c2[:1]} (lap {sc_lap})",
                    stops=[PitStop(
                        lap=sc_lap,
                        from_compound=c1,
                        to_compound=c2,
                        under_sc=period.type
                    )],
                    first_compound=c1,
                    sc_opportunistic=True,
                ))

                # 2-stop with one under SC/VSC
                normal_lap = total_laps // 2 if sc_lap < total_laps // 3 else total_laps // 4
                if abs(normal_lap - sc_lap) > 5:
                    for c3 in compounds:
                        lap1, lap2 = min(sc_lap, normal_lap), max(sc_lap, normal_lap)
                        strategies.append(Strategy(
                            name=f"2-stop ({sc_type_label} lap {sc_lap}): {c1[:1]}-{c2[:1]}-{c3[:1]}",
                            stops=[
                                PitStop(
                                    lap=lap1,
                                    from_compound=c1,
                                    to_compound=c2,
                                    under_sc=period.type if lap1 == sc_lap else None
                                ),
                                PitStop(
                                    lap=lap2,
                                    from_compound=c2,
                                    to_compound=c3,
                                    under_sc=period.type if lap2 == sc_lap else None
                                ),
                            ],
                            first_compound=c1,
                            sc_opportunistic=True,
                        ))

    logger.debug(f"Generated {len(strategies)} SC-opportunistic strategies")
    return strategies


def generate_alt_strategies(
    total_laps: int,
    actual_stints: List[Dict[str, Any]],
    sc_periods_mapped: List[Dict[str, Any]],
    lap_weather: Optional[Dict[int, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Enumerate plausible alternative strategies, including SC/weather-opportunistic ones.

    Args:
        total_laps: Total number of laps in the race.
        actual_stints: List of actual stint dictionaries (for reference).
        sc_periods_mapped: List of SC/VSC period dictionaries with 'start_lap', 'end_lap', 'type'.
        lap_weather: Optional dict mapping lap number to weather data.

    Returns:
        List of strategy dictionaries compatible with existing code.

    Raises:
        ValueError: If total_laps is not positive.
    """
    if total_laps <= 0:
        raise ValueError(f"total_laps must be positive, got {total_laps}")

    lap_weather = lap_weather or {}

    # Convert SC periods to model objects
    sc_periods = [
        SCPeriod(type=p["type"], start_lap=p["start_lap"], end_lap=p["end_lap"])
        for p in sc_periods_mapped
    ]

    # Detect rain windows
    rain_windows = _detect_rain_windows(lap_weather, total_laps)

    # Generate strategies by type
    all_strategies: List[Strategy] = []
    all_strategies.extend(_generate_1stop_strategies(total_laps))
    all_strategies.extend(_generate_2stop_strategies(total_laps))
    all_strategies.extend(_generate_3stop_strategies(total_laps))

    if rain_windows:
        all_strategies.extend(_generate_weather_strategies(total_laps, rain_windows))

    if sc_periods:
        all_strategies.extend(_generate_sc_strategies(total_laps, sc_periods))

    logger.info(
        f"Generated {len(all_strategies)} total alternative strategies "
        f"({len(rain_windows)} rain windows, {len(sc_periods)} SC periods)"
    )

    # Convert back to dict format for backward compatibility
    return [
        {
            "name": s.name,
            "stops": [
                {"lap": stop.lap, "compound": s.first_compound, "next_compound": stop.to_compound}
                for stop in s.stops
            ],
            "first_compound": s.first_compound,
            "sc_opportunistic": s.sc_opportunistic,
            "weather_aware": s.weather_aware,
        }
        for s in all_strategies
    ]
