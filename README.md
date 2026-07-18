# gamma_capture

Daily Gamma Capture volatility prototype using counting-cycle barrier logic on 1-minute OHLC bars.

## What This Repository Contains

- `gc_daily.py`: reference implementation of daily/session Gamma Capture computation.
- `docs/Daily Gamma Capture Volatility Framework.md`: official methodology and formulas.

## Core Idea

For each session:

1. Start a counting cycle at `P0` (initially prior daily close).
2. For each minute bar, compute crossing candidates from:
   - close displacement
   - bar range
   - anchor excursions around `P0`
   - return leg (conservative or upper-biased option)
3. Let `m_j` be the selected crossing count for minute `j`.
4. If `m_j >= 1`, end the current cycle, add to `N_daily`, and reset `P0` to that minute close.
5. Annualize from session length.

## Requirements

- Python 3.10+
- numpy
- pandas
- yfinance

Install:

```bash
pip install numpy pandas yfinance
```

## Usage

### Quick Start

From the repository root:

```bash
python examples/spy_yahoo_1m_example.py
```

Typical output:

```text
Symbol: SPY
Target session: 2026-07-17  bars=390
Previous session close: 750.7600
TR scale (14-day SMA ATR proxy): 7.6921
Gamma Capture annualized sigma: 12.91%
Daily close-to-close historical sigma (21d, annualized): 12.48%
GC / daily close-to-close ratio: 1.034
```

### Real SPY 1-minute Example (Yahoo Finance)

What it does:

1. Downloads SPY 1-minute OHLC bars from Yahoo Finance for the recent period.
2. Selects a target session plus its previous session for `close_prev`.
3. Downloads daily SPY bars and computes a 14-day SMA ATR proxy for `tr_scale`.
4. Computes annualized Gamma Capture sigma from the selected session.

### Direct API Use (Real Data)

The function expects aligned minute arrays from one session:

- `minute_closes[i]`, `minute_highs[i]`, `minute_lows[i]` are from the same bar.
- `high >= low` for every bar.
- `close` must be within `[low, high]` for every bar.

Example using Yahoo minute bars for one session:

```python
import numpy as np
import pandas as pd
import yfinance as yf

from gc_daily import compute_daily_gamma_capture

# Download recent 1-minute bars.
df = yf.download("SPY", period="7d", interval="1m", progress=False, threads=False)
if isinstance(df.columns, pd.MultiIndex):
    # Handle possible MultiIndex columns from yfinance.
    df.columns = df.columns.get_level_values(0)

df = df[["High", "Low", "Close"]].dropna()

# Select one session (example: most recent date).
session_date = df.index.date[-1]
session = df[df.index.date == session_date]

# Prior close from previous session.
prev_session_date = np.unique(df.index.date)[-2]
prev_close = float(df[df.index.date == prev_session_date]["Close"].iloc[-1])

# TR scale is generic: use your preferred true-range statistic.
tr_scale = 7.5

sigma = compute_daily_gamma_capture(
    close_prev=prev_close,
    minute_closes=session["Close"].to_numpy(dtype=float),
    minute_highs=session["High"].to_numpy(dtype=float),
    minute_lows=session["Low"].to_numpy(dtype=float),
    tr_scale=tr_scale,
    k=0.15,
    use_upper_biased_return=False,
    minutes_per_day=390,
    trading_days_per_year=252,
)

print(sigma)
```

## Function Signature

```python
compute_daily_gamma_capture(
    close_prev,
    minute_closes,
    minute_highs,
    minute_lows,
    tr_scale,
    k=0.15,
    use_upper_biased_return=False,
    minutes_per_day=390,
    trading_days_per_year=252,
)
```

## Parameter Meaning

- `close_prev`: previous session close used as first counting-cycle anchor.
- `minute_closes`, `minute_highs`, `minute_lows`: aligned minute OHLC arrays for the target session.
- `tr_scale`: generic true-range scale (not fixed to 21-day ATR).
- `k`: barrier scaling coefficient.
- `use_upper_biased_return`: optional aggressive intrabar return-leg counting.
- `minutes_per_day`: full-session minute normalization constant (default 390).
- `trading_days_per_year`: annualization constant (default 252).

## Notes

- `tr_scale` is intentionally generic (for example arithmetic ATR, EMA ATR, median TR, or other true-range-based scale).
- Session annualization supports partial days via `n_minutes / minutes_per_day`.
- `docs/Daily Gamma Capture Volatility Framework.md` is the canonical spec.
- Yahoo 1-minute data coverage can be limited by vendor constraints and market calendar effects.
