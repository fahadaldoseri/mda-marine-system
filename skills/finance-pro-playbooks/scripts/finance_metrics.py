#!/usr/bin/env python3
"""Deterministic finance calculations for the finance-analysis Skill.

Input is one JSON object with an ``operation`` field. Output is JSON and never
silently substitutes missing or invalid inputs.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable


class MetricError(ValueError):
    """Raised when a metric cannot be computed from the supplied contract."""


def _numbers(values: Iterable[Any], name: str, minimum: int = 1) -> list[float]:
    result: list[float] = []
    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MetricError(f"{name}[{index}] must be numeric")
        number = float(value)
        if not math.isfinite(number):
            raise MetricError(f"{name}[{index}] must be finite")
        result.append(number)
    if len(result) < minimum:
        raise MetricError(f"{name} requires at least {minimum} observations")
    return result


def _positive(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MetricError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise MetricError(f"{name} must be finite and > 0")
    return number


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise MetricError(f"{name} must be a positive integer")
    if isinstance(value, int):
        number = value
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise MetricError(f"{name} must be a positive integer")
        number = int(value)
    elif isinstance(value, str):
        try:
            number = int(value.strip())
        except ValueError as error:
            raise MetricError(f"{name} must be a positive integer") from error
    else:
        raise MetricError(f"{name} must be a positive integer")
    if number <= 0:
        raise MetricError(f"{name} must be a positive integer")
    return number


def _period_rate(annual_rate: float, periods_per_year: float) -> float:
    if annual_rate <= -1:
        raise MetricError("annual rate must be greater than -1")
    return (1.0 + annual_rate) ** (1.0 / periods_per_year) - 1.0


def simple_returns(values: list[float]) -> list[float]:
    if any(value <= 0 for value in values):
        raise MetricError("wealth or price values must be > 0")
    return [values[index] / values[index - 1] - 1.0 for index in range(1, len(values))]


def max_drawdown(values: list[float]) -> dict[str, Any]:
    peak_value = values[0]
    peak_index = 0
    worst = 0.0
    worst_peak = 0
    trough_index = 0
    for index, value in enumerate(values):
        if value > peak_value:
            peak_value = value
            peak_index = index
        drawdown = value / peak_value - 1.0
        if drawdown < worst:
            worst = drawdown
            worst_peak = peak_index
            trough_index = index
    recovery_index = None
    peak_to_recover = values[worst_peak]
    for index in range(trough_index + 1, len(values)):
        if values[index] >= peak_to_recover:
            recovery_index = index
            break
    return {
        "value": worst,
        "peak_index": worst_peak,
        "trough_index": trough_index,
        "recovery_index": recovery_index,
    }


def return_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    values = _numbers(payload.get("values", []), "values", minimum=2)
    periods_per_year = _positive(payload.get("periods_per_year"), "periods_per_year")
    annual_rf = float(payload.get("risk_free_annual", 0.0))
    annual_mar = float(payload.get("minimum_acceptable_annual", 0.0))
    returns = simple_returns(values)
    mean_return = statistics.fmean(returns)
    vol_period = statistics.stdev(returns) if len(returns) >= 2 else None
    arithmetic_annual = mean_return * periods_per_year

    calendar_days = payload.get("calendar_days")
    cagr = None
    if calendar_days is not None:
        days = _positive(calendar_days, "calendar_days")
        cagr = (values[-1] / values[0]) ** (365.0 / days) - 1.0

    annual_vol = vol_period * math.sqrt(periods_per_year) if vol_period is not None else None
    rf_period = _period_rate(annual_rf, periods_per_year)
    excess = [ret - rf_period for ret in returns]
    excess_stdev = statistics.stdev(excess) if len(excess) >= 2 else None
    sharpe = None
    if excess_stdev not in (None, 0.0):
        sharpe = statistics.fmean(excess) / excess_stdev * math.sqrt(periods_per_year)

    mar_period = _period_rate(annual_mar, periods_per_year)
    downside = [min(ret - mar_period, 0.0) for ret in returns]
    downside_deviation_period = math.sqrt(statistics.fmean([item * item for item in downside]))
    sortino = None
    if downside_deviation_period != 0:
        sortino = (mean_return - mar_period) / downside_deviation_period * math.sqrt(periods_per_year)

    result: dict[str, Any] = {
        "n_values": len(values),
        "n_returns": len(returns),
        "periods_per_year": periods_per_year,
        "total_return": values[-1] / values[0] - 1.0,
        "cagr": cagr,
        "annualized_arithmetic_return": arithmetic_annual,
        "annualized_volatility": annual_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown(values),
    }

    benchmark_values_raw = payload.get("benchmark_values")
    if benchmark_values_raw is not None:
        benchmark_values = _numbers(benchmark_values_raw, "benchmark_values", minimum=2)
        if len(benchmark_values) != len(values):
            raise MetricError("benchmark_values must align one-to-one with values")
        benchmark_returns = simple_returns(benchmark_values)
        active = [left - right for left, right in zip(returns, benchmark_returns)]
        active_stdev = statistics.stdev(active) if len(active) >= 2 else None
        tracking_error = active_stdev * math.sqrt(periods_per_year) if active_stdev is not None else None
        information_ratio = None
        if active_stdev not in (None, 0.0):
            information_ratio = statistics.fmean(active) / active_stdev * math.sqrt(periods_per_year)

        benchmark_excess = [ret - rf_period for ret in benchmark_returns]
        if len(excess) >= 2:
            variance_benchmark = statistics.variance(benchmark_excess)
            beta = None
            alpha_annual = None
            if variance_benchmark != 0:
                covariance = statistics.covariance(excess, benchmark_excess)
                beta = covariance / variance_benchmark
                alpha_period = statistics.fmean(excess) - beta * statistics.fmean(benchmark_excess)
                if alpha_period > -1:
                    alpha_annual = (1.0 + alpha_period) ** periods_per_year - 1.0
            result.update({"beta": beta, "alpha_annual": alpha_annual})
        result.update({"tracking_error": tracking_error, "information_ratio": information_ratio})
    return result


def portfolio_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    weights = _numbers(payload.get("weights", []), "weights", minimum=1)
    if not math.isclose(sum(weights), 1.0, rel_tol=1e-8, abs_tol=1e-8):
        raise MetricError("weights must sum to 1.0")
    hhi = sum(weight * weight for weight in weights)
    top_n = int(payload.get("top_n", min(10, len(weights))))
    if top_n <= 0:
        raise MetricError("top_n must be positive")
    result: dict[str, Any] = {
        "hhi": hhi,
        "effective_number_of_holdings": 1.0 / hhi if hhi != 0 else None,
        "top_n_concentration": sum(sorted(weights, reverse=True)[:top_n]),
    }

    target_raw = payload.get("target_weights")
    if target_raw is not None:
        target = _numbers(target_raw, "target_weights", minimum=1)
        if len(target) != len(weights):
            raise MetricError("target_weights must align with weights")
        if not math.isclose(sum(target), 1.0, rel_tol=1e-8, abs_tol=1e-8):
            raise MetricError("target_weights must sum to 1.0")
        result["one_way_turnover"] = 0.5 * sum(abs(new - old) for old, new in zip(weights, target))

    covariance_raw = payload.get("covariance")
    if covariance_raw is not None:
        if not isinstance(covariance_raw, list) or len(covariance_raw) != len(weights):
            raise MetricError("covariance must be a square matrix aligned with weights")
        covariance = [_numbers(row, f"covariance[{index}]", minimum=len(weights)) for index, row in enumerate(covariance_raw)]
        if any(len(row) != len(weights) for row in covariance):
            raise MetricError("covariance must be square")
        marginal = [sum(covariance[i][j] * weights[j] for j in range(len(weights))) for i in range(len(weights))]
        variance = sum(weights[i] * marginal[i] for i in range(len(weights)))
        if variance < -1e-12:
            raise MetricError("portfolio variance cannot be negative")
        variance = max(variance, 0.0)
        volatility = math.sqrt(variance)
        risk_contribution = None
        risk_contribution_share = None
        if volatility != 0:
            risk_contribution = [weights[i] * marginal[i] / volatility for i in range(len(weights))]
            risk_contribution_share = [item / volatility for item in risk_contribution]
        result.update(
            {
                "portfolio_volatility_per_period": volatility,
                "risk_contribution": risk_contribution,
                "risk_contribution_share": risk_contribution_share,
            }
        )
    return result


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return statistics.fmean(values[-period:])


def _ema_series(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    seed = statistics.fmean(values[:period])
    alpha = 2.0 / (period + 1.0)
    output = [seed]
    for value in values[period:]:
        output.append(alpha * value + (1.0 - alpha) * output[-1])
    return output


def _wilder(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    output = [statistics.fmean(values[:period])]
    for value in values[period:]:
        output.append((output[-1] * (period - 1) + value) / period)
    return output


def technical_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    closes = _numbers(payload.get("closes", []), "closes", minimum=2)
    highs = _numbers(payload.get("highs", []), "highs", minimum=2)
    lows = _numbers(payload.get("lows", []), "lows", minimum=2)
    if not (len(closes) == len(highs) == len(lows)):
        raise MetricError("highs, lows, and closes must align")
    if any(high < low for high, low in zip(highs, lows)):
        raise MetricError("each high must be >= its low")
    period = int(payload.get("period", 14))
    if period <= 1:
        raise MetricError("period must be > 1")

    changes = [closes[index] - closes[index - 1] for index in range(1, len(closes))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    avg_gains = _wilder(gains, period)
    avg_losses = _wilder(losses, period)
    rsi = None
    if avg_gains and avg_losses:
        if avg_losses[-1] == 0:
            rsi = 100.0
        else:
            rs = avg_gains[-1] / avg_losses[-1]
            rsi = 100.0 - 100.0 / (1.0 + rs)

    true_ranges = [highs[0] - lows[0]]
    for index in range(1, len(closes)):
        true_ranges.append(max(highs[index] - lows[index], abs(highs[index] - closes[index - 1]), abs(lows[index] - closes[index - 1])))
    atr_series = _wilder(true_ranges, period)

    bollinger_period = _positive_integer(payload.get("bollinger_period", 20), "bollinger_period")
    bollinger_k = float(payload.get("bollinger_k", 2.0))
    middle = _sma(closes, bollinger_period)
    upper = lower = None
    if middle is not None:
        window = closes[-bollinger_period:]
        stdev_population = statistics.pstdev(window)
        upper = middle + bollinger_k * stdev_population
        lower = middle - bollinger_k * stdev_population

    ema_fast = _ema_series(closes, 12)
    ema_slow = _ema_series(closes, 26)
    macd = signal = histogram = None
    if ema_fast and ema_slow:
        fast_offset = len(closes) - len(ema_fast)
        slow_offset = len(closes) - len(ema_slow)
        start = max(fast_offset, slow_offset)
        macd_series = [ema_fast[index - fast_offset] - ema_slow[index - slow_offset] for index in range(start, len(closes))]
        signal_series = _ema_series(macd_series, 9)
        if signal_series:
            macd = macd_series[-1]
            signal = signal_series[-1]
            histogram = macd - signal

    return {
        "period": period,
        "sma": _sma(closes, period),
        "ema": _ema_series(closes, period)[-1] if _ema_series(closes, period) else None,
        "rsi_wilder": rsi,
        "atr_wilder": atr_series[-1] if atr_series else None,
        "bollinger": {"period": bollinger_period, "k": bollinger_k, "middle": middle, "upper": upper, "lower": lower},
        "macd": {"line": macd, "signal": signal, "histogram": histogram},
    }


def option_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    spots = _numbers(payload.get("underlying_prices", []), "underlying_prices", minimum=1)
    legs = payload.get("legs")
    if not isinstance(legs, list) or not legs:
        raise MetricError("legs must be a non-empty list")
    output = []
    for spot in spots:
        total = 0.0
        leg_results = []
        for index, leg in enumerate(legs):
            if not isinstance(leg, dict):
                raise MetricError(f"legs[{index}] must be an object")
            kind = leg.get("kind")
            side = leg.get("side")
            if kind not in {"call", "put"} or side not in {"long", "short"}:
                raise MetricError(f"legs[{index}] kind/side is invalid")
            strike = _positive(leg.get("strike"), f"legs[{index}].strike")
            premium = float(leg.get("premium"))
            quantity = _positive(leg.get("quantity", 1), f"legs[{index}].quantity")
            multiplier = _positive(leg.get("multiplier"), f"legs[{index}].multiplier")
            fees = float(leg.get("fees", 0.0))
            intrinsic = max(spot - strike, 0.0) if kind == "call" else max(strike - spot, 0.0)
            sign = 1.0 if side == "long" else -1.0
            pnl = sign * (intrinsic - premium) * quantity * multiplier - fees
            total += pnl
            leg_results.append({"index": index, "intrinsic_per_unit": intrinsic, "pnl": pnl})
        output.append({"underlying_price": spot, "total_pnl": total, "legs": leg_results})
    return {"scenarios": output}


def defi_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    ratio = _positive(payload.get("price_ratio"), "price_ratio")
    impermanent_loss = 2.0 * math.sqrt(ratio) / (1.0 + ratio) - 1.0
    result: dict[str, Any] = {"constant_product_50_50_impermanent_loss": impermanent_loss}
    if "fees" in payload or "average_capital" in payload or "days" in payload:
        fees = float(payload.get("fees"))
        average_capital = _positive(payload.get("average_capital"), "average_capital")
        days = _positive(payload.get("days"), "days")
        result["simple_fee_apr"] = fees / average_capital * 365.0 / days
    return result


OPERATIONS = {
    "return_metrics": return_metrics,
    "portfolio_metrics": portfolio_metrics,
    "technical_metrics": technical_metrics,
    "option_scenario": option_scenario,
    "defi_metrics": defi_metrics,
}


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    operation = payload.get("operation")
    if operation not in OPERATIONS:
        raise MetricError(f"operation must be one of: {', '.join(sorted(OPERATIONS))}")
    result = OPERATIONS[operation](payload)
    return {"status": "ok", "operation": operation, "result": result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to input JSON")
    parser.add_argument("--output", type=Path, help="Optional output JSON path")
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise MetricError("top-level JSON value must be an object")
        response = calculate(payload)
        exit_code = 0
    except (OSError, json.JSONDecodeError, MetricError, TypeError, ValueError) as error:
        response = {"status": "error", "error": str(error)}
        exit_code = 2
    serialized = json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
