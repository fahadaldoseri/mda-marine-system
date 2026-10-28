# Unified Financial Metric Dictionary

When any domain module needs to compute or interpret metrics, read this file. Metric names, formulas, and default conventions are maintained only here; domain References may only reference them and must not copy or rewrite them.

## Table of contents

1. [General calculation conventions](#general-calculation-conventions)
2. [Returns and risk](#returns-and-risk)
3. [Portfolio and benchmark](#portfolio-and-benchmark)
4. [Financials and valuation](#financials-and-valuation)
5. [Funds and ETFs](#funds-and-etfs)
6. [Technical indicators and order flow](#technical-indicators-and-order-flow)
7. [Options](#options)
8. [Crypto and DeFi](#crypto-and-defi)
9. [Trading and backtesting](#trading-and-backtesting)
10. [Institutional investing](#institutional-investing)
11. [Custom and Adjusted Metrics](#custom-and-adjusted-metrics)
12. [General Valuation Discipline](#general-valuation-discipline)
13. [Non-computable and exception handling](#non-computable-and-exception-handling)

## General calculation conventions

### Data and return values

| Item | Unified convention |
|---|---|
| Price | Default to close price within the same market, currency, and timezone; execution-level analysis use executable bid/ask on the same venue |
| Total return | `TR_t = (P_t × AF_t + D_t) / (P_{t-1} × AF_{t-1}) - 1`; prefer vendor-provided fully adjusted total return series |
| Simple return | `r_t = V_t / V_{t-1} - 1` |
| Log return | `g_t = ln(V_t / V_{t-1})`; use only where models explicitly require it; do not mix with simple returns in reports |
| Annualization factor `A` | Equity/ETF daily default 252; crypto daily default 365; weekly 52; monthly 12; intraday computed and disclosed using actual trading days and the number of intraday intervals per day |
| Volatility | Use sample standard deviation with denominator `n-1` |
| Risk-free rate | Match return currency, term, and frequency; convert annual rate to per-period rate before computing excess returns |
| Percentages | Use decimals internally; multiply by 100 for display; do not mix `0.05` and `5` as the same input |
| Monetary amounts | Use a single currency and scale within the same table; when converting currencies record rate and timestamp |
| Time window | Each metric must record `start`, `end`, `frequency`, `n_obs`, and `annualization_factor` |

Unless explicitly stated, annualization uses simple frequency scaling; do not directly compare daily-frequency and monthly-frequency results. All metric outputs must include `value`, `unit`, `window`, `method`, `inputs`, and `status`.

## Returns and risk

| Metric | Formula | Must disclose | Edge-case handling |
|---|---:|---|---|
| Period total return | `R = V_end / V_start - 1` | Handling of dividends, fees, and cash flows | If `V_start <= 0` return `null` |
| CAGR | `(V_end / V_start)^(365 / calendar_days) - 1` | Start/end dates, cash flow adjustments | Compute for intervals under 365 days but flag `short_window`; non-positive start/end values return `null` |
| Annualized arithmetic return | `mean(r_t) × A` | Frequency and `A` | Do not call this CAGR |
| Annualized volatility | `stdev_sample(r_t) × sqrt(A)` | Price or total return series | If `n < 2` return `null` |
| Maximum drawdown | `min_t(V_t / running_max(V)_t - 1)` | Wealth index and window used | Return negative value; also report peak date, trough date, and recovery date |
| Downside deviation | `sqrt(mean(min(r_t - MAR_period, 0)^2)) × sqrt(A)` | MAR and frequency | If no downside observations return `0` and flag |
| Sharpe | `mean(r_t - rf_t) / stdev_sample(r_t - rf_t) × sqrt(A)` | Risk-free rate, window, frequency | If standard deviation is 0 return `null` |
| Sortino | `(mean(r_t) - MAR_period) / downside_deviation_period × sqrt(A)` | MAR and downside sample | If downside deviation is 0 return `null`; do not output infinity |
| Calmar | `CAGR / abs(MaxDrawdown)` | Use consistent windows for CAGR and drawdown | If maximum drawdown is 0 return `null` |
| VaR (historical) | `-quantile(P&L, 1-c)` | Confidence `c`, window, holding period, amount/percent | Describe only historical quantile; do not label as maximum loss |
| CVaR/ES (historical) | `-mean(P&L | P&L <= quantile(P&L, 1-c))` | Same as VaR | If tail sample is insufficient return `insufficient_data` |

## Portfolio and benchmark

| Metric | Formula | Must disclose | Edge-case handling |
|---|---:|---|---|
| Portfolio return | `r_p,t = Σ_i w_i,t-1 × r_i,t + cashflows_t` | Weight timestamps, cash and fees | If weights do not sum to 1 reconcile first |
| Beta | `Cov(r_p-rf, r_b-rf) / Var(r_b-rf)` | Benchmark, frequency, window | If benchmark variance is 0 return `null` |
| Alpha | Run OLS on synchronous excess returns: `y_t = alpha_period + beta x_t + e_t`; annualize `alpha = (1+alpha_period)^A-1` | Regression window, frequency, standard errors | Do not report significance when sample is insufficient |
| Tracking error | `stdev_sample(r_p,t - r_b,t) × sqrt(A)` | Benchmark and total return convention | If synchronous observations insufficient return `null` |
| Information ratio | `mean(active_return) / stdev_sample(active_return) × sqrt(A)` | Same as tracking error | If tracking error is 0 return `null` |
| Correlation | `Cov(r_i,r_j)/(σ_iσ_j)` | Synchronous window, frequency | If either standard deviation is 0 return `null` |
| HHI concentration | `Σ_i w_i^2` | Specify whether weights are look-through exposure | Use decimal weights; long-short portfolios report gross/net separately |
| Effective number of holdings | `1 / HHI` | Same convention as HHI | If HHI is 0 return `null` |
| Top-N concentration | `Σ` largest `N` absolute or net weights | Disclose `N` and weight convention | Long-short portfolios must report gross and net |
| Portfolio turnover (weight method) | `0.5 × Σ_i |w_i,target - w_i,pretrade|` | Rebalancing frequency | Treat cash as an asset |
| Risk contribution | `RC_i = w_i × (Σw)_i / σ_p`; share `RC_i / σ_p` | Covariance window | If `σ_p=0` return `null` |

## Financials and valuation

| Metric | Formula | Standard convention |
|---|---|---|
| Revenue growth | `Revenue_t / Revenue_t-1 - 1` | Compare the same accounting period; separately list M&A and FX effects |
| Gross margin | `Gross Profit / Revenue` | Not mandatory for financial companies |
| EBITDA | `EBIT + D&A` | If bridging from net income disclose interest, tax, depreciation & amortization, and one-time adjustments line by line |
| EBITDA Margin | `EBITDA / Revenue` | Separate adjusted and reported-series conventions |
| EBIT Margin | `EBIT / Revenue` | Use operating profit definition and disclose reclassifications |
| Net margin | `Net Income attributable to common / Revenue` | Numerator and denominator must be for the same period |
| CFO | Operating cash flow from the cash flow statement | Do not substitute EBITDA |
| FCF (levered) | `CFO - Capital Expenditures` | Capex equals the absolute value of cash outflows for acquisition/construction of long-term assets from the cash flow statement |
| FCFF | `EBIT×(1-T) + D&A - Capex - ΔNWC` | Tax rate and working capital definitions must be disclosed |
| FCF Margin | `FCF / Revenue` | Must indicate whether using FCF or FCFF |
| ROE | `Net Income attributable to common / Average Common Equity` | Average equity is the mean of beginning and ending balances |
| ROA | `Net Income / Average Total Assets` | Acceptable for financial companies |
| ROIC | `NOPAT / Average Invested Capital`; `NOPAT=EBIT×(1-T)`; `Invested Capital=Debt+Equity-Cash_nonoperating` | Disclose treatment of cash and goodwill |
| ROCE | `EBIT / Average Capital Employed`; default `Capital Employed=Total Assets-Current Liabilities` | If using Equity + Net Debt, document the name and definition |
| Net debt | `Interest-bearing Debt - Cash & Cash Equivalents` | Present restricted cash and lease liabilities separately |
| Net leverage | `Net Debt / LTM EBITDA` | If EBITDA ≤ 0 return `not_meaningful` |
| Interest coverage | `EBIT / Net Interest Expense` | If net interest is non-positive explain rather than returning infinity |
| P/E | `Price per Share / EPS` or `Market Cap / Net Income` | Annotate LTM/NTM and GAAP/adjusted; if EPS ≤ 0 return `not_meaningful` |
| EV | `Market Cap + Debt + Preferred + Minority Interest - Cash` | Disclose market cap on the valuation date and the most recent balance sheet date |
| EV/EBITDA | `EV / LTM or NTM EBITDA` | If EBITDA ≤ 0 return `not_meaningful` |
| P/B | `Market Cap / Common Equity` | If equity ≤ 0 return `not_meaningful` |
| FCF Yield | `LTM FCF / Market Cap` | Disclose FCF definition and market cap date |
| PEG | `P/E / expected EPS growth percentage` | Input growth as percentage points, e.g., 20% as `20`; if growth ≤ 0 return `not_meaningful` |
| WACC | `E/(D+E)×Re + D/(D+E)×Rd×(1-T)` | Use market-value weights; ensure currency and nominal/real conventions are consistent |
| DCF enterprise value | `Σ FCFF_t/(1+WACC)^t + TV/(1+WACC)^n` | Specify forecast horizon, semiannual conventions, terminal value method, and net debt bridge |
| Perpetuity terminal value | `TV = FCFF_(n+1)/(WACC-g)` | Must satisfy `WACC>g` |
| Exit multiple terminal value | `TV = Metric_n × Exit Multiple` | Ensure metric and comparable multiples are on the same convention |
| Per-share value | `(Enterprise Value - Net Debt - Preferred - Minority + nonoperating assets) / diluted shares` | Use fully diluted share count |

## Funds and ETFs

| Metric | Formula | Standard convention |
|---|---|---|
| Expense ratio | Annual operating expenses / Average net assets | Use issuer disclosure; trading costs reported separately |
| Tracking difference | `Fund Total Return - Index Total Return` | Same currency, same period, including dividends and fees |
| Tracking error | Annualized sample standard deviation of active returns | Use definition above; do not mix with tracking difference |
| Premium/discount | `Market Price / NAV - 1` | Timestamp and NAV type must be consistent |
| Bid-ask spread | `(Ask-Bid)/Mid`; `Mid=(Ask+Bid)/2` | Use executable quotes; if `Mid=0` return `null` |
| AUM change | `AUM_t/AUM_t-1-1` | Not equal to net fund flows; adjust for investment returns before estimating net flows |
| Concentration | HHI and Top-N | Calculate on look-through holdings; separately show derivative exposures |

## Technical indicators and order flow

| Metric | Formula | Default parameters and notes |
|---|---|---|
| SMA | Arithmetic mean of the most recent `n` prices | Default close price; disclose `n` |
| EMA | `EMA_t=αP_t+(1-α)EMA_t-1`, `α=2/(n+1)` | Initialize with prior `n`-period SMA |
| MACD | `EMA_12 - EMA_26`; Signal=`EMA_9(MACD)`; Histogram=`MACD-Signal` | Use close price |
| RSI | Wilder method: compute gains/losses, `RS=AvgGain_n/AvgLoss_n`, `RSI=100-100/(1+RS)` | Default `n=14`; if `AvgLoss=0` RSI = 100 |
| True Range | `max(H-L, |H-C_prev|, |L-C_prev|)` | For first period use `H-L` |
| ATR | Wilder-smoothed True Range | Default `n=14`; unit is price |
| Bollinger Bands | Middle `SMA_n`; bands `SMA_n ± k×stdev_population(P,n)` | Default `n=20, k=2`; `bollinger_period` (`n`) must be a positive integer and invalid values fail closed before window calculation; must state population vs sample standard deviation; this dictionary defaults to population |
| ADX | Derived from `+DM/-DM`, ATR, `+DI/-DI`, `DX=100×|+DI--DI|/(+DI+-DI)` with Wilder smoothing | Default `n=14` |
| KDJ | `RSV=100×(C-LL_n)/(HH_n-LL_n)`; `K=2/3K_prev+1/3RSV`; `D=2/3D_prev+1/3K`; `J=3K-2D` | Default `n=9`; if denominator is 0 carry forward prior value |
| VWAP | `Σ Price_i×Volume_i / Σ Volume_i` | Price defaults to trade price; candle approximations must be marked |
| CVD | `Σ(BuyInitiatedVolume-SellInitiatedVolume)` | Must have buy/sell initiation direction; do not fabricate from standard OHLCV |
| POC | Price bucket with highest volume in the selected interval | Disclose interval, bucket width, and data source |
| VAH/VAL | Upper/lower bounds of value area containing a specified proportion of volume | Default 70%; expand from POC to adjacent high-volume buckets; disclose algorithm |
| Support/Resistance | Non-unique mathematical indicators | Provide detection algorithm, window, minimum touch count, and tolerance; otherwise mark as analytical judgment |

## Options

All option monetary amounts are computed using contract multiplier `M`; US equity standard contracts are typically 100 but must be read from contract specs and not hard-coded.

| Metric | Formula | Standard convention |
|---|---|---|
| Call intrinsic value | `max(S-K,0)×M` | `S` is the underlying price at valuation |
| Put intrinsic value | `max(K-S,0)×M` | As above |
| Time value | `Option Price×M - Intrinsic Value` | Use mid or specified trade price |
| Long call payoff at expiry | `(max(S_T-K,0)-premium)×M-fees` | `premium` per share |
| Short put payoff at expiry | `(premium-max(K-S_T,0))×M-fees` | Assignment and margin handled separately |
| Spread strategy payoff | Sum of signed payoffs of each leg | Use same multiplier, currency, and expiry convention |
| Breakeven | Solve for roots where strategy expiry payoff equals 0 | Multi-leg strategies may have multiple roots |
| IV Rank | `(IV_now-IV_low)/(IV_high-IV_low)×100` | Default lookback 252 trading days; if denominator is 0 return `null` |
| IV Percentile | `count(IV_history < IV_now)/N×100` | Default lookback 252 trading days; specify whether current day is included |
| Delta | First derivative of option price with respect to underlying price | Unit is per share; portfolio Delta=`Σ delta_i×qty_i×M` |
| Gamma | First derivative of Delta with respect to underlying price | Disclose per 1 price unit change |
| Theta | First derivative of option price with respect to time | Present as per-day per-contract or per-share and indicate sign |
| Vega | First derivative of option price with respect to IV | Express per 1 percentage point increase in IV |
| Margin safety cushion | CSP default `(S-K)/S` | Describe only the strike relative-to-spot buffer; not equal to maximum risk |
| Capital return | `Net Premium / Capital at Risk` | Prefer non-annualized version |
| Annualized return on capital (ARoC) | `(Net Premium/Capital at Risk)×365/DTE` | Simple annualization, not compounded; `DTE>0`; do not confuse with realized returns |
| Spread rate | `(Ask-Bid)/Mid` | Check per leg and against portfolio net price |

If using Black-Scholes or other models to estimate Greeks/IV, record the model, rates, dividends, timing, and numerical method; for American options prefer models or vendor values that support early exercise.

## Crypto and DeFi

| Metric | Formula | Standard convention |
|---|---|---|
| Perpetual funding rate annualized | `funding_rate_per_interval × intervals_per_year` | Simple annualization; record exchange, interval, and direction sign |
| Basis for expiring futures | `(F-S)/S` | Ensure spot and futures are from the same venue/currency or explain differences |
| Annualized basis | `(F-S)/S × 365/DTE` | Simple annualization; `DTE>0` |
| OI change | `OI_t/OI_t-1-1` | Use consistent contract count or notional convention |
| Liquidation intensity | `Liquidation Notional / Market Volume` | Same venue and interval; disclose source methodology |
| 50/50 constant-product impermanent loss | `IL = 2×sqrt(r)/(1+r)-1`, `r=P_end/P_start` | For relatively static holds, fees excluded; do not use for concentrated liquidity |
| LP fee APR | `Fees_period/Average_Capital × 365/days` | Simple annualization; deduct gas, rebalancing, and incentive token depreciation separately |
| LP net return | `End Value + Fees + Rewards - Start Value - Costs` | Compare against same-currency HODL benchmark |
| Range coverage | `time(price within range)/total observed time` | Disclose frequency, price source, and observation window |

For concentrated liquidity pools use path-by-path simulation including ticks, out-of-range unilateral assets, fees, gas, and rebalancing; do not substitute with the 50/50 impermanent loss formula.

## Trading and backtesting

| Metric | Formula | Standard convention |
|---|---|---|
| Single-trade risk | `abs(entry-stop)×quantity×multiplier + estimated_costs` | For options/futures prefer scenario maximum loss |
| Notional value | `price×quantity×multiplier` | Report direction separately; do not use notional as a substitute for maximum loss |
| R multiple | `realized_P&L / planned_initial_risk` | Initial risk must be locked before the trade |
| Reward-to-risk | `planned_reward / planned_risk` | Compute using executable prices and fees |
| Win rate | `winning_trades / closed_trades` | Disclose rules for handling break-even trades |
| Average win/loss | Compute mean separately for positive and negative net P&L | Use results after fees |
| Payoff Ratio | `Average Win / abs(Average Loss)` | If either side has no samples return `null` |
| Profit Factor | `Gross Profit / abs(Gross Loss)` | If no losses return `null`; do not output infinity |
| Expectancy | `WinRate×AvgWin - LossRate×abs(AvgLoss)` | Use consistent per-trade or per-unit-risk basis |
| Trading turnover | `Σ abs(trade_notional) / Average NAV` | Disclose reporting period and whether double-counting; default is double-sided total traded volume |
| Market exposure | `time_with_open_position / total_time` | May alternatively report average gross exposure; label accordingly |
| Slippage | For buys `(fill-reference)/reference`, for sells `(reference-fill)/reference` | `reference` is mid or decision price at order time |
| Implementation Shortfall | Difference between actual portfolio outcome and the decision-time paper portfolio | Include delay, market impact, fees, and unfilled orders |

## Institutional investing

| Metric | Formula | Standard convention |
|---|---|---|
| MOIC | `Total Value / Invested Capital` | `Total Value = Distributions + Residual Value` |
| DPI | `Cumulative Distributions / Paid-in Capital` | Same valuation date and currency |
| RVPI | `Residual Value / Paid-in Capital` | Disclose residual value valuation method |
| TVPI | `(Distributions+Residual Value)/Paid-in Capital` | Equals DPI + RVPI |
| IRR | `r` such that `Σ CF_i/(1+r)^((date_i-date_0)/365)=0` | Use actual-date XIRR; report when multiple roots or no root |
| RAROC | `Annualized Risk-adjusted Net Income / Average Economic Capital` | Numerator must list income, expected loss, expenses, and tax; disclose ECAP source |
| Economic Capital | From an approved internal or regulatory risk model | Not a universal formula; record model, confidence level, horizon, and version |
| SPPI | Contract cash flows solely for principal and interest classification test | Non-numeric metric; output test steps, contentious clauses, and conclusion; do not substitute for accounting opinion |

## Custom and Adjusted Metrics

This section contains normative rules (Golden Rule) for custom-convention metrics and applies to all nine domain modules; see the checklist of specific data endpoint pitfalls at `corporate-finance/formats/metric_disambiguation.md`.

| Rule | Requirement |
|---|---|
| Adjusted-prefix identification | When a user or document requests a metric prefixed with `Adjusted`, `Covenant`, `Pro Forma`, `Run-rate`, or `Management`, do not use the standardized data API endpoint field with the same name |
| Reconstruction path | Return to original disclosures (SEC filing, Earnings Release, CIM), parse the corresponding reconciliation table, rebuild item by item, and disclose each add-back |
| Naming constraint | Reconstructed metrics must not share the name of a dictionary standard metric; use a new name with a convention suffix (e.g., `EBITDA_covenant_2024Q3`) and fully define it in the report |
| Lease consistency | When computing EV/EBITDA treat numerator and denominator consistently for operating leases: if EBITDA excludes rent expense then EV must include operating lease liabilities; if using EBITDAR then EV must exclude lease liabilities |
| Conflict resolution | If any appendix, Playbook, or domain document conflicts with this dictionary, this dictionary prevails and downstream documents must be corrected |

## General Valuation Discipline

This section defines cross-module public disciplines for valuation work and applies to equity-research valuation steps and corporate-finance valuation task groups; domain documents and Playbooks may only reference this section and must not copy or rewrite it.

| Discipline | Requirement |
|---|---|
| Primary method declaration | Specify a primary valuation method (e.g., DCF or Public Comps) and explain the rationale; use other methods for cross-validation |
| Cross-validation | Use at least one independent method to validate the primary result; if the difference exceeds ±20% explain the drivers; do not silently average |
| Three scenarios | Provide bear/base/bull scenarios; list key driver assumptions for each (growth, rates, terminal parameters, or exit multiples) item by item |
| Sensitivity | For the primary method provide a two-way sensitivity table for at least two key inputs (e.g., WACC × perpetual growth) |
| Parameter constraints | Perpetuity method must satisfy `WACC > g`; exit multiples must be consistent with comparable-company conventions (see Financials and valuation table above) |
| Conclusion presentation | Present a valuation range rather than a single point; state valuation date, share count convention, and net debt bridge date |
| Market-sensitive parameter timeliness | Market- or policy-sensitive parameters (risk-free rate, ERP, tax regime, credit spread, etc.) must be sourced from current authoritative sources; Playbook backup defaults marked `[market-sensitive]` may only be used if current data cannot be obtained, and must be recorded in `assumptions[]` with parameter name, value, and a "unable to verify current value" flag |

## Non-computable and exception handling

Do not fill missing values with `0` when any formula encounters the following conditions.

| Status | Use condition | Output requirement |
|---|---|---|
| `ok` | Inputs, units, window, and formula complete | Output numeric value and metadata |
| `insufficient_data` | Insufficient observations or missing key fields | List missing fields |
| `not_meaningful` | Mathematically computable but economically misleading (e.g., EV/EBITDA with negative EBITDA) | Do not output misleading multiples |
| `undefined` | Denominator zero, no solution, or multiple unresolved solutions | Explain the reason |
| `estimated` | Inputs derived from estimates or proxies | Provide estimation method and sensitivity |
| `stale` | Data older than task-allowed freshness | Do not use for execution-level conclusions |

Do not automatically trim, take absolute value, replace the denominator, or change the sign in exceptional cases. Any formula that differs from this dictionary must use a new metric name and be fully defined in the report.
