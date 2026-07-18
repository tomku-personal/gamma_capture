# gamma_capture

Daily volatility estimator using counting-cycle barrier logic on
standard 1-minute OHLC bars. The implementation is designed for
practical trading and research workflow: transparent formulas, reproducible
examples, and inputs available from common market-data vendors.

## Origin And Attribution

This repository is an independent implementation of volatility-estimation
ideas described by Louis Pellathy in the paper linked below.

- [Gamma Capture model](https://www.researchgate.net/publication/404866134_Volatility_Measured_as_Barrier_Crossings_Limit_Orders_Gamma_Capture_and_the_Future_of_Intraday_Risk_Measurement)

This repository is an unaffiliated implementation for research and
engineering purposes. It is not endorsed by, sponsored by, or otherwise
associated with the original author or any related commercial offering,
including https://gammacapture.com/.

## What This Repository Contains

- `gc_daily.py`: reference implementation of daily Gamma Capture computation.
- `docs/Daily Gamma Capture Volatility Framework.md`: official methodology and formulas.

## Core Idea

This repository estimates daily realized volatility by incorporating
barrier-crossing activity inferred from 1-minute OHLC bars during the
regular trading session. Instead of relying
only on daily close-to-close returns, it uses intraday bar information
to approximate how much price traversed within the session and converts
that estimated crossing activity into an annualized volatility measure.

The implementation is intended for practical use with widely available
market data while keeping the full methodology documented separately in
[docs/Daily Gamma Capture Volatility Framework.md](docs/Daily%20Gamma%20Capture%20Volatility%20Framework.md).

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

> Example output only. Values vary by date, data availability, and vendor responses.

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

session_dates = np.unique(df.index.date)
if len(session_dates) < 2:
    raise ValueError("Need at least two sessions of minute bars.")

# Prefer latest near-full session; fallback to latest available.
bars_by_session = pd.Series(df.index.date).value_counts()
candidate_dates = [d for d in session_dates if bars_by_session.get(d, 0) >= 350]
session_date = candidate_dates[-1] if candidate_dates else session_dates[-1]

# Select one session (example: most recent date).
session = df[df.index.date == session_date]

# Prior close from previous session.
prev_candidates = [d for d in session_dates if d < session_date]
if not prev_candidates:
    raise ValueError("No previous session found for close_prev.")
prev_session_date = prev_candidates[-1]
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

print(f"{sigma:.2%}")
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
