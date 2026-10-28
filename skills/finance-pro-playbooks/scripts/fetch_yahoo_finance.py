#!/usr/bin/env python3
"""Fetch and normalize Yahoo Finance data through the Manus data API.

The adapter intentionally supports only operations confirmed by the Manus API
catalog. It emits a traceable source artifact and never fabricates or silently
substitutes values when the runtime or provider is unavailable.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import signal
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

SCHEMA_VERSION = "finance-analysis-pro/yahoo-finance-source/1.0"
PROVIDER = "Yahoo Finance"
RUNTIME_DIR = Path("/opt/.manus/.sandbox-runtime")
RATE_STATE_FILE = Path.home() / ".cache" / "manus-finance" / "yahoo-finance-last-call"
DEFAULT_MIN_INTERVAL_SECONDS = 0.75
DEFAULT_TIMEOUT_SECONDS = 30.0

OPERATIONS = {
    "chart": "YahooFinance/get_stock_chart",
    "profile": "YahooFinance/get_stock_profile",
    "holders": "YahooFinance/get_stock_holders",
    "insights": "YahooFinance/get_stock_insights",
    "filings": "YahooFinance/get_stock_sec_filing",
}
EQUITY_ONLY_OPERATIONS = {"profile", "holders", "insights", "filings"}
EXIT_CODES = {"ok": 0, "partial": 0, "failed": 1, "blocked": 2}


class ProviderTimeoutError(RuntimeError):
    """Raised when a Yahoo Finance call exceeds the configured deadline."""


@contextmanager
def provider_deadline(timeout_seconds: float):
    """Bound provider calls on Unix without adding a third-party dependency."""

    if timeout_seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    previous_handler = signal.getsignal(signal.SIGALRM)

    def handle_timeout(_signum: int, _frame: Any) -> None:
        raise ProviderTimeoutError(f"Yahoo Finance did not respond within {timeout_seconds:g} seconds.")

    signal.signal(signal.SIGALRM, handle_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def epoch_to_iso(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(timestamp):
        return None
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return None


def raw_value(value: Any) -> Any:
    """Recursively prefer provider numeric `raw` values over display strings."""

    if isinstance(value, dict):
        if "raw" in value:
            return raw_value(value["raw"])
        return {str(key): raw_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [raw_value(item) for item in value]
    return value


def safe_value(sequence: Any, index: int) -> Any:
    if not isinstance(sequence, list) or index >= len(sequence):
        return None
    return raw_value(sequence[index])


def source_url(symbol: str, operation: str) -> str:
    encoded = quote(symbol, safe="")
    suffix = {
        "chart": "history/",
        "profile": "profile/",
        "holders": "holders/",
        "insights": "analysis/",
        "filings": "sec-filings/",
    }[operation]
    return f"https://finance.yahoo.com/quote/{encoded}/{suffix}"


def source_ref(symbol: str, operation: str, retrieved_at: str) -> str:
    timestamp = re.sub(r"[^0-9]", "", retrieved_at)
    clean_symbol = re.sub(r"[^a-z0-9]+", "-", symbol.lower()).strip("-") or "instrument"
    return f"yf-{operation}-{clean_symbol}-{timestamp}"


def source_entry(symbol: str, operation: str, retrieved_at: str, data_as_of: str | None) -> dict[str, Any]:
    operation_id = OPERATIONS[operation]
    return {
        "source_ref": source_ref(symbol, operation, retrieved_at),
        "title": f"{operation_id} for {symbol}",
        "publisher": PROVIDER,
        "url": source_url(symbol, operation),
        "retrieved_at": retrieved_at,
        "data_as_of": data_as_of,
        "source_type": "market_data",
        "period": None,
        "original_or_derived": "original",
    }


def base_artifact(
    *,
    status: str,
    symbol: str,
    operation: str,
    query: dict[str, Any],
    retrieved_at: str,
    data_as_of: str | None,
    data: dict[str, Any] | list[Any] | None,
    warnings: list[str],
    error: dict[str, Any] | None,
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "provider": PROVIDER,
        "operation": OPERATIONS[operation],
        "symbol": symbol,
        "query": query,
        "retrieved_at": retrieved_at,
        "data_as_of": data_as_of,
        "source_manifest_entry": source_entry(symbol, operation, retrieved_at, data_as_of),
        "data": data,
        "warnings": warnings,
        "error": error,
    }
    return artifact


def write_json(path: Path | None, payload: dict[str, Any]) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path is None:
        sys.stdout.write(rendered)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(rendered)
        temporary = Path(handle.name)
    temporary.replace(path)


def wait_for_rate_limit(min_interval_seconds: float, state_file: Path = RATE_STATE_FILE) -> None:
    """Apply a shared best-effort delay between consecutive Yahoo Finance calls."""

    if min_interval_seconds <= 0:
        return
    state_file.parent.mkdir(parents=True, exist_ok=True)
    previous = 0.0
    try:
        previous = float(state_file.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, OSError, ValueError):
        previous = 0.0
    remaining = min_interval_seconds - (time.time() - previous)
    if remaining > 0:
        time.sleep(remaining)
    state_file.write_text(f"{time.time():.6f}\n", encoding="utf-8")


def load_client_class() -> tuple[type[Any] | None, str | None]:
    if not RUNTIME_DIR.is_dir():
        return None, f"Manus data API runtime not found at {RUNTIME_DIR}."
    runtime = str(RUNTIME_DIR)
    if runtime not in sys.path:
        sys.path.append(runtime)
    try:
        from data_api import ApiClient  # type: ignore
    except Exception as exc:  # pragma: no cover - exact import error is environment-specific
        return None, f"Unable to import Manus data API client: {exc}"
    return ApiClient, None


def provider_error(response: Any) -> dict[str, Any] | None:
    if not isinstance(response, dict):
        return {"code": "invalid_response", "message": "Provider response is not a JSON object."}
    direct = response.get("error")
    if direct:
        return {"code": "provider_error", "message": str(direct)}
    for container_name in ("chart", "quoteSummary", "finance"):
        container = response.get(container_name)
        if isinstance(container, dict) and container.get("error"):
            return {"code": "provider_error", "message": str(container["error"])}
    return None


def first_result(response: dict[str, Any], containers: tuple[str, ...]) -> dict[str, Any] | None:
    for name in containers:
        container = response.get(name)
        if isinstance(container, dict):
            results = container.get("result")
            if isinstance(results, list) and results and isinstance(results[0], dict):
                return results[0]
            if isinstance(results, dict):
                return results
    direct_result = response.get("result")
    if isinstance(direct_result, list) and direct_result and isinstance(direct_result[0], dict):
        return direct_result[0]
    if isinstance(direct_result, dict):
        return direct_result
    return None


def normalize_chart_events(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    field_map = {
        "dividends": ("amount", "date"),
        "capitalGains": ("amount", "date"),
        "splits": ("date", "numerator", "denominator", "splitRatio"),
    }
    normalized: dict[str, Any] = {}
    for event_type, fields in field_map.items():
        container = value.get(event_type)
        if isinstance(container, dict):
            rows = {
                str(event_id): approved_fields(row, fields)
                for event_id, row in container.items()
                if isinstance(row, dict)
            }
            if rows:
                normalized[event_type] = rows
        elif isinstance(container, list):
            rows = [approved_fields(row, fields) for row in container if isinstance(row, dict)]
            if rows:
                normalized[event_type] = rows
    return normalized


def normalize_chart(response: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    result = first_result(response, ("chart",))
    if result is None:
        return None, None, ["Yahoo Finance returned no chart result."]

    meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    indicators = result.get("indicators") if isinstance(result.get("indicators"), dict) else {}
    quotes = indicators.get("quote") if isinstance(indicators.get("quote"), list) else []
    quote_data = quotes[0] if quotes and isinstance(quotes[0], dict) else {}
    adjusted = indicators.get("adjclose") if isinstance(indicators.get("adjclose"), list) else []
    adjusted_data = adjusted[0] if adjusted and isinstance(adjusted[0], dict) else {}
    timestamps = result.get("timestamp") if isinstance(result.get("timestamp"), list) else []

    bars: list[dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        bars.append(
            {
                "timestamp": raw_value(timestamp),
                "time": epoch_to_iso(timestamp),
                "open": safe_value(quote_data.get("open"), index),
                "high": safe_value(quote_data.get("high"), index),
                "low": safe_value(quote_data.get("low"), index),
                "close": safe_value(quote_data.get("close"), index),
                "adjusted_close": safe_value(adjusted_data.get("adjclose"), index),
                "volume": safe_value(quote_data.get("volume"), index),
            }
        )

    regular_market_time = raw_value(meta.get("regularMarketTime"))
    data_as_of = epoch_to_iso(regular_market_time)
    if data_as_of is None and timestamps:
        data_as_of = epoch_to_iso(timestamps[-1])

    normalized_meta_keys = (
        "symbol",
        "instrumentType",
        "currency",
        "exchangeName",
        "fullExchangeName",
        "exchangeTimezoneName",
        "timezone",
        "gmtoffset",
        "dataGranularity",
        "range",
        "regularMarketPrice",
        "regularMarketVolume",
        "chartPreviousClose",
        "fiftyTwoWeekHigh",
        "fiftyTwoWeekLow",
    )
    normalized_meta = {key: raw_value(meta.get(key)) for key in normalized_meta_keys if key in meta}
    normalized_meta["regularMarketTime"] = data_as_of

    warnings: list[str] = []
    if not bars:
        warnings.append("Yahoo Finance returned metadata but no OHLCV bars.")
    if bars and any(bar["close"] is None for bar in bars):
        warnings.append("One or more chart observations have a missing close value.")
    if data_as_of is None:
        warnings.append("The provider response did not include a usable market observation time.")

    return {
        "meta": normalized_meta,
        "bars": bars,
        "events": normalize_chart_events(result.get("events")),
    }, data_as_of, warnings


def normalize_profile(response: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    result = first_result(response, ("quoteSummary", "finance"))
    if result is None:
        return None, None, ["Yahoo Finance returned no profile result."]

    if isinstance(result.get("assetProfile"), dict):
        profile = result["assetProfile"]
    elif isinstance(result.get("summaryProfile"), dict):
        profile = result["summaryProfile"]
    else:
        profile = {}
    price = result.get("price") if isinstance(result.get("price"), dict) else {}
    quote_type = result.get("quoteType") if isinstance(result.get("quoteType"), dict) else {}
    summary = result.get("summaryDetail") if isinstance(result.get("summaryDetail"), dict) else {}

    profile_fields = ("sector", "industry", "longBusinessSummary", "fullTimeEmployees", "website", "country")
    price_fields = ("symbol", "shortName", "longName", "currency", "exchangeName", "regularMarketPrice", "marketCap")
    quote_fields = ("symbol", "quoteType", "exchange", "shortName", "longName")
    summary_fields = ("marketCap", "previousClose", "open", "dayLow", "dayHigh", "volume", "averageVolume")

    data_as_of = epoch_to_iso(raw_value(price.get("regularMarketTime")))
    warnings: list[str] = []
    if data_as_of is None:
        warnings.append("The profile response did not include a usable market observation time.")

    normalized = {
        "profile": {key: raw_value(profile.get(key)) for key in profile_fields if key in profile},
        "price": {key: raw_value(price.get(key)) for key in price_fields if key in price},
        "quote_type": {key: raw_value(quote_type.get(key)) for key in quote_fields if key in quote_type},
        "summary": {key: raw_value(summary.get(key)) for key in summary_fields if key in summary},
    }
    if not any(normalized.values()):
        return None, data_as_of, ["Yahoo Finance returned a profile container with no approved fields."]
    return normalized, data_as_of, warnings


def approved_fields(value: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: raw_value(value.get(key)) for key in fields if key in value}


def normalize_holders(response: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    result = first_result(response, ("quoteSummary", "finance"))
    if result is None:
        return None, None, ["Yahoo Finance returned no holders result."]

    major = result.get("majorHoldersBreakdown") if isinstance(result.get("majorHoldersBreakdown"), dict) else {}
    institution_container = result.get("institutionOwnership") if isinstance(result.get("institutionOwnership"), dict) else {}
    fund_container = result.get("fundOwnership") if isinstance(result.get("fundOwnership"), dict) else {}
    insider_container = result.get("insiderHolders") if isinstance(result.get("insiderHolders"), dict) else {}

    institution_rows = institution_container.get("ownershipList") if isinstance(institution_container.get("ownershipList"), list) else []
    fund_rows = fund_container.get("ownershipList") if isinstance(fund_container.get("ownershipList"), list) else []
    insider_rows = insider_container.get("holders") if isinstance(insider_container.get("holders"), list) else []

    organization_fields = ("organization", "pctHeld", "position", "value", "reportDate")
    insider_fields = (
        "relation",
        "positionDirect",
        "positionDirectDate",
        "latestTransDate",
        "transactionDescription",
    )
    normalized = {
        "major_holders": approved_fields(
            major,
            (
                "insidersPercentHeld",
                "institutionsPercentHeld",
                "institutionsFloatPercentHeld",
                "institutionsCount",
            ),
        ),
        "institutional_holders": [approved_fields(row, organization_fields) for row in institution_rows if isinstance(row, dict)],
        "fund_holders": [approved_fields(row, organization_fields) for row in fund_rows if isinstance(row, dict)],
        "insider_positions": [approved_fields(row, insider_fields) for row in insider_rows if isinstance(row, dict)],
    }
    normalized = {key: value for key, value in normalized.items() if value}
    if not normalized:
        return None, None, ["Yahoo Finance returned a holders container with no approved fields."]

    dated_values: list[int | float] = []
    for collection in (institution_rows, fund_rows, insider_rows):
        for row in collection:
            if not isinstance(row, dict):
                continue
            for key in ("reportDate", "positionDirectDate", "latestTransDate"):
                value = raw_value(row.get(key))
                if isinstance(value, (int, float)):
                    dated_values.append(value)
    data_as_of = epoch_to_iso(max(dated_values)) if dated_values else None
    warnings = ["Public-person names from insider-holder records were omitted under the privacy-minimization policy."]
    if data_as_of is None:
        warnings.append("The provider response did not expose a usable holder observation timestamp.")
    return normalized, data_as_of, warnings


def normalize_insights(response: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    result = first_result(response, ("finance", "quoteSummary"))
    if result is None:
        return None, None, ["Yahoo Finance returned no insights result."]

    instrument = result.get("instrumentInfo") if isinstance(result.get("instrumentInfo"), dict) else {}
    snapshot = result.get("companySnapshot") if isinstance(result.get("companySnapshot"), dict) else {}
    recommendation = approved_fields(result.get("recommendation"), ("provider", "rating", "targetPrice"))
    event_fields = ("eventType", "pricePeriod", "tradingHorizon", "tradeType", "startDate", "endDate")
    events = result.get("events") if isinstance(result.get("events"), list) else []

    outlook_fields = (
        "direction",
        "indexDirection",
        "indexScore",
        "indexScoreDescription",
        "score",
        "scoreDescription",
        "sectorDirection",
        "sectorScore",
        "sectorScoreDescription",
        "stateDescription",
    )
    technical_events_source = instrument.get("technicalEvents") if isinstance(instrument.get("technicalEvents"), dict) else {}
    technical_events = approved_fields(technical_events_source, ("provider", "sector"))
    for key in ("shortTermOutlook", "intermediateTermOutlook", "longTermOutlook"):
        outlook = approved_fields(technical_events_source.get(key), outlook_fields)
        if outlook:
            technical_events[key] = outlook

    instrument_info = {
        "key_technicals": approved_fields(
            instrument.get("keyTechnicals"),
            ("provider", "support", "resistance", "stopLoss"),
        ),
        "technical_events": technical_events,
        "valuation": approved_fields(
            instrument.get("valuation"),
            ("provider", "description", "discount", "relativeValue", "color"),
        ),
    }
    instrument_info = {key: value for key, value in instrument_info.items() if value}

    score_fields = ("dividends", "earningsReports", "hiring", "innovativeness", "insiderSentiments", "sustainability")
    company_snapshot = {
        "company": approved_fields(snapshot.get("company"), score_fields),
        "sector": approved_fields(snapshot.get("sector"), score_fields),
    }
    if isinstance(snapshot.get("sectorInfo"), str):
        company_snapshot["sector_info"] = snapshot["sectorInfo"]
    company_snapshot = {key: value for key, value in company_snapshot.items() if value}

    normalized = {
        "instrument_info": instrument_info,
        "company_snapshot": company_snapshot,
        "recommendation": recommendation,
        "events": [approved_fields(row, event_fields) for row in events if isinstance(row, dict)],
    }
    normalized = {key: value for key, value in normalized.items() if value}
    if not normalized:
        return None, None, ["Yahoo Finance returned an insights container with no approved fields."]

    event_dates: list[int | float] = []
    for row in events:
        if not isinstance(row, dict):
            continue
        for key in ("startDate", "endDate"):
            value = raw_value(row.get(key))
            if isinstance(value, (int, float)):
                event_dates.append(value)
    data_as_of = epoch_to_iso(max(event_dates)) if event_dates else None
    warnings = [
        "Third-party ratings, target prices, technical events, and model scores are secondary evidence and require independent validation.",
        "Full third-party research reports and report text were intentionally omitted from the normalized artifact.",
    ]
    if data_as_of is None:
        warnings.append("The provider response did not expose a usable insight observation timestamp.")
    return normalized, data_as_of, warnings


def normalize_filings(response: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    result = first_result(response, ("quoteSummary", "finance"))
    if result is None:
        return None, None, ["Yahoo Finance returned no filings result."]

    filings_section = result.get("secFilings") if isinstance(result.get("secFilings"), dict) else result
    filing_rows = filings_section.get("filings") if isinstance(filings_section, dict) and isinstance(filings_section.get("filings"), list) else []
    normalized_rows: list[dict[str, Any]] = []
    dated_values: list[int | float] = []
    for row in filing_rows:
        if not isinstance(row, dict):
            continue
        exhibits = row.get("exhibits") if isinstance(row.get("exhibits"), list) else []
        normalized_row = approved_fields(row, ("date", "epochDate", "type", "title", "edgarUrl"))
        normalized_row["exhibits"] = [approved_fields(item, ("type", "url")) for item in exhibits if isinstance(item, dict)]
        normalized_rows.append(normalized_row)
        epoch_date = raw_value(row.get("epochDate"))
        if isinstance(epoch_date, (int, float)):
            dated_values.append(epoch_date)

    if not normalized_rows:
        return None, None, ["Yahoo Finance returned a filings container with no approved filing rows."]
    data_as_of = epoch_to_iso(max(dated_values)) if dated_values else None
    warnings = [
        "Yahoo Finance filing links are discovery aids; verify filing content and dates against the relevant regulator before material use."
    ]
    if data_as_of is None:
        warnings.append("The provider response did not expose a usable filing timestamp.")
    return {"filings": normalized_rows}, data_as_of, warnings


def normalize_response(response: dict[str, Any], operation: str) -> tuple[dict[str, Any] | list[Any] | None, str | None, list[str]]:
    if operation == "chart":
        return normalize_chart(response)
    if operation == "profile":
        return normalize_profile(response)
    if operation == "holders":
        return normalize_holders(response)
    if operation == "insights":
        return normalize_insights(response)
    if operation == "filings":
        return normalize_filings(response)
    return None, None, [f"Unsupported Yahoo Finance operation: {operation}."]


def build_query(args: argparse.Namespace) -> dict[str, Any]:
    symbol = str(args.symbol).strip()
    if not symbol or len(symbol) > 64 or not re.fullmatch(r"[A-Za-z0-9.^=_-]+", symbol):
        raise ValueError("--symbol must be a non-empty Yahoo Finance symbol using only letters, digits, '.', '^', '=', '_', or '-'.")
    if not 0 < args.timeout <= 120:
        raise ValueError("--timeout must be greater than zero and no more than 120 seconds; the hard provider deadline cannot be disabled.")
    if not 0 <= args.min_interval <= 60:
        raise ValueError("--min-interval must be between 0 and 60 seconds.")
    args.symbol = symbol

    query: dict[str, Any] = {"symbol": symbol}
    if args.operation != "insights":
        if args.region:
            region = str(args.region).strip()
            if len(region) > 16 or not re.fullmatch(r"[A-Za-z-]+", region):
                raise ValueError("--region must contain only letters or hyphens and be no longer than 16 characters.")
            query["region"] = region
        if args.lang:
            lang = str(args.lang).strip()
            if len(lang) > 16 or not re.fullmatch(r"[A-Za-z-]+", lang):
                raise ValueError("--lang must contain only letters or hyphens and be no longer than 16 characters.")
            query["lang"] = lang

    if args.operation == "chart":
        interval = str(args.interval).strip()
        if not interval or len(interval) > 16 or not re.fullmatch(r"[A-Za-z0-9]+", interval):
            raise ValueError("--interval must be a non-empty alphanumeric Yahoo Finance interval.")
        query["interval"] = interval
        if args.period1 is not None or args.period2 is not None:
            if args.period1 is None or args.period2 is None:
                raise ValueError("Chart requests must provide both --period1 and --period2.")
            if args.period1 < 0 or args.period2 < 0 or args.period1 >= args.period2:
                raise ValueError("Chart timestamps must be non-negative and --period1 must be earlier than --period2.")
            query["period1"] = args.period1
            query["period2"] = args.period2
        else:
            range_value = str(args.range).strip()
            if not range_value or len(range_value) > 16 or not re.fullmatch(r"[A-Za-z0-9]+", range_value):
                raise ValueError("--range must be a non-empty alphanumeric Yahoo Finance range.")
            query["range"] = range_value
        query["includePrePost"] = bool(args.include_pre_post)
        query["includeAdjustedClose"] = True
    return query


def fetch(args: argparse.Namespace, client_class: type[Any] | None = None) -> dict[str, Any]:
    retrieved_at = utc_now()
    try:
        query = build_query(args)
    except ValueError as exc:
        failed_symbol = str(args.symbol).strip()
        if not failed_symbol or len(failed_symbol) > 64 or not re.fullmatch(r"[A-Za-z0-9.^=_-]+", failed_symbol):
            failed_symbol = "invalid-symbol"
        return base_artifact(
            status="failed",
            symbol=failed_symbol,
            operation=args.operation,
            query={"symbol": failed_symbol},
            retrieved_at=retrieved_at,
            data_as_of=None,
            data=None,
            warnings=[],
            error={"code": "invalid_request", "message": str(exc)},
        )

    if args.operation in EQUITY_ONLY_OPERATIONS and args.asset_class != "equity":
        return base_artifact(
            status="failed",
            symbol=args.symbol,
            operation=args.operation,
            query=query,
            retrieved_at=retrieved_at,
            data_as_of=None,
            data=None,
            warnings=[],
            error={
                "code": "unsupported_asset_operation",
                "message": f"The {args.operation} operation is restricted to equity instruments.",
            },
        )

    runtime_error: str | None = None
    if client_class is None:
        client_class, runtime_error = load_client_class()
    if client_class is None:
        return base_artifact(
            status="blocked",
            symbol=args.symbol,
            operation=args.operation,
            query=query,
            retrieved_at=retrieved_at,
            data_as_of=None,
            data=None,
            warnings=[],
            error={"code": "runtime_unavailable", "message": runtime_error or "Manus data API runtime unavailable."},
        )

    try:
        client = client_class()
    except Exception as exc:
        return base_artifact(
            status="blocked",
            symbol=args.symbol,
            operation=args.operation,
            query=query,
            retrieved_at=retrieved_at,
            data_as_of=None,
            data=None,
            warnings=[],
            error={"code": "runtime_initialization_failed", "message": str(exc)},
        )

    wait_for_rate_limit(args.min_interval)
    try:
        with provider_deadline(args.timeout):
            response = client.call_api(OPERATIONS[args.operation], query=query)
    except ProviderTimeoutError as exc:
        return base_artifact(
            status="failed",
            symbol=args.symbol,
            operation=args.operation,
            query=query,
            retrieved_at=retrieved_at,
            data_as_of=None,
            data=None,
            warnings=[],
            error={"code": "provider_timeout", "message": str(exc)},
        )
    except Exception as exc:  # Defensive: ApiClient normally returns an error object.
        return base_artifact(
            status="failed",
            symbol=args.symbol,
            operation=args.operation,
            query=query,
            retrieved_at=retrieved_at,
            data_as_of=None,
            data=None,
            warnings=[],
            error={"code": "provider_call_failed", "message": str(exc)},
        )

    error = provider_error(response)
    if error is not None:
        return base_artifact(
            status="failed",
            symbol=args.symbol,
            operation=args.operation,
            query=query,
            retrieved_at=retrieved_at,
            data_as_of=None,
            data=None,
            warnings=[],
            error=error,
        )

    normalized, data_as_of, warnings = normalize_response(response, args.operation)
    if normalized is None:
        status = "failed"
        error = {"code": "empty_result", "message": warnings[0] if warnings else "Yahoo Finance returned no usable data."}
    else:
        status = "partial" if warnings else "ok"
        error = None

    return base_artifact(
        status=status,
        symbol=args.symbol,
        operation=args.operation,
        query=query,
        retrieved_at=retrieved_at,
        data_as_of=data_as_of,
        data=normalized,
        warnings=warnings,
        error=error,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=sorted(OPERATIONS))
    parser.add_argument("--symbol", required=True, help="Yahoo Finance ticker, including exchange suffix when applicable.")
    parser.add_argument(
        "--asset-class",
        choices=("equity", "etf", "index", "crypto", "forex", "future", "other"),
        default="equity",
        help="Used to enforce operation-specific data boundaries.",
    )
    parser.add_argument("--region", default=None)
    parser.add_argument("--lang", default=None)
    parser.add_argument("--interval", default="1d", help="Chart interval, for example 1m, 1h, 1d, or 1wk.")
    parser.add_argument("--range", default="1y", help="Chart range used when period1/period2 are omitted.")
    parser.add_argument("--period1", type=int, default=None, help="Chart start as a Unix timestamp.")
    parser.add_argument("--period2", type=int, default=None, help="Chart end as a Unix timestamp.")
    parser.add_argument("--include-pre-post", action="store_true")
    parser.add_argument("--min-interval", type=float, default=DEFAULT_MIN_INTERVAL_SECONDS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Provider deadline in seconds.")
    parser.add_argument("--output", type=Path, default=None, help="Write the source artifact to this JSON file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    artifact = fetch(args)
    write_json(args.output, artifact)
    return EXIT_CODES.get(str(artifact.get("status")), 1)


if __name__ == "__main__":
    raise SystemExit(main())
