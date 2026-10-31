#!/usr/bin/env python3
"""بوابة أمانة بطاقات العدادات: السجل هو مصدر العقد الوحيد والفشل مغلق."""
from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "appendices" / "card_registry.json"


def _default_dist_root() -> Path:
    site = os.environ.get("SITE_DIR")
    if site:
        return Path(site) / "dist"
    return ROOT.parent.parent / "seawatch" / "dist"


class Node:
    def __init__(self, tag="root", attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []

    def text(self):
        return " ".join(c if isinstance(c, str) else c.text() for c in self.children).strip()


class TreeParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag.lower(), attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if node.tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack[-1].tag == tag.lower():
            self.stack.pop()

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].children.append(data)


def parse_document(source: str) -> Node:
    parser = TreeParser()
    parser.feed(source)
    parser.close()
    return parser.root


def _nodes(node: Node, tag: str | None = None):
    out = []
    for child in node.children:
        if isinstance(child, Node):
            if tag is None or child.tag == tag:
                out.append(child)
            out.extend(_nodes(child, tag))
    return out


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(value or "")).strip()


def _load_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def load_registry(path: Path | None = None) -> dict:
    """Load and minimally validate the one declarative card registry."""
    registry_path = path or DEFAULT_REGISTRY
    registry = _load_json(registry_path)
    if not registry or not isinstance(registry.get("cards"), list):
        raise ValueError(f"سجل البطاقات مفقود أو غير صالح: {registry_path}")
    for card in registry["cards"]:
        if not isinstance(card, dict) or not card.get("id") or not isinstance(card.get("counters"), list):
            raise ValueError(f"سجل البطاقات يحوي بطاقة بلا id أو counters: {registry_path}")
        status = card.get("status") or {}
        if status.get("state") not in {"enabled", "disabled"}:
            raise ValueError(f"حالة بطاقة غير معتمدة: {card.get('id')}")
        component = card.get("page_component") or {}
        if not component.get("class") or not component.get("aria_label"):
            raise ValueError(f"بطاقة بلا مكوّن أو aria_label: {card.get('id')}")
        if status.get("state") == "enabled" and not card["counters"]:
            raise ValueError(f"بطاقة مفعّلة بلا مفاتيح عدادات: {card.get('id')}")
    return registry


def _load_title_map(glossary_path: Path | None = None) -> dict[str, str]:
    if glossary_path is None or not glossary_path.is_file():
        return {}
    data = _load_json(glossary_path) or {}
    entries = data.get("entries", {})
    return {_norm(str(k)): _norm(str(v)) for k, v in entries.items() if str(k).strip() and str(v).strip()}


def _same_title(left: str, right: str, lang: str = "ar", title_map: dict[str, str] | None = None) -> bool:
    left_n, right_n = _norm(left), _norm(right)
    if left_n == right_n or (lang == "en" and left_n.casefold() == right_n.casefold()):
        return True
    if lang != "en" or not title_map:
        return False
    return (title_map.get(left_n, left_n).casefold() == right_n.casefold()
            or title_map.get(right_n, right_n).casefold() == left_n.casefold())


def _lang(root: Node) -> str:
    html_node = next(iter(_nodes(root, "html")), None)
    return ((html_node.attrs.get("lang") if html_node else "") or "ar").lower()


def _find_id(root: Node, ident: str) -> Node | None:
    return next((node for node in _nodes(root) if node.attrs.get("id") == ident), None)


def _find_heading(root: Node, title: str, tags=("h2", "h3", "h4"), lang="ar", title_map=None) -> Node | None:
    for tag in tags:
        for node in _nodes(root, tag):
            if _same_title(node.text(), title, lang, title_map):
                return node
    return None


def _count_list(node: Node) -> int:
    lists = _nodes(node, "ul") + _nodes(node, "ol")
    return sum(1 for li in _nodes(lists[0], "li")) if lists else 0


def _count_table_rows(node: Node) -> int:
    tables = _nodes(node, "table")
    if not tables:
        return 0
    bodies = _nodes(tables[0], "tbody")
    if bodies:
        return len(_nodes(bodies[0], "tr"))
    return max(0, len(_nodes(tables[0], "tr")) - 1)


def _count_heading_list(heading: Node) -> int:
    direct_lists = _nodes(heading, "ul") + _nodes(heading, "ol")
    if direct_lists:
        return sum(1 for li in _nodes(direct_lists[0], "li"))
    parent = heading.parent
    if not parent:
        return 0
    try:
        start = parent.children.index(heading) + 1
    except ValueError:
        return 0
    for child in parent.children[start:]:
        if isinstance(child, str):
            continue
        if child.tag in {"h2", "h3", "h4"}:
            break
        lists = ([child] if child.tag in {"ul", "ol"} else []) + _nodes(child, "ul") + _nodes(child, "ol")
        if lists:
            return sum(1 for li in _nodes(lists[0], "li"))
    return 0


def _arabic_counter(text: str) -> tuple[int, str] | None:
    value = _norm(text)
    patterns = (
        (r"(?:^|\s)لا\s+(بنود|تحذيرات)(?=\s|$|·)", 0),
        (r"(?:^|\s)(بند|تحذير)\s+واحد(?=\s|$|·)", 1),
        (r"(?:^|\s)(بندان|تحذيران)(?=\s|$|·)", 2),
        (r"(?:^|\s)([3-9]\d*)\s+(بنود|تحذيرات)(?=\s|$|·)", None),
    )
    for pattern, fixed in patterns:
        match = re.search(pattern, value)
        if not match:
            continue
        if fixed in (0, 1):
            noun = match.group(1)
        elif fixed is not None:
            noun = "بنود" if match.group(1) == "بندان" else match.group(1)
        else:
            noun = match.group(2)
        kind = "items" if noun in {"بند", "بندان", "بنود"} else "warnings" if noun in {"تحذير", "تحذيران", "تحذيرات"} else None
        return (fixed if fixed is not None else int(match.group(1)), kind) if kind else None
    return None


def _counter(text: str, lang: str) -> int | None:
    if lang == "en":
        match = re.search(r"\b(\d+)\s+(?:items?|rows?)\b", _norm(text), re.I)
        return int(match.group(1)) if match else None
    parsed = _arabic_counter(text)
    return parsed[0] if parsed else None


def _counter_kind(text: str, lang: str) -> str | None:
    parsed = _arabic_counter(text) if lang != "en" else None
    return parsed[1] if parsed else None


def _component_label(card: dict, lang: str) -> str:
    component = card["page_component"]
    return component.get("aria_label_en") if lang == "en" else component["aria_label"]


def _class_nodes(root: Node, class_name: str) -> list[Node]:
    return [node for node in _nodes(root) if class_name in node.attrs.get("class", "").split()]


def _resolve_components(root: Node, cards: list[dict], lang: str, title_map: dict[str, str]) -> tuple[dict[str, Node], list[str]]:
    errors: list[str] = []
    resolved: dict[str, Node] = {}
    registered_classes = {c["page_component"]["class"] for c in cards}
    for card in cards:
        component = card["page_component"]
        candidates = _class_nodes(root, component["class"])
        expected = _component_label(card, lang)
        matches = [node for node in candidates if _same_title(node.attrs.get("aria-label", ""), expected, lang, title_map)]
        if not matches or (len(matches) > 1 and not component.get("allow_multiple")):
            if not candidates:
                errors.append(f"{lang}: البطاقة المسجّلة {card['id']} مفقودة من الصفحة")
            else:
                errors.append(f"{lang}: البطاقة المسجّلة {card['id']} غير موجودة مرة واحدة")
            continue
        resolved[card["id"]] = matches
    for class_name in registered_classes:
        for node in _class_nodes(root, class_name):
            if not any(node is value for values in resolved.values() for value in values):
                errors.append(f"{lang}: بطاقة في الصفحة غير مسجلة: {node.attrs.get('aria-label', '') or class_name}")
    return resolved, errors


def _unknown_latin(text: str, allowlist: list[str]) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", text)
    allowed = {str(x).casefold() for x in allowlist}
    return sorted({token for token in tokens if token.casefold() not in allowed})


def _card_rows(card: Node, lang: str):
    rows = []
    for row in _nodes(card):
        if "sc-row" not in row.attrs.get("class", "").split():
            continue
        labels = [node for node in _nodes(row) if "sc-l" in node.attrs.get("class", "").split()]
        more = [node for node in _nodes(row) if "sc-more" in node.attrs.get("class", "").split()]
        links = _nodes(more[0], "a") if more else []
        rows.append({
            "label": _norm(labels[0].text()) if labels else "",
            "more": _norm(more[0].text()) if more else "",
            "count": _counter(more[0].text() if more else "", lang),
            "counter_kind": _counter_kind(more[0].text() if more else "", lang),
            "text": _norm(row.text()),
            "href": (links[0].attrs.get("href") or "") if links else "",
            "goto": (links[0].attrs.get("data-goto") or "") if links else "",
        })
    return rows


def _target_for_href(href: str, ar_report: Node, ar_additions: Node, en_report: Node | None, en_additions: Node | None, lang: str) -> Node:
    if "additions" in href.split("#", 1)[0]:
        return en_additions if lang == "en" and en_additions is not None else ar_additions
    return en_report if lang == "en" and en_report is not None else ar_report


def _target_title(counter: dict, lang: str) -> str:
    return counter.get("target", {}).get("title_en" if lang == "en" else "title", "")


def _validate_news_card(card: dict, node: Node, report: Node, additions: Node, ar_report: Node, ar_additions: Node,
                        lang: str, title_map: dict[str, str]) -> list[str]:
    errors: list[str] = []
    counters = card["counters"]
    rows = _card_rows(node, lang)
    if len(rows) != len(counters):
        errors.append(f"{lang}: بطاقة {card['id']} تحوي {len(rows)} صفوف؛ الملزم {len(counters)}")
    expected_labels = {c["key"]: (c.get("row_label_en") if lang == "en" else c.get("row_label", "")) for c in counters}
    for counter in counters:
        key = counter["key"]
        label = expected_labels[key]
        matches = [row for row in rows if row["label"] == label]
        if len(matches) != 1:
            errors.append(f"{lang}: مفتاح مطلوب مفقود أو مكرر في بطاقة {card['id']}: {key}")
            continue
        row = matches[0]
        expected_kind = counter.get("format", {}).get("en" if lang == "en" else "ar")
        if row["count"] is None:
            errors.append(f"{lang}: عداد {key} غير مقروء")
        if lang != "en" and row["counter_kind"] != expected_kind:
            errors.append(f"{lang}: صياغة عداد {label} غير مطابقة للعدد العربي المعتمد")
        unknown = _unknown_latin(row["text"], card.get("latin_allowlist", [])) if lang == "ar" else []
        if unknown:
            errors.append(f"{lang}: نص بحروف لاتينية متصلة داخل صف {label} خارج المسموح: {', '.join(unknown)}")
        href = row["href"]
        if "#" not in href:
            errors.append(f"{lang}: مرساة {label} بلا جزء معرف: {href}")
            continue
        frag = href.split("#", 1)[1]
        target = _target_for_href(href, ar_report, ar_additions, report if lang == "en" else None, additions if lang == "en" else None, lang)
        target_node = _find_id(target, frag)
        if target_node is None:
            errors.append(f"{lang}: مرساة {label} غير موجودة: #{frag}")
            continue
        title = _target_title(counter, lang)
        measurement = counter.get("target", {}).get("measurement")
        if measurement == "list_items":
            if key == "watch" and target_node.tag in {"h2", "h3", "h4"}:
                target_heading = target_node if _same_title(target_node.text(), title, lang, title_map) else None
            else:
                target_heading = next((n for n in _nodes(target_node, "h2") if _same_title(n.text(), title, lang, title_map)), None)
            measured = _count_heading_list(target_heading) if key == "watch" and target_heading else _count_list(target_node)
        elif measurement == "table_body_rows":
            target_heading = _find_heading(target_node if target_node.tag == "section" else target_node, title, ("h2",), lang, title_map)
            measured = _count_table_rows(target_node)
            if not _nodes(target_node, "table"):
                errors.append(f"{lang}: قسم {title} ليس جدولًا")
        else:
            target_heading = None
            measured = 0
        if target_heading is None:
            errors.append(f"{lang}: عنوان الهدف لا يطابق {label}: {title}")
        if key == "watch" and target_heading is not target_node:
            errors.append(f"{lang}: مرساة {label} لا تهبط مباشرة على عنوان الهدف «{title}»: {frag}")
        if row["count"] != measured:
            errors.append(f"{lang}: {label} ({key}) عداد البطاقة={row['count']} والهدف={measured}")
        if row["goto"] and not _same_title(row["goto"], title, lang, title_map):
            errors.append(f"{lang}: مرساة {label} بعنوان غير مطابق: {row['goto']} ≠ {title}")
    card_text = _norm(node.text())
    if "خلال 24 ساعة السابقة" in card_text or "over the previous 24 hours" in card_text:
        errors.append(f"{lang}: لفظ الفترة السابقة تسرب إلى بطاقة الفروع")
    if lang == "en" and re.search(r"[\u0600-\u06FF]", card_text):
        errors.append("en: نص عربي متسرب داخل بطاقة الفروع")
    return errors


def _nested_get(data: dict, path: str):
    value = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _validate_zone_card(card: dict, node: Node, lang: str, zones_data: dict | None, title_map: dict[str, str]) -> list[str]:
    errors: list[str] = []
    title = card["target_section"].get("title_en" if lang == "en" else "title", "")
    heading = _find_heading(node, title, ("h3", "h2"), lang, title_map)
    if heading is None:
        errors.append(f"{lang}: مرساة بطاقة القطاعات لا تطابق عنوانها: {title}")
    if zones_data is None:
        return errors + [f"{lang}: مصدر عدادات بطاقة القطاعات مفقود"]
    count_nodes = [n for n in _nodes(node) if "tz-count" in n.attrs.get("class", "").split()]
    if len(count_nodes) != 1:
        return errors + [f"{lang}: مفتاح عدادات بطاقة القطاعات مفقود أو مكرر"]
    count_text = _norm(count_nodes[0].text())
    for counter in card["counters"]:
        key = counter["key"]
        label = counter.get("display_label_en" if lang == "en" else "display_label", "")
        match = re.search(rf"(?<![\w-]){re.escape(label)}\s+(\d+)(?!\d)", count_text, re.I if lang == "en" else 0)
        if not match:
            errors.append(f"{lang}: مفتاح مطلوب مفقود في بطاقة القطاعات: {key}")
            continue
        actual = int(match.group(1))
        expected = _nested_get(zones_data, counter["source_path"])
        if not isinstance(expected, int):
            errors.append(f"{lang}: مصدر عداد {key} غير صالح")
        elif actual != expected:
            errors.append(f"{lang}: sector {key} عداد البطاقة={actual} والمصدر={expected}")
    unknown = _unknown_latin(_norm(node.text()), card.get("latin_allowlist", [])) if lang == "ar" else []
    if unknown:
        errors.append(f"{lang}: نص بحروف لاتينية متصلة داخل بطاقة القطاعات خارج المسموح: {', '.join(unknown)}")
    if lang == "en" and re.search(r"[\u0600-\u06FF]", _norm(node.text())):
        errors.append("en: نص عربي متسرب داخل بطاقة القطاعات")
    return errors


def validate_one(report_html: str, additions_html: str, *, ar_report_html: str | None = None,
                 ar_additions_html: str | None = None, title_map: dict[str, str] | None = None,
                 registry: dict | None = None, zones_data: dict | None = None) -> list[str]:
    report = parse_document(report_html)
    additions = parse_document(additions_html)
    lang = _lang(report)
    ar_report = parse_document(ar_report_html) if ar_report_html else report
    ar_additions = parse_document(ar_additions_html) if ar_additions_html else additions
    cards = [card for card in (registry or {}).get("cards", []) if (card.get("status") or {}).get("state") == "enabled"]
    resolved, errors = _resolve_components(report, cards, lang, title_map or {})
    for card in cards:
        nodes = resolved.get(card["id"], [])
        if not nodes:
            continue
        component_class = card["page_component"]["class"]
        for node in nodes:
            if component_class == "sc-card":
                errors.extend(_validate_news_card(card, node, report, additions, ar_report, ar_additions, lang, title_map or {}))
            elif component_class == "tz":
                errors.extend(_validate_zone_card(card, node, lang, zones_data, title_map or {}))
            else:
                errors.append(f"{lang}: مكوّن بطاقة غير معتمد في السجل: {component_class}")
    return errors


def validate_card_documents(*, ar_report: str, ar_additions: str, en_report: str | None = None,
                             en_additions: str | None = None, glossary_path: Path | None = None,
                             registry_path: Path | None = None, zones_data: dict | None = None) -> list[str]:
    try:
        registry = load_registry(registry_path)
    except ValueError as exc:
        return [str(exc)]
    title_map = _load_title_map(glossary_path)
    errors = validate_one(ar_report, ar_additions, title_map=title_map, registry=registry, zones_data=zones_data)
    if en_report:
        errors.extend(validate_one(en_report, en_additions or ar_additions, ar_report_html=ar_report,
                                   ar_additions_html=ar_additions, title_map=title_map,
                                   registry=registry, zones_data=zones_data))
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--dist-root", default=str(_default_dist_root()))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    args = parser.parse_args(argv)
    dist = Path(args.dist_root)
    paths = [dist / "reports" / f"{args.date}.html", dist / "additions.html",
             dist / "reports" / "en" / f"{args.date}.html", dist / "reports" / "en" / "additions.html"]
    for path in paths:
        if not path.is_file():
            print(f"✘ ملف مطلوب مفقود: {path}")
            return 2
    zone_path = dist.parent / "sources" / "zones" / f"{args.date}.json"
    zones_data = _load_json(zone_path)
    errors = validate_card_documents(
        ar_report=paths[0].read_text(encoding="utf-8"), ar_additions=paths[1].read_text(encoding="utf-8"),
        en_report=paths[2].read_text(encoding="utf-8"), en_additions=paths[3].read_text(encoding="utf-8"),
        glossary_path=dist.parent / "sources" / "i18n" / "en" / "glossary.json",
        registry_path=Path(args.registry), zones_data=zones_data,
    )
    if errors:
        for error in errors:
            print(f"✘ {error}")
        return 2
    enabled = [c["id"] for c in load_registry(Path(args.registry))["cards"] if c["status"]["state"] == "enabled"]
    print(f"✔ حراسة البطاقات التصريحية: {len(enabled)} بطاقات مفعّلة ({'، '.join(enabled)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
