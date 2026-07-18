import numpy as np

def compute_daily_gamma_capture(
    close_prev,
    minute_closes,
    minute_highs,
    minute_lows,
    tr_scale,
    k=0.15,
    use_upper_biased_return=False,
    minutes_per_day=390,
    trading_days_per_year=252,
):
    """
    Compute standalone annualized Gamma Capture volatility for one day.

    This implementation follows the counting-cycle specification:
    1) Start each counting cycle from an active reset anchor P0.
    2) For each minute j, compute close/range/anchor/return crossing components.
    3) Let m_j be the maximum of those candidates.
    4) If m_j >= 1, terminate the current cycle on minute j and reset P0 to C_j.

    Parameters:
    -----------
    close_prev : float
        Prior day close, used as the first cycle anchor P0.
    minute_closes : list or np.array
        Current day 1-minute closes (expected length 390).
    minute_highs : list or np.array
        Current day 1-minute highs aligned with minute_closes.
    minute_lows : list or np.array
        Current day 1-minute lows aligned with minute_closes.
    tr_scale : float
        True-range scale input in price units. This is intentionally
        generic and can represent arithmetic ATR, EMA ATR, median TR,
        or any other true-range-based statistic over any lookback.
    k : float
        Tuning scalar for relative barrier sizing.
    use_upper_biased_return : bool
        If True, return-leg component uses max(H_j - C_j, C_j - L_j)
        instead of the conservative min(...).
    minutes_per_day : int
        Normalization constant for a full trading day (default 390).
    trading_days_per_year : int
        Annualization day count (default 252).

    Returns:
    --------
    float
        Annualized daily Gamma Capture volatility (decimal form).
    """
    minute_closes = np.asarray(minute_closes, dtype=float)
    minute_highs = np.asarray(minute_highs, dtype=float)
    minute_lows = np.asarray(minute_lows, dtype=float)

    n_minutes = minute_closes.size
    if n_minutes <= 0:
        raise ValueError("minute_closes must contain at least one data point.")
    if minute_highs.size != n_minutes or minute_lows.size != n_minutes:
        raise ValueError("minute_highs and minute_lows must have the same length as minute_closes.")
    if np.any(minute_highs < minute_lows):
        raise ValueError("Invalid bar data: each high must be >= corresponding low.")
    if np.any((minute_closes < minute_lows) | (minute_closes > minute_highs)):
        raise ValueError("Invalid bar data: each close must lie within [low, high].")
    if tr_scale <= 0 or k <= 0:
        raise ValueError("tr_scale and k must be positive.")
    if minutes_per_day <= 0 or trading_days_per_year <= 0:
        raise ValueError("minutes_per_day and trading_days_per_year must be positive.")

    p0 = float(close_prev)
    if p0 <= 0:
        raise ValueError("close_prev must be positive.")

    n_daily = 0
    b_day = k * (tr_scale / p0)

    # Process minute bars in chronological order as counting cycles.
    for c_j, h_j, l_j in zip(minute_closes, minute_highs, minute_lows):
        if p0 <= 0:
            raise ValueError("Encountered non-positive cycle anchor P0 during processing.")

        # Spec form: b_t = k * (TR_scale / P_t), w_t = b_t * P0.
        # Using P_t = P0 for the active cycle yields this absolute width.
        b_t = k * (tr_scale / p0)
        w_t = b_t * p0
        if w_t <= 0:
            raise ValueError("Computed non-positive barrier width w_t.")

        count_close = int(np.floor(np.abs(c_j - p0) / w_t))
        count_range = int(np.floor((h_j - l_j) / w_t))
        count_anchor = int(np.floor(max(h_j - p0, 0.0) / w_t)) + int(
            np.floor(max(p0 - l_j, 0.0) / w_t)
        )

        if use_upper_biased_return:
            count_return = int(np.floor(max(h_j - c_j, c_j - l_j) / w_t))
        else:
            count_return = int(np.floor(min(h_j - c_j, c_j - l_j) / w_t))

        m_j = max(count_close, count_range, count_anchor + count_return)

        if m_j >= 1:
            n_daily += m_j
            # Counting cycle handoff: terminating minute close seeds next cycle.
            p0 = float(c_j)

    # Annualize using session fraction T = n_minutes / minutes_per_day.
    if n_daily <= 0:
        return 0.0

    t_session = n_minutes / float(minutes_per_day)
    sigma_gc_daily = b_day * np.sqrt(n_daily) * np.sqrt(trading_days_per_year / t_session)
    return sigma_gc_daily

if __name__ == "__main__":
    print("gc_daily.py is a library module and does not run a default workflow by itself.")
    print("\nUse one of the following:")
    print("1) Run the real-data demo:")
    print("   python examples/spy_yahoo_1m_example.py")
    print("2) Import and call compute_daily_gamma_capture(...) from your own script/notebook.")