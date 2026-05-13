"""Design tokens, tire data, and simulation tuning constants."""
import os

APP_NAME = "Explain That Strategy"
CACHE_DIR = os.path.expanduser("~/.cache/fastf1")

# Design tokens (mirrors the CSS :root so plotly charts can use the same palette).
TOKENS = {
    "paper":        "#FBF9F4",
    "paper_sh":     "#EDEAE2",
    "ink":          "#1A1A1C",
    "ink_2":        "#3A3A3C",
    "ink_3":        "#7A7568",
    "ink_4":        "#A8A498",
    "rule":         "#E6E3DB",
    "rule_soft":    "#EFEDE7",
    "accent":       "#C5242A",
    "alert":        "#8F2F35",
    "warn":         "#B88A28",
    "info":         "#5A7FA8",
    "font":         "Geist Mono, ui-monospace, SF Mono, Menlo, monospace",
    "font_display": "Titillium Web, sans-serif",
}

# Tire compounds — 2026 Pirelli P Zero official sidewall colors.
TIRE_DATA = {
    "SOFT":         {"base_delta": 0.0, "deg_per_lap": 0.08, "color": "#E30613"},  # Red
    "MEDIUM":       {"base_delta": 0.6, "deg_per_lap": 0.05, "color": "#C89800"},  # Darker gold for chart visibility
    "HARD":         {"base_delta": 1.1, "deg_per_lap": 0.03, "color": "#4A4A4A"},  # Dark gray for chart visibility
    "INTERMEDIATE": {"base_delta": 0.3, "deg_per_lap": 0.04, "color": "#00A54F"},  # Green
    "WET":          {"base_delta": 1.5, "deg_per_lap": 0.03, "color": "#0049B0"},  # Blue
}

# Pit stop time losses (seconds).
PIT_STOP_LOSS_NORMAL = 22.0
PIT_STOP_LOSS_SC = 10.0
PIT_STOP_LOSS_VSC = 12.0

# SC/VSC slowdown multipliers applied per lap.
SC_LAP_TIME_FACTOR = 1.40
VSC_LAP_TIME_FACTOR = 1.20

# Weather tuning.
REF_TRACK_TEMP = 30.0          # reference track temperature (°C)
TRACK_TEMP_DEG_COEFF = 0.015   # extra deg/lap per °C above reference

# Per-compound wet penalty (seconds added on wet laps).
WET_PENALTY = {
    "SOFT": 12.0,
    "MEDIUM": 11.0,
    "HARD": 10.0,
    "INTERMEDIATE": 0.0,
    "WET": -1.0,
}

# Per-compound dry penalty (rain tires on a dry track).
DRY_PENALTY = {
    "SOFT": 0.0,
    "MEDIUM": 0.0,
    "HARD": 0.0,
    "INTERMEDIATE": 4.0,
    "WET": 8.0,
}

# =============================================================================
# SIMULATION CONSTANTS
# =============================================================================

# Fuel effect: lap time improves by this many seconds per lap as fuel burns off
FUEL_EFFECT_PER_LAP = -0.03  # seconds per lap

# Quantile for computing base pace from clean laps (0.25 = 25th percentile = fast laps)
BASE_TIME_QUANTILE = 0.25

# Default pit lap divisors for strategy generation
PIT_LAP_DIVISOR_1STOP = 2           # Single stop at 50%
PIT_LAP_DIVISOR_2STOP_1 = 3         # First stop at 33%
PIT_LAP_DIVISOR_2STOP_2 = 2         # Second stop at ~66% (2 * total / 3)
PIT_LAP_DIVISOR_3STOP_1 = 4         # First stop at 25%
PIT_LAP_DIVISOR_3STOP_2 = 2         # Second stop at 50%
PIT_LAP_DIVISOR_3STOP_3 = 4         # Third stop at 75% (3 * total / 4)

# Minimum degradation rate to prevent unrealistic negative values
MIN_DEGRADATION_RATE = 0.005  # seconds per lap

# Rain threshold for wet weather detection (mm)
RAIN_THRESHOLD_MM = 0.5

# Valid tire compounds for validation
VALID_COMPOUNDS = frozenset(TIRE_DATA.keys())

# Simulation thresholds for verdict classification
VERDICT_FASTER_THRESHOLD = -1.0     # seconds faster to be considered "faster"
VERDICT_SIGNIFICANT_THRESHOLD = -2.0  # seconds faster to be considered "significant"
VERDICT_NEUTRAL_RANGE = 1.0         # +/- this range is "neutral"
