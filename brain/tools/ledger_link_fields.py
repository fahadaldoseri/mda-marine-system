#!/usr/bin/env python3
"""Derive strict, evidence-backed links between cumulative ledger rows.

The tool intentionally uses only literal identifiers and explicit phrases.  It
never uses title similarity, semantic similarity, or a score.  It computes the
whole ledger as context and writes only the requested day(s).
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


ALLOWED_EVENT_KINDS = ("جديد", "تحديث", "تكرار", "فرع تابع")
RELATION_FIELDS = ("update_of", "parent_id", "duplicate_of")
DERIVED_FIELDS = (
    "event_kind",
    "update_of",
    "parent_id",
    "duplicate_of",
    "link_basis",
    "link_evidence",
    "link_status",
    "counts_as_new",
)

# The first seven are the Arabic signals required by the contract.  The
# English equivalents are literal source text in this ledger and are handled
# as explicit text, never as semantic inference.
EXPLICIT_SIGNAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("تحديث", re.compile(r"تحديث(?:ًا|اً)?")),
    ("كما ورد سابقًا", re.compile(r"كما ورد سابقًا")),
    ("المذكور أعلاه", re.compile(r"المذكور أعلاه")),
    ("متابعة", re.compile(r"متابعة")),
    ("فرع من", re.compile(r"فرع من")),
    ("سبق أن", re.compile(r"سبق أن")),
    ("update", re.compile(r"(?i)\bupdates?\b|\bupdated\b|\bfollow[- ]?up\b")),
    ("branch", re.compile(r"(?i)\bbranch(?:ed)?\s+from\b")),
    ("previously", re.compile(r"(?i)\bpreviously\b|\babove[- ]mentioned\b")),
)

# These patterns extract official identities, not arbitrary numbers.  A bare
# numeric pair is accepted only when it is immediately introduced by an
# explicit update/warning phrase; dates elsewhere in a source are never IDs.
UKMTO_WARNING_RE = re.compile(
    r"(?i)\bUKMTO\s*[- _:]?\s*(?:WARNING\s*[- _:]?\s*)?"
    r"(\d{1,3})[-/](\d{2,4})"
    r"(?:\s*[-_/ ]?\s*(?:UPDATE|التحديث)\s*[-_/ ]?\s*(\d{1,3}))?"
)
WARNING_RE = re.compile(
    r"(?i)\bWARNING\s*#?\s*(\d{1,3})[-/](\d{2,4})"
    r"(?:\s*UPDATE\s*[-_/ ]?\s*(\d{1,3}))?"
)
GENERIC_WARNING_ID_RE = re.compile(
    r"(?i)(?:\b(?:تحديث|update)\s+(?:التحذير\s+)?|\bwarning\s+)"
    r"(\d{1,3})[-/](\d{2,4})(?:\s*/\s*(\d{1,3}))?\b"
)
UKMTO_REPORT_RE = re.compile(r"(?i)\bUKMTO\s*#\s*(\d{1,4})\b")
JMIC_RE = re.compile(
    r"(?i)\bJMIC\s*[- _]?\s*(?:ADVISORY\s*[- _]?\s*"
    r"(?:NOTE|UPDATE)?\s*[- _]?\s*)?(\d{1,4})"
    r"(?:[-/](\d{2,4}))?\b"
)
NAVAREA_RE = re.compile(
    r"(?i)\bNAVAREA\s+[IVX]+\s*[-:# ]?\s*(\d{1,4})[-/](\d{2,4})\b"
)
MSCIO_RE = re.compile(
    r"(?i)\bMSCIO\s+(?:ALERT|UPDATE)\s*[-:# ]?\s*"
    r"(\d{1,4})(?:[-/](\d{2,4}))?\b"
)
INCIDENT_RE = re.compile(
    r"(?i)\b(?:UKMTO\s*[- ]?\s*)?INCIDENT\s*[-:# ]?\s*"
    r"(\d{4})[-/](\d{2})[-/](\d{2})(?:[-_][A-Z0-9]+)*\b"
)
GENERIC_INCIDENT_RE = re.compile(r"(?i)\bINCIDENT\s*#?\s*(\d{1,4})\b")
IMO_RE = re.compile(r"(?i)\bIMO\s*[-:# ]?\s*(\d{7})\b")
UKMTO_SEQUENCE_RE = re.compile(
    r"(?i)\bUKMTO\s*[- _:]?\s*(?:WARNING\s*[- _:]?\s*)?"
    r"(\d{1,3})[-/](\d{2,4})"
    r"(?:\s*[-_/ ]?\s*UPDATE\s*[-_/ ]?\s*(\d{1,3}))?"
)
JMIC_SEQUENCE_RE = re.compile(
    r"(?i)\bJMIC\s*[- _:]?\s*(?:ADVISORY\s*[- _:]?\s*(?:NOTE|UPDATE)?\s*)?"
    r"(\d{1,4})(?:[-/](\d{2,4}))?\b"
)
JMIC_ARABIC_UPDATE_RE = re.compile(
    r"(?i)\bJMIC\b.{0,30}?\b(?:تحديث|UPDATE)\s*[-:# ]?\s*"
    r"(\d{1,4})(?:[-/](\d{2,4}))?\b"
)
MSCIO_SEQUENCE_RE = re.compile(
    r"(?i)\bMSCIO\s*(?:ALERT|UPDATE)\s*[-:# _]?\s*"
    r"(\d{1,4})(?:[-/](\d{2,4}))?\b"
)
GENERIC_UPDATED_SEQUENCE_RE = re.compile(
    r"(?i)(?:\b(?:تحديث|update)\s+)"
    r"(\d{1,3})[-/](\d{2,4})\s*/\s*(\d{1,3})\b"
)
EXPLICIT_BRANCH_RE = re.compile(
    r"(?i)فرع من|امتداد|الحادثة ذاتها|السفينة ذاتها|"
    r"branch\s+from|extension|same\s+incident|same\s+vessel"
)


class LedgerError(Exception):
    """A real data or validation failure; the CLI returns exit code 2."""


@dataclass
class RefEvidence:
    key: str
    family: str
    evidence: str
    update_marker: bool = False


@dataclass
class SequenceEvidence:
    issuer: str
    series: str
    number: int
    year: str | None
    suffix: int | None
    update_marker: bool
    evidence: str


@dataclass
class Row:
    path: Path
    file_order: int
    row_index: int
    data: dict[str, Any]
    date: dt.date
    order: tuple[dt.date, str, int]
    code: str | None
    refs: list[RefEvidence] = field(default_factory=list)
    imo_numbers: set[str] = field(default_factory=set)
    vessel_name: str | None = None
    signals: list[str] = field(default_factory=list)
    sequence_refs: list[SequenceEvidence] = field(default_factory=list)

    @property
    def row_key(self) -> tuple[str, int]:
        return (str(self.path), self.row_index)


@dataclass
class Candidate:
    row: Row
    basis: str
    evidence: str
    priority: int
    provenance: str


def text_value(value: Any) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def date_from_row(path: Path, data: dict[str, Any]) -> dt.date:
    raw = data.get("date")
    try:
        return dt.date.fromisoformat(text_value(raw))
    except (TypeError, ValueError) as exc:
        raise LedgerError(f"invalid or missing date in {path}: {raw!r}") from exc


def source_fields(data: dict[str, Any]) -> Iterable[tuple[str, str]]:
    for field_name in ("official_ref", "title", "source_excerpt", "imo_number"):
        yield field_name, text_value(data.get(field_name))
    source = text_value(data.get("source"))
    if source and not re.match(r"(?i)^https?://", source):
        yield "source", source


def has_update_marker(text: str) -> bool:
    return bool(
        re.search(r"تحديث(?:ًا|اً)?|(?i:\bupdates?\b|\bupdated\b|\bfollow[- ]?up\b)", text)
    )


def extract_refs(data: dict[str, Any]) -> list[RefEvidence]:
    found: dict[tuple[str, str], RefEvidence] = {}

    def add(key: str, family: str, evidence: str, text: str) -> None:
        item = RefEvidence(key, family, evidence, has_update_marker(text))
        dedupe_key = (key, evidence)
        prior = found.get(dedupe_key)
        if prior is None or item.update_marker and not prior.update_marker:
            found[dedupe_key] = item

    for _field_name, text in source_fields(data):
        if not text:
            continue
        for match in UKMTO_WARNING_RE.finditer(text):
            number, year, update_number = match.groups()
            add(
                f"UKMTO-WARNING-{number}-{year}",
                "warning",
                f"{number}-{year}",
                text,
            )
        for match in WARNING_RE.finditer(text):
            number, year, _update_number = match.groups()
            add(
                f"UKMTO-WARNING-{number}-{year}",
                "warning",
                f"{number}-{year}",
                text,
            )
        # A source can say "تحديث 003-26/001 ... UKMTO" without repeating
        # UKMTO immediately before the number.  The regex itself requires the
        # literal update/warning introducer, so calendar dates are excluded.
        for match in GENERIC_WARNING_ID_RE.finditer(text):
            number, year, _update_number = match.groups()
            add(
                f"UKMTO-WARNING-{number}-{year}",
                "warning",
                f"{number}-{year}",
                text,
            )
        for match in UKMTO_REPORT_RE.finditer(text):
            add(f"UKMTO-REPORT-{match.group(1)}", "incident", match.group(1), text)
        for match in JMIC_RE.finditer(text):
            number, year = match.groups()
            evidence = f"{number}-{year}" if year else number
            add(f"JMIC-ADVISORY-{number}-{year or ''}", "advisory", evidence, text)
        for match in NAVAREA_RE.finditer(text):
            add(f"NAVAREA-{match.group(1)}-{match.group(2)}", "incident", match.group(0), text)
        for match in MSCIO_RE.finditer(text):
            add(f"MSCIO-{match.group(1)}-{match.group(2)}", "incident", match.group(0), text)
        for match in INCIDENT_RE.finditer(text):
            raw = match.group(0)
            add(f"INCIDENT-{raw.upper().replace(' ', '-')}", "incident", raw, text)
        for match in GENERIC_INCIDENT_RE.finditer(text):
            add(f"INCIDENT-{match.group(1)}", "incident", match.group(1), text)
        for match in IMO_RE.finditer(text):
            add(f"IMO-{match.group(1)}", "imo_official", f"IMO {match.group(1)}", text)
        if _field_name == "imo_number" and text.isdigit() and len(text) == 7:
            add(f"IMO-{text}", "imo_official", f"IMO {text}", text)

    return list(found.values())


def source_family(data: dict[str, Any]) -> str:
    """Return a conservative organization family from the recorded source label."""
    raw = normalize_space(text_value(data.get("source")))
    folded = raw.casefold()
    if not raw:
        return ""
    # Composite labels name the independent publisher first; preserve that
    # distinction for cross-source duplicate checks.
    if any(token in folded for token in ("سنغافوري", "singapore")):
        return "سنغافورة"
    if any(token in folded for token in ("الهندية", "india")):
        return "الهند"
    if any(token in folded for token in ("رويترز", "reuters")):
        return "رويترز"
    if "maritime executive" in folded:
        return "maritime executive"
    if "mscio.eu" in folded or re.search(r"\bmscio\b", folded):
        return "MSCIO"
    if "jmic" in folded:
        return "JMIC"
    if "ukmto" in folded or "uk_mto" in folded:
        return "UKMTO"
    if "imo.org" in folded or re.search(r"\bimo\b", folded):
        return "IMO"
    if "navarea" in folded:
        return "NAVAREA"
    return folded


def class_family(data: dict[str, Any]) -> str:
    raw = normalize_space(text_value(data.get("class")))
    if not raw:
        return ""
    first_segment = normalize_space(re.split(r"[/—–,:·]", raw, maxsplit=1)[0])
    return first_segment.split()[0].casefold()


def extract_sequence_refs(data: dict[str, Any]) -> list[SequenceEvidence]:
    found: dict[tuple[str, str, int, str | None, int | None, bool], SequenceEvidence] = {}
    row_source_family = source_family(data)

    def add(item: SequenceEvidence) -> None:
        key = (item.issuer, item.series, item.number, item.year, item.suffix, item.update_marker)
        found.setdefault(key, item)

    for _field_name, text in source_fields(data):
        if not text:
            continue
        for match in UKMTO_SEQUENCE_RE.finditer(text):
            number, year, suffix = match.groups()
            add(
                SequenceEvidence(
                    issuer="UKMTO",
                    series="UKMTO-WARNING",
                    number=int(number),
                    year=year,
                    suffix=int(suffix) if suffix else None,
                    update_marker=suffix is not None,
                    evidence=match.group(0).strip(),
                )
            )
        for match in JMIC_SEQUENCE_RE.finditer(text):
            number, year = match.groups()
            raw_match = match.group(0).strip()
            add(
                SequenceEvidence(
                    issuer="JMIC",
                    series="JMIC-ADVISORY",
                    number=int(number),
                    year=year,
                    suffix=None,
                    update_marker=bool(re.search(r"(?i)update|تحديث", raw_match)),
                    evidence=raw_match,
                )
            )
        for match in JMIC_ARABIC_UPDATE_RE.finditer(text):
            number, year = match.groups()
            add(
                SequenceEvidence(
                    issuer="JMIC",
                    series="JMIC-ADVISORY",
                    number=int(number),
                    year=year,
                    suffix=None,
                    update_marker=True,
                    evidence=match.group(0).strip(),
                )
            )
        for match in MSCIO_SEQUENCE_RE.finditer(text):
            number, year = match.groups()
            raw_match = match.group(0).strip()
            add(
                SequenceEvidence(
                    issuer="MSCIO",
                    series="MSCIO-UPDATE",
                    number=int(number),
                    year=year,
                    suffix=None,
                    update_marker=bool(re.search(r"(?i)update|تحديث", raw_match)),
                    evidence=raw_match,
                )
            )
        for match in GENERIC_UPDATED_SEQUENCE_RE.finditer(text):
            number, year, suffix = match.groups()
            if row_source_family != "UKMTO":
                continue
            add(
                SequenceEvidence(
                    issuer="UKMTO",
                    series="UKMTO-WARNING",
                    number=int(number),
                    year=year,
                    suffix=int(suffix),
                    update_marker=True,
                    evidence=match.group(0).strip(),
                )
            )
    return list(found.values())


def extract_imo_numbers(data: dict[str, Any]) -> set[str]:
    values = [text_value(data.get(name)) for name in ("imo_number", "vessel_name", "title", "source_excerpt", "official_ref")]
    numbers: set[str] = set()
    for value in values:
        numbers.update(match.group(1) for match in IMO_RE.finditer(value))
        # Some structured rows keep only the seven digits in imo_number.
        if value.isdigit() and len(value) == 7:
            numbers.add(value)
    return numbers


def extract_vessel_name(data: dict[str, Any]) -> str | None:
    raw = normalize_space(text_value(data.get("vessel_name")))
    return raw or None


def extract_signals(data: dict[str, Any]) -> list[str]:
    excerpt = text_value(data.get("source_excerpt"))
    return [label for label, pattern in EXPLICIT_SIGNAL_PATTERNS if pattern.search(excerpt)]


def load_rows(root: Path) -> tuple[list[Path], list[Row], int]:
    daily = root / "cumulative-2026" / "daily"
    files = sorted(daily.glob("*.json"))
    if not files:
        raise LedgerError(f"no daily JSON files found under {daily}")
    rows: list[Row] = []
    no_code = 0
    seen_codes: dict[str, Row] = {}
    for file_order, path in enumerate(files):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LedgerError(f"cannot read JSON {path}: {exc}") from exc
        if not isinstance(payload, list):
            raise LedgerError(f"ledger file is not a list: {path}")
        for row_index, data in enumerate(payload):
            if not isinstance(data, dict):
                raise LedgerError(f"row is not an object: {path}:{row_index + 1}")
            row_date = date_from_row(path, data)
            raw_code = data.get("code")
            code = normalize_space(text_value(raw_code)) or None
            if code is None:
                no_code += 1
            elif code in seen_codes:
                other = seen_codes[code]
                raise LedgerError(
                    f"duplicate code {code!r} in {other.path}:{other.row_index + 1} and {path}:{row_index + 1}"
                )
            row = Row(
                path=path,
                file_order=file_order,
                row_index=row_index,
                data=data,
                date=row_date,
                order=(row_date, path.name, row_index),
                code=code,
                refs=extract_refs(data),
                imo_numbers=extract_imo_numbers(data),
                vessel_name=extract_vessel_name(data),
                signals=extract_signals(data),
                sequence_refs=extract_sequence_refs(data),
            )
            rows.append(row)
            if code is not None:
                seen_codes[code] = row
    rows.sort(key=lambda item: item.order)
    return files, rows, no_code


def basis_for_ref(family: str) -> str:
    if family == "warning":
        return "رقم تحذير مشترك"
    if family == "advisory":
        return "معرّف نشرة مشترك"
    if family == "imo_official":
        return "معرّف IMO مشترك"
    return "معرّف واقعة مشترك"


def relation_candidates(current: Row, prior_rows: list[Row]) -> list[Candidate]:
    by_code: dict[str, Candidate] = {}
    prior_by_ref: dict[str, list[tuple[Row, RefEvidence]]] = collections.defaultdict(list)
    for prior in prior_rows:
        for ref in prior.refs:
            prior_by_ref[ref.key].append((prior, ref))

    current_source_family = source_family(current.data)
    current_class_family = class_family(current.data)

    # Same-source explicit updates retain the original literal route.  A
    # shared identifier alone is not enough: cross-source duplicates are
    # handled separately below and are limited to three calendar days.
    for ref in current.refs:
        for prior, _prior_ref in prior_by_ref.get(ref.key, []):
            if prior.code is None:
                continue
            if current_source_family != source_family(prior.data):
                continue
            if not (ref.update_marker or current.signals):
                continue
            candidate = Candidate(
                row=prior,
                basis=basis_for_ref(ref.family),
                evidence=ref.evidence,
                priority=2,
                provenance="official_ref_update",
            )
            previous = by_code.get(prior.code)
            if previous is None or candidate.priority < previous.priority:
                by_code[prior.code] = candidate

    # Pass 2a: a directly numbered update must point to the immediately
    # preceding number/suffix from the same source and class family.
    for current_ref in current.sequence_refs:
        if not current_ref.update_marker:
            continue
        expected_suffix = (
            None
            if current_ref.suffix == 1
            else current_ref.suffix - 1
            if current_ref.suffix is not None
            else None
        )
        expected_number = current_ref.number if current_ref.suffix is not None else current_ref.number - 1
        for prior in prior_rows:
            if prior.code is None:
                continue
            if (source_family(prior.data), class_family(prior.data)) != (
                current_source_family,
                current_class_family,
            ):
                continue
            for prior_ref in prior.sequence_refs:
                if (
                    prior_ref.issuer != current_ref.issuer
                    or prior_ref.series != current_ref.series
                    or prior_ref.number != expected_number
                    or prior_ref.suffix != expected_suffix
                    or (current_ref.year and prior_ref.year and current_ref.year != prior_ref.year)
                ):
                    continue
                common_match = re.search(
                    r"(?<!\d)(\d{1,3}[-/]\d{2,4})(?!\d)", current_ref.evidence
                )
                common_number = common_match.group(1) if common_match else str(current_ref.number)
                candidate = Candidate(
                    row=prior,
                    basis="تسلسل رقمي من الجهة نفسها",
                    evidence=common_number,
                    priority=0,
                    provenance="sequence",
                )
                previous = by_code.get(prior.code)
                if previous is None or candidate.priority < previous.priority:
                    by_code[prior.code] = candidate

    # Pass 2b: an identical official identifier from an independent source
    # is a duplicate only when the source families differ and dates are close.
    for ref in current.refs:
        for prior, _prior_ref in prior_by_ref.get(ref.key, []):
            if prior.code is None or abs((current.date - prior.date).days) > 3:
                continue
            if not current_source_family or current_source_family == source_family(prior.data):
                continue
            candidate = Candidate(
                row=prior,
                basis="معرّف رسمي مشترك بين مصدرين",
                evidence=ref.evidence,
                priority=1,
                provenance="official_duplicate",
            )
            previous = by_code.get(prior.code)
            if previous is None or candidate.priority < previous.priority:
                by_code[prior.code] = candidate

    # Existing literal IMO/name routes remain exact-match routes, not text
    # similarity.  They are retained for backwards compatibility.
    for prior in prior_rows:
        if prior.code is None or current.data.get("class") != prior.data.get("class"):
            continue
        distance = abs((current.date - prior.date).days)
        if distance > 7:
            continue
        shared_imos = sorted(current.imo_numbers & prior.imo_numbers)
        for imo in shared_imos:
            candidate = Candidate(
                row=prior,
                basis="معرّف IMO مشترك",
                evidence=f"IMO {imo}",
                priority=3,
                provenance="imo",
            )
            previous = by_code.get(prior.code)
            if previous is None or candidate.priority < previous.priority:
                by_code[prior.code] = candidate
        if current.vessel_name and prior.vessel_name:
            if current.vessel_name.casefold() == prior.vessel_name.casefold():
                candidate = Candidate(
                    row=prior,
                    basis="اسم سفينة وتاريخ",
                    evidence=current.vessel_name,
                    priority=4,
                    provenance="vessel_name",
                )
                previous = by_code.get(prior.code)
                if previous is None or candidate.priority < previous.priority:
                    by_code[prior.code] = candidate

    # Pass 2c: explicit branch/extension language plus a shared IMO or exact
    # vessel name within fourteen days proves a dependent branch.
    current_text = " ".join(
        text_value(current.data.get(name)) for name in ("source_excerpt", "title", "official_ref")
    )
    branch_match = EXPLICIT_BRANCH_RE.search(current_text)
    if branch_match:
        for prior in prior_rows:
            if prior.code is None or abs((current.date - prior.date).days) > 14:
                continue
            shared_imos = sorted(current.imo_numbers & prior.imo_numbers)
            shared_vessel = bool(
                current.vessel_name
                and prior.vessel_name
                and current.vessel_name.casefold() == prior.vessel_name.casefold()
            )
            if not shared_imos and not shared_vessel:
                continue
            identifier = f"IMO {shared_imos[0]}" if shared_imos else current.vessel_name
            explicit_phrase = branch_match.group(0)
            if re.search(r"(?i)فرع من|branch\s+from", explicit_phrase):
                branch_basis = "نصّ صريح: فرع من"
            elif re.search(r"(?i)السفينة ذاتها|same\s+vessel", explicit_phrase):
                branch_basis = "نصّ صريح: السفينة ذاتها"
            elif re.search(r"(?i)الحادثة ذاتها|same\s+incident", explicit_phrase):
                branch_basis = "نصّ صريح: الحادثة ذاتها"
            else:
                branch_basis = "سفينة واحدة وتاريخ قريب"
            candidate = Candidate(
                row=prior,
                basis=branch_basis,
                # Basis phrases explain the rule; evidence contains only the
                # literal identifier that must be present in source fields.
                evidence=identifier,
                priority=1,
                provenance="explicit_branch",
            )
            previous = by_code.get(prior.code)
            if previous is None or candidate.priority < previous.priority:
                by_code[prior.code] = candidate
    return list(by_code.values())


def classify(current: Row, candidates: list[Candidate]) -> tuple[str, Candidate | None, str | None]:
    # No code is a hard stop for relationships, even if evidence exists.
    if current.code is None:
        return "جديد", None, "لا يوجد code"
    if len(candidates) != 1:
        if len(candidates) > 1:
            return "جديد", None, "أكثر من هدف أقدم مطابق؛ الهدف غير وحيد"
        return "جديد", None, "لا يوجد هدف أقدم مطابق"
    candidate = candidates[0]
    if candidate.provenance == "sequence":
        return "تحديث", candidate, None
    if candidate.provenance == "official_duplicate":
        return "تكرار", candidate, None
    if candidate.provenance == "explicit_branch":
        return "فرع تابع", candidate, None
    if "فرع من" in current.signals or "branch" in current.signals:
        return "فرع تابع", candidate, None
    if any(signal in current.signals for signal in ("تحديث", "update", "previously", "كما ورد سابقًا", "المذكور أعلاه", "متابعة", "سبق أن")):
        return "تحديث", candidate, None
    if any(ref.update_marker for ref in current.refs):
        return "تحديث", candidate, None
    if candidate.provenance == "official_ref_update":
        return "تحديث", candidate, None
    # A vessel identifier proves a related branch but, without a literal
    # update/duplicate statement, cannot prove that the report is identical.
    return "فرع تابع", candidate, None


def annotate(rows: list[Row]) -> tuple[dict[tuple[str, int], dict[str, Any]], list[dict[str, Any]]]:
    planned: dict[tuple[str, int], dict[str, Any]] = {}
    unmatched_signals: list[dict[str, Any]] = []
    prior_rows: list[Row] = []
    for current in rows:
        data = dict(current.data)
        for field_name in DERIVED_FIELDS:
            data.pop(field_name, None)
        for field_name in RELATION_FIELDS:
            data[field_name] = None
        candidates = relation_candidates(current, prior_rows)
        event_kind, candidate, reason = classify(current, candidates)
        data["event_kind"] = event_kind
        if candidate is not None and candidate.row.code is not None:
            field_name = {
                "تحديث": "update_of",
                "فرع تابع": "parent_id",
                "تكرار": "duplicate_of",
            }[event_kind]
            data[field_name] = candidate.row.code
            if candidate.provenance in {"sequence", "official_duplicate", "explicit_branch"}:
                basis = candidate.basis
            else:
                basis = candidate.basis
            if event_kind == "تحديث" and candidate.provenance != "sequence":
                basis = f"{basis}؛ نصّ صريح: تحديث"
            elif event_kind == "فرع تابع" and ("فرع من" in current.signals or "branch" in current.signals):
                basis = "نصّ صريح: فرع من"
            data["link_basis"] = basis
            data["link_evidence"] = candidate.evidence
            data["link_status"] = "مرتبط"
        else:
            if current.signals and current.code is not None:
                data["link_basis"] = "إشارة صريحة بلا هدف وحيد"
                data["link_evidence"] = ""
                unmatched_signals.append(
                    {
                        "code": current.code,
                        "date": current.date.isoformat(),
                        "signals": current.signals,
                        "reason": reason,
                        "candidate_codes": [candidate.row.code for candidate in candidates if candidate.row.code],
                    }
                )
            else:
                data["link_basis"] = "لا دليل رابط"
                data["link_evidence"] = ""
            data["link_status"] = "غير مرتبط"
        data["counts_as_new"] = event_kind != "تكرار"
        # Derived fields are always appended in the same order.  All existing
        # non-derived fields retain their values; this also makes the second
        # run byte-for-byte stable.
        planned[current.row_key] = data
        prior_rows.append(current)
    return planned, unmatched_signals


def validate_planned(rows: list[Row], planned: dict[tuple[str, int], dict[str, Any]]) -> None:
    by_code: dict[str, Row] = {row.code: row for row in rows if row.code is not None}
    references: dict[str, str] = {}
    for row in rows:
        data = planned[row.row_key]
        missing_fields = [field_name for field_name in DERIVED_FIELDS if field_name not in data]
        if missing_fields:
            raise LedgerError(f"missing derived fields for {row.code}: {missing_fields}")
        event_kind = data.get("event_kind")
        if event_kind not in ALLOWED_EVENT_KINDS:
            raise LedgerError(f"invalid event_kind for {row.code}: {event_kind!r}")
        if data.get("counts_as_new") is not (event_kind != "تكرار"):
            raise LedgerError(f"counts_as_new mismatch for {row.code}")
        relation_values = [(field_name, data.get(field_name)) for field_name in RELATION_FIELDS if data.get(field_name) is not None]
        if len(relation_values) > 1:
            raise LedgerError(f"more than one relationship field for {row.code}")
        if data.get("link_status") == "مرتبط" and len(relation_values) != 1:
            raise LedgerError(f"linked row has no single target: {row.code}")
        if data.get("link_status") == "غير مرتبط" and relation_values:
            raise LedgerError(f"unlinked row has a relationship target: {row.code}")
        expected_field = {
            "تحديث": "update_of",
            "فرع تابع": "parent_id",
            "تكرار": "duplicate_of",
        }.get(event_kind)
        if data.get("link_status") == "مرتبط" and expected_field and not data.get(expected_field):
            raise LedgerError(f"event kind has wrong relationship field for {row.code}: {expected_field}")
        if row.code is None and relation_values:
            raise LedgerError("row without code received a relationship")
        if relation_values:
            field_name, target = relation_values[0]
            if not isinstance(target, str) or target not in by_code:
                raise LedgerError(f"{field_name} target is not an existing code for {row.code}: {target!r}")
            target_row = by_code[target]
            if not (target_row.order < row.order):
                raise LedgerError(f"{field_name} target is not older for {row.code}: {target}")
            if target == row.code:
                raise LedgerError(f"self-reference in {field_name}: {row.code}")
            references[row.code] = target
    # Defensive cycle check, independent of the chronological check.
    for start in references:
        seen: set[str] = set()
        cursor: str | None = start
        while cursor in references:
            if cursor in seen:
                raise LedgerError(f"relationship cycle detected at {cursor}")
            seen.add(cursor)
            cursor = references[cursor]


def select_files(files: list[Path], date_arg: str | None) -> set[Path]:
    if date_arg is None:
        return set(files)
    try:
        requested = dt.date.fromisoformat(date_arg)
    except ValueError as exc:
        raise LedgerError(f"invalid --date value: {date_arg!r}; expected YYYY-MM-DD") from exc
    selected = {path for path in files if path.stem == requested.isoformat()}
    if not selected:
        raise LedgerError(f"no ledger file for --date {date_arg}")
    return selected


def write_selected(rows: list[Row], planned: dict[tuple[str, int], dict[str, Any]], selected: set[Path]) -> None:
    by_path: dict[Path, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in sorted(rows, key=lambda item: (item.path.name, item.row_index)):
        if row.path in selected:
            by_path[row.path].append(planned[row.row_key])
    for path in sorted(by_path):
        try:
            text = json.dumps(by_path[path], ensure_ascii=False, indent=1) + "\n"
            path.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise LedgerError(f"cannot write {path}: {exc}") from exc


def summary(rows: list[Row], planned: dict[tuple[str, int], dict[str, Any]], selected: set[Path], unmatched: list[dict[str, Any]]) -> dict[str, Any]:
    selected_rows = [row for row in rows if row.path in selected]
    event_counts = collections.Counter(planned[row.row_key]["event_kind"] for row in selected_rows)
    basis_counts = collections.Counter(
        planned[row.row_key]["link_basis"]
        for row in selected_rows
        if planned[row.row_key]["link_status"] == "مرتبط"
    )
    linked = sum(planned[row.row_key]["link_status"] == "مرتبط" for row in selected_rows)
    no_code = sum(row.code is None for row in selected_rows)
    selected_codes = {row.code for row in selected_rows}
    selected_unmatched = [item for item in unmatched if item["code"] in selected_codes]
    return {
        "files_processed": len(selected),
        "rows_processed": len(selected_rows),
        "event_kind_counts": {kind: event_counts.get(kind, 0) for kind in ALLOWED_EVENT_KINDS},
        "linked_rows": linked,
        "link_basis_counts": dict(sorted(basis_counts.items())),
        "rows_without_code": no_code,
        "explicit_signal_unlinked_count": len(selected_unmatched),
        "explicit_signal_unlinked_examples": selected_unmatched[:20],
        "written_files": [path.name for path in sorted(selected)],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="اشتقاق حقول ربط دفتر الوقائع بدليل حرفي فقط")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="معالجة كل الأيام")
    group.add_argument("--date", metavar="YYYY-MM-DD", help="معالجة يوم واحد")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        files, rows, _all_no_code = load_rows(root)
        selected = select_files(files, None if args.all else args.date)
        planned, unmatched = annotate(rows)
        validate_planned(rows, planned)
        write_selected(rows, planned, selected)
        print(json.dumps(summary(rows, planned, selected, unmatched), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except LedgerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # Real unexpected failures also fail closed.
        print(f"ERROR: unexpected failure: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
