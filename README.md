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

Install:

```bash
pip install numpy
```

## Usage

```python
from gc_daily import compute_daily_gamma_capture

sigma = compute_daily_gamma_capture(
    close_prev=500.0,
    minute_closes=[500.1] * 390,
    minute_highs=[500.2] * 390,
    minute_lows=[499.9] * 390,
    tr_scale=5.0,
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

## Notes

- `tr_scale` is intentionally generic (for example arithmetic ATR, EMA ATR, median TR, or other true-range-based scale).
- Session annualization supports partial days via `n_minutes / minutes_per_day`.
- `docs/Daily Gamma Capture Volatility Framework.md` is the canonical spec.
