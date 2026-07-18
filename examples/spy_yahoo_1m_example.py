import numpy as np
import pandas as pd
import yfinance as yf
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gc_daily import compute_daily_gamma_capture


def _compute_sma_atr(daily_df: pd.DataFrame, window: int = 14) -> float:
    high = daily_df["High"]
    low = daily_df["Low"]
    prev_close = daily_df["Close"].shift(1)

    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    atr = tr.rolling(window=window).mean().iloc[-1]
    if not np.isfinite(atr) or atr <= 0:
        raise ValueError("Unable to compute a valid ATR scale from daily data.")
    return float(atr)


def _compute_daily_close_to_close_volatility(
    daily_close: pd.Series,
    window: int = 21,
    trading_days_per_year: int = 252,
) -> float:
    # Standard historical volatility from daily close-to-close log returns.
    close = daily_close.astype(float).dropna()
    if close.size < window + 1:
        raise ValueError(
            f"Need at least {window + 1} daily closes to compute {window}-day historical volatility."
        )
    if np.any(close <= 0):
        raise ValueError("Daily close-to-close volatility requires strictly positive closes.")

    log_returns = np.log(close / close.shift(1)).dropna()
    sigma_daily = log_returns.rolling(window=window).std(ddof=1).iloc[-1]
    if not np.isfinite(sigma_daily):
        raise ValueError("Unable to compute a valid daily close-to-close volatility estimate.")
    return float(sigma_daily * np.sqrt(trading_days_per_year))


def _standardize_ohlc_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        # Keep first level labels such as Open/High/Low/Close.
        df = df.copy()
        df.columns = df.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required OHLC columns: {missing}")
    return df[required]


def _pick_target_session(minute_df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    session_dates = pd.Index(minute_df.index.date).unique()
    if len(session_dates) < 2:
        raise ValueError("Need at least two sessions of minute bars to compute close_prev.")

    bars_by_session = minute_df.groupby(minute_df.index.date).size()

    # Prefer latest session with near-full regular-hours coverage.
    for d in reversed(session_dates):
        if bars_by_session.loc[d] >= 350:
            prev_candidates = [x for x in session_dates if x < d]
            if prev_candidates:
                return pd.Timestamp(d), pd.Timestamp(prev_candidates[-1])

    # Fallback: use the most recent session and its predecessor.
    return pd.Timestamp(session_dates[-1]), pd.Timestamp(session_dates[-2])


def main() -> None:
    symbol = "SPY"

    minute_df = yf.download(
        tickers=symbol,
        period="7d",
        interval="1m",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if minute_df.empty:
        raise ValueError("No minute data returned from Yahoo Finance.")

    minute_df = _standardize_ohlc_columns(minute_df).dropna()

    target_date, prev_date = _pick_target_session(minute_df)

    target_mask = pd.Index(minute_df.index.date) == target_date.date()
    prev_mask = pd.Index(minute_df.index.date) == prev_date.date()

    target = minute_df.loc[target_mask]
    prev = minute_df.loc[prev_mask]

    if target.empty or prev.empty:
        raise ValueError("Unable to isolate target/previous sessions from minute data.")

    close_prev = float(prev["Close"].iloc[-1])
    minute_closes = target["Close"].to_numpy(dtype=float)
    minute_highs = target["High"].to_numpy(dtype=float)
    minute_lows = target["Low"].to_numpy(dtype=float)

    daily_df = yf.download(
        tickers=symbol,
        period="6mo",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if daily_df.empty:
        raise ValueError("No daily data returned from Yahoo Finance.")

    daily_df = _standardize_ohlc_columns(daily_df)[["High", "Low", "Close"]].dropna()
    tr_scale = _compute_sma_atr(daily_df, window=14)

    sigma = compute_daily_gamma_capture(
        close_prev=close_prev,
        minute_closes=minute_closes,
        minute_highs=minute_highs,
        minute_lows=minute_lows,
        tr_scale=tr_scale,
        k=0.15,
        use_upper_biased_return=False,
        minutes_per_day=390,
        trading_days_per_year=252,
    )

    sigma_cc_daily = _compute_daily_close_to_close_volatility(
        daily_close=daily_df["Close"],
        window=21,
        trading_days_per_year=252,
    )

    print(f"Symbol: {symbol}")
    print(f"Target session: {target_date.date()}  bars={len(target)}")
    print(f"Previous session close: {close_prev:.4f}")
    print(f"TR scale (14-day SMA ATR proxy): {tr_scale:.4f}")
    print(f"Gamma Capture annualized sigma: {sigma:.2%}")
    print(f"Daily close-to-close historical sigma (21d, annualized): {sigma_cc_daily:.2%}")
    if sigma_cc_daily > 0:
        print(f"GC / daily close-to-close ratio: {sigma / sigma_cc_daily:.3f}")


if __name__ == "__main__":
    main()
