#!/usr/bin/env python3
"""Validate a Yahoo Finance source artifact against the skill contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ensure_runtime import RuntimePreparationError, ensure_runtime

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "references" / "schemas" / "yahoo-finance-source.schema.json"


def load_jsonschema() -> Any:
    ensure_runtime()
    import jsonschema  # type: ignore

    return jsonschema


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def unexpected_keys(value: Any, allowed: set[str]) -> list[str]:
    if not isinstance(value, dict):
        return []
    return sorted(str(key) for key in value if key not in allowed)


def recursive_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(recursive_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(recursive_keys(item))
    return keys


def append_unexpected(errors: list[str], value: Any, allowed: set[str], location: str) -> None:
    present = unexpected_keys(value, allowed)
    if present:
        errors.append(f"{location} contains non-whitelisted fields: {', '.join(present)}.")


def semantic_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = payload.get("status")
    warnings = payload.get("warnings")
    operation = payload.get("operation")
    data = payload.get("data")
    source = payload.get("source_manifest_entry")

    if status == "partial" and not warnings:
        errors.append("A partial artifact must include at least one warning.")
    if status in {"failed", "blocked"} and data is not None:
        errors.append("A failed or blocked artifact must set data to null.")
    if status in {"ok", "partial"} and payload.get("data_as_of") is None:
        warnings_text = " ".join(str(item).lower() for item in warnings or [])
        if "timestamp" not in warnings_text and "observation" not in warnings_text:
            errors.append("A successful artifact with no data_as_of must explain the missing observation time.")

    query = payload.get("query")
    if isinstance(query, dict) and query.get("symbol") != payload.get("symbol"):
        errors.append("query.symbol must match the top-level symbol.")
    if isinstance(source, dict):
        title = str(source.get("title", ""))
        if operation and not title.startswith(f"{operation} for "):
            errors.append("source_manifest_entry.title must identify the confirmed Yahoo Finance operation.")
        if source.get("retrieved_at") != payload.get("retrieved_at"):
            errors.append("source_manifest_entry.retrieved_at must match the artifact retrieved_at.")
        if source.get("data_as_of") != payload.get("data_as_of"):
            errors.append("source_manifest_entry.data_as_of must match the artifact data_as_of.")

    if operation == "YahooFinance/get_stock_chart" and status in {"ok", "partial"}:
        if not isinstance(data, dict):
            errors.append("A successful chart artifact must contain an object in data.")
        else:
            append_unexpected(errors, data, {"meta", "bars", "events"}, "data")
            bars = data.get("bars")
            meta = data.get("meta")
            events = data.get("events")
            if not isinstance(meta, dict) or not meta.get("symbol"):
                errors.append("A chart artifact must include data.meta.symbol.")
            else:
                append_unexpected(
                    errors,
                    meta,
                    {
                        "symbol", "instrumentType", "currency", "exchangeName", "fullExchangeName",
                        "exchangeTimezoneName", "timezone", "gmtoffset", "dataGranularity", "range",
                        "regularMarketPrice", "regularMarketVolume", "chartPreviousClose", "fiftyTwoWeekHigh",
                        "fiftyTwoWeekLow", "regularMarketTime",
                    },
                    "data.meta",
                )
            if not isinstance(bars, list) or not bars:
                errors.append("A chart artifact must include at least one OHLCV bar.")
            else:
                for index, bar in enumerate(bars):
                    append_unexpected(
                        errors,
                        bar,
                        {"timestamp", "time", "open", "high", "low", "close", "adjusted_close", "volume"},
                        f"data.bars[{index}]",
                    )
            append_unexpected(errors, events, {"dividends", "capitalGains", "splits"}, "data.events")
            if isinstance(events, dict):
                event_fields = {
                    "dividends": {"amount", "date"},
                    "capitalGains": {"amount", "date"},
                    "splits": {"date", "numerator", "denominator", "splitRatio"},
                }
                for event_type, allowed_fields in event_fields.items():
                    container = events.get(event_type)
                    if isinstance(container, dict):
                        event_rows = list(container.values())
                    elif isinstance(container, list):
                        event_rows = container
                    else:
                        event_rows = []
                    for index, row in enumerate(event_rows):
                        append_unexpected(errors, row, allowed_fields, f"data.events.{event_type}[{index}]")

    if operation == "YahooFinance/get_stock_profile" and status in {"ok", "partial"}:
        if not isinstance(data, dict):
            errors.append("A successful profile artifact must contain an object in data.")
        else:
            append_unexpected(errors, data, {"profile", "price", "quote_type", "summary"}, "data")
            append_unexpected(
                errors,
                data.get("profile"),
                {"sector", "industry", "longBusinessSummary", "fullTimeEmployees", "website", "country"},
                "data.profile",
            )
            append_unexpected(
                errors,
                data.get("price"),
                {"symbol", "shortName", "longName", "currency", "exchangeName", "regularMarketPrice", "marketCap"},
                "data.price",
            )
            append_unexpected(
                errors,
                data.get("quote_type"),
                {"symbol", "quoteType", "exchange", "shortName", "longName"},
                "data.quote_type",
            )
            append_unexpected(
                errors,
                data.get("summary"),
                {"marketCap", "previousClose", "open", "dayLow", "dayHigh", "volume", "averageVolume"},
                "data.summary",
            )

    if operation == "YahooFinance/get_stock_holders" and status in {"ok", "partial"}:
        if not isinstance(data, dict):
            errors.append("A successful holders artifact must contain an object in data.")
        else:
            append_unexpected(
                errors,
                data,
                {"major_holders", "institutional_holders", "fund_holders", "insider_positions"},
                "data",
            )
            append_unexpected(
                errors,
                data.get("major_holders"),
                {"insidersPercentHeld", "institutionsPercentHeld", "institutionsFloatPercentHeld", "institutionsCount"},
                "data.major_holders",
            )
            for collection in ("institutional_holders", "fund_holders"):
                rows = data.get(collection)
                if isinstance(rows, list):
                    for index, row in enumerate(rows):
                        append_unexpected(
                            errors,
                            row,
                            {"organization", "pctHeld", "position", "value", "reportDate"},
                            f"data.{collection}[{index}]",
                        )
            rows = data.get("insider_positions")
            if isinstance(rows, list):
                for index, row in enumerate(rows):
                    append_unexpected(
                        errors,
                        row,
                        {"relation", "positionDirect", "positionDirectDate", "latestTransDate", "transactionDescription"},
                        f"data.insider_positions[{index}]",
                    )
            prohibited = {
                "name", "firstName", "middleName", "lastName", "email", "phone", "fax", "address",
                "address1", "address2", "city", "state", "zip", "postalCode",
            }
            present = sorted(recursive_keys(data).intersection(prohibited))
            if present:
                errors.append(f"Normalized holders data must omit personal identifiers and contact fields: {', '.join(present)}.")

    if operation == "YahooFinance/get_stock_insights" and status in {"ok", "partial"}:
        if not isinstance(data, dict):
            errors.append("A successful insights artifact must contain an object in data.")
        else:
            append_unexpected(errors, data, {"instrument_info", "company_snapshot", "recommendation", "events"}, "data")
            instrument = data.get("instrument_info")
            append_unexpected(errors, instrument, {"key_technicals", "technical_events", "valuation"}, "data.instrument_info")
            if isinstance(instrument, dict):
                append_unexpected(
                    errors,
                    instrument.get("key_technicals"),
                    {"provider", "support", "resistance", "stopLoss"},
                    "data.instrument_info.key_technicals",
                )
                technical = instrument.get("technical_events")
                append_unexpected(
                    errors,
                    technical,
                    {"provider", "sector", "shortTermOutlook", "intermediateTermOutlook", "longTermOutlook"},
                    "data.instrument_info.technical_events",
                )
                if isinstance(technical, dict):
                    outlook_fields = {
                        "direction", "indexDirection", "indexScore", "indexScoreDescription", "score",
                        "scoreDescription", "sectorDirection", "sectorScore", "sectorScoreDescription", "stateDescription",
                    }
                    for key in ("shortTermOutlook", "intermediateTermOutlook", "longTermOutlook"):
                        append_unexpected(errors, technical.get(key), outlook_fields, f"data.instrument_info.technical_events.{key}")
                append_unexpected(
                    errors,
                    instrument.get("valuation"),
                    {"provider", "description", "discount", "relativeValue", "color"},
                    "data.instrument_info.valuation",
                )
            snapshot = data.get("company_snapshot")
            append_unexpected(errors, snapshot, {"company", "sector", "sector_info"}, "data.company_snapshot")
            if isinstance(snapshot, dict):
                score_fields = {"dividends", "earningsReports", "hiring", "innovativeness", "insiderSentiments", "sustainability"}
                append_unexpected(errors, snapshot.get("company"), score_fields, "data.company_snapshot.company")
                append_unexpected(errors, snapshot.get("sector"), score_fields, "data.company_snapshot.sector")
            append_unexpected(errors, data.get("recommendation"), {"provider", "rating", "targetPrice"}, "data.recommendation")
            rows = data.get("events")
            if isinstance(rows, list):
                for index, row in enumerate(rows):
                    append_unexpected(
                        errors,
                        row,
                        {"eventType", "pricePeriod", "tradingHorizon", "tradeType", "startDate", "endDate"},
                        f"data.events[{index}]",
                    )
            report_fields = {"reports", "reportTitle", "title", "headHtml", "reportDate", "author", "analystName"}
            present = sorted(recursive_keys(data).intersection(report_fields))
            if present:
                errors.append(f"Normalized insights data must omit third-party report text and report metadata: {', '.join(present)}.")

    if operation == "YahooFinance/get_stock_sec_filing" and status in {"ok", "partial"}:
        if not isinstance(data, dict):
            errors.append("A successful filings artifact must contain an object in data.")
        else:
            append_unexpected(errors, data, {"filings"}, "data")
            rows = data.get("filings")
            if not isinstance(rows, list) or not rows:
                errors.append("A successful filings artifact must include at least one filing row.")
            else:
                for index, row in enumerate(rows):
                    append_unexpected(
                        errors,
                        row,
                        {"date", "epochDate", "type", "title", "edgarUrl", "exhibits"},
                        f"data.filings[{index}]",
                    )
                    if isinstance(row, dict):
                        exhibits = row.get("exhibits")
                        if isinstance(exhibits, list):
                            for exhibit_index, exhibit in enumerate(exhibits):
                                append_unexpected(
                                    errors,
                                    exhibit,
                                    {"type", "url"},
                                    f"data.filings[{index}].exhibits[{exhibit_index}]",
                                )
    return errors


def validate(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    schema = load_json(SCHEMA_PATH)
    jsonschema = load_jsonschema()
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = [error.message for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.path))]
    errors.extend(semantic_errors(payload))
    return {
        "status": "valid" if not errors else "invalid",
        "artifact": str(path),
        "errors": errors,
        "warnings": [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate(args.artifact)
    except RuntimePreparationError as exc:
        result = {
            "status": "blocked",
            "artifact": str(args.artifact),
            "errors": [str(exc)],
            "warnings": [],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    except Exception as exc:
        result = {
            "status": "invalid",
            "artifact": str(args.artifact),
            "errors": [str(exc)],
            "warnings": [],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
