# Daily Gamma Capture Volatility Framework

## A Continuous, Path-Dependent Realized Volatility Architecture

The standard implementation of the [Gamma Capture model](https://www.researchgate.net/publication/404866134_Volatility_Measured_as_Barrier_Crossings_Limit_Orders_Gamma_Capture_and_the_Future_of_Intraday_Risk_Measurement)
focuses primarily on fixed intraday lookbacks (for example, hourly
rolling loops) using high-granularity data. This scheme adapts the
algorithm into a standalone daily metric designed to bridge the
overnight session gap, use standard 1-minute OHLC inputs, and produce
an undistorted, zero-lag daily annualized volatility estimate:

$$
\widehat{\sigma}_{\text{GC,daily}}
$$

## 1. Barrier-Crossing Recap

Before defining sequencing, we first define what a crossing means.
At any point in time, the active reset anchor is $P_0$. Around $P_0$,
the model defines symmetric barriers with half-width $w_t$:

$$
U_t = P_0 + w_t, \qquad L_t = P_0 - w_t
$$

An up-cross is registered when price reaches or exceeds $U_t$.
A down-cross is registered when price reaches or falls below $L_t$.
In one transition, price can traverse multiple barrier widths, so a
single minute may contribute one or more crossings.

The counting-cycle rule is:

- A counting cycle starts at $P_0$.
- The cycle ends at the first one-minute close that registers at least
  one crossing.
- The close of that terminating minute becomes the next cycle anchor.

## 2. Counting-Cycle Sequencing Across the Full Day

The day is processed in strict chronological order on a stitched path:

$$
\mathrm{Path}_t = \left[C_{t-1}^{\mathrm{daily}}, C_1^{\mathrm{min}}, C_2^{\mathrm{min}}, \ldots, C_n^{\mathrm{min}}\right]
$$

where $n$ is the number of observed minutes in the session
(full day: $n=390$; half day: $n<390$).

The first cycle anchor for day $t$ is:

$$
P_0^{(1)} = C_{t-1}^{\mathrm{daily}}
$$

No crossing is forced at the open.
If overnight and early-minute movement is small, multiple minutes can
pass with zero crossings while the same cycle remains active.
If a large move occurs (including overnight-to-open), one minute can
register multiple crossings, and that same minute close still closes
the active cycle and seeds the next cycle.

## 3. Exact Daily Counting Computation

Barrier scaling is set in relative form as:

$$
b_t = k \times \frac{\mathrm{TR}^{\mathrm{scale}}_t}{P_t}
$$

with typical $k \in [0.10, 0.25]$.
Here $\mathrm{TR}^{\mathrm{scale}}_t$ is a generic true-range scale
input (for example arithmetic ATR, EMA ATR, median TR, or another
true-range-based statistic over any lookback).
For an active cycle anchor $P_0$, convert to absolute barrier width:

$$
w_t = b_t \times P_0
$$

For each one-minute bar $j$, let $C_j$ be the minute close, $H_j$ the
minute high, and $L_j$ the minute low.

To reduce undercounting in volatile round-trip minutes, compute close,
range, anchor, and return components, then take the largest combined
candidate.

$$
\mathrm{count}^{\mathrm{close}}_j = \left\lfloor \frac{|C_j - P_0|}{w_t} \right\rfloor
$$

$$
\mathrm{count}^{\mathrm{range}}_j = \left\lfloor \frac{H_j - L_j}{w_t} \right\rfloor
$$

$$
\mathrm{count}^{\mathrm{anchor}}_j =
\left\lfloor \frac{\max(H_j - P_0, 0)}{w_t} \right\rfloor +
\left\lfloor \frac{\max(P_0 - L_j, 0)}{w_t} \right\rfloor
$$

$$
\mathrm{count}^{\mathrm{return}}_j =
\left\lfloor \frac{\min(H_j - C_j,\, C_j - L_j)}{w_t} \right\rfloor
$$

$$
m_j = \max\!\left(
\mathrm{count}^{\mathrm{close}}_j,
\mathrm{count}^{\mathrm{range}}_j,
\mathrm{count}^{\mathrm{anchor}}_j + \mathrm{count}^{\mathrm{return}}_j
\right)
$$

Optional upper-biased return variant:

$$
\mathrm{count}^{\mathrm{return}}_j =
\left\lfloor \frac{\max(H_j - C_j,\, C_j - L_j)}{w_t} \right\rfloor
$$

Use this variant only if you intentionally prefer a more aggressive
intrabar crossing estimate.

Interpretation:

- $\mathrm{count}^{\mathrm{close}}_j$ captures net movement from cycle
  start $P_0$ to the minute close.
- $\mathrm{count}^{\mathrm{range}}_j$ captures total intraminute span.
- $\mathrm{count}^{\mathrm{anchor}}_j$ captures two-sided excursions
  around $P_0$ in the same minute. The $\max(\cdot, 0)$ terms prevent
  negative floor contributions when $P_0$ is above $H_j$ or below $L_j$,
  which would otherwise undercount crossings.
- $\mathrm{count}^{\mathrm{return}}_j$ captures a conservative estimate
  of the return leg from an extreme back toward the minute close.

Cycle update rules:

- If $m_j = 0$, no crossing is registered and the current counting
  cycle continues.
- If $m_j \ge 1$, the current counting cycle terminates on minute $j$,
  and:

$$
N_{\mathrm{daily}} \leftarrow N_{\mathrm{daily}} + m_j,
\qquad
P_0^{(\mathrm{next})} = C_j
$$

Begin the next counting cycle at $P_0^{(\mathrm{next})}$.

## 4. Calibration and Annualization

The generalized annualized Gamma Capture formula is:

$$
\widehat{\sigma}_{\text{GC}} = b \times \sqrt{\frac{N}{T}} \times \sqrt{Y}
$$

For an $n$-minute session, define session length in trading-day units:

$$
T_{\mathrm{session}} = \frac{n}{390}
$$

with annualization day count
$Y = 252\text{ trading days}$. The generalized session formula is:

$$
\widehat{\sigma}_{\text{GC,session}} = b_t \times \sqrt{N_{\mathrm{daily}}} \times \sqrt{\frac{252}{T_{\mathrm{session}}}}
$$

For a full day ($n=390$), this collapses to:

$$
\widehat{\sigma}_{\text{GC,daily}} = b_t \times \sqrt{N_{\mathrm{daily}}} \times \sqrt{252}
$$

## 5. Architectural Comparison Matrix

| Structural Feature | Standard Daily Historical Volatility ($\sigma$ log returns) | Daily Gamma Capture Schema ($\sigma_{\text{GC,daily}}$) |
|---|---|---|
| Regime-switching latency | High lag. Requires a fixed window lookback (for example, 20 days) to calculate a standard deviation point. Slowly drags upward or downward following environment changes. | Zero lag. Outputs a standalone, highly responsive annualized figure for today alone based purely on today's internal path density. |
| Outlier and jump sensitivity | High distortion. Large isolated return shocks (for example, earnings gaps) enter the model squared, dominating variance and bloating readings artificially for weeks. | Low distortion. Large structural jumps register linearly as a finite, localized cascade of discrete crossings ($N$) without a dominant squared term. |
| Path awareness | Blind. Evaluates purely point-to-point terminal close differentials; completely unreflective of intra-bar or intraday traversal intensity. | High awareness. Incorporates the entire structural path from the prior close through the intraday OHLC reversals. |
