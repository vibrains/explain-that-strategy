# 🏎️ Explain That Strategy

Was that F1 pit stop the right call? This app lets you pick any recent race and driver, see their actual tire strategy, and simulate alternate strategies to see if the team left time on the table.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## How It Works

1. Pick a season, Grand Prix, and driver
2. See their actual tire strategy and lap times
3. The app simulates all reasonable 1-stop and 2-stop alternatives
4. Compare any alternative head-to-head with what actually happened
5. Get a verdict: did the team nail it, or leave time on the table?

## Tire Model

Uses a simplified degradation model:

- **Soft**:
  est but degrades at ~0.08s/lap
- **Medium**: +0.6s base, degrades at ~0.05s/lap
- **Hard**: +1.1s base, degrades at ~0.03s/lap

Pit stop time loss is estimated from the actual race data.

## Data

Powered by [FastF1](https://github.com/theOehrly/Fast-F1) — all data comes from the official F1 timing system.
