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
CONTRACT_LINE = "✔ بطاقة الفروع الثلاثة: العناوين والعدادات والمراسي متطابقة عربيًا وإنجليزيًا"
sys.path.insert(0, str(ROOT))
from tools.arabic_counter import format_arabic_count  # noqa: E402
def _site_root() -> Path:
    """جذر الموقع بالقياس لا بالافتراض (ك-563): البيئة أولًا ثم المرشحات الفعلية."""
    for key in ("SITE_DIR", "SITE"):
        value = (os.environ.get(key) or "").strip()
        if value and (Path(value) / "generator").is_dir():
            return Path(value)
    for cand in (Path.home() / "seawatch", ROOT.parent / "seawatch", ROOT.parent / "site"):
        if (cand / "generator").is_dir():
            return cand
    return Path.home() / "seawatch"


_SITE_GENERATOR = _site_root() / "generator"
if not _SITE_GENERATOR.is_dir():
    raise ImportError(f"مسار مولّد السطح المرسوم غير موجود: {_SITE_GENERATOR}")
sys.path.insert(0, str(_SITE_GENERATOR))
from card_measurements import measure_rendered_target as _shared_measure_rendered_target  # noqa: E402


def _default_dist_root() -> Path:
    site = os.environ.get("SITE_DIR")
    if site:
        return Path(site) / "dist"
    return ROOT.parent / "seawatch" / "dist"


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


def _has_ancestor_class(node: Node, class_name: str) -> bool:
    parent = node.parent
    while parent is not None:
        if class_name in (parent.attrs.get("class") or "").split():
            return True
        parent = parent.parent
    return False


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(value or "")).strip()


def _load_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _default_kpis_totals() -> dict:
    """مصدر المقاييس الافتراضي: يوم البيئة إن حُدد، وإلا أحدث يوم مؤرَّخ مُبنى.

    عطل (2026-11-01): كان المصدر مثبتًا على 2026-10-31 فيقارن بطاقة اليوم بمقياس يوم
    سابق ويفشل مغلقًا بلا سبب حقيقي. القاعدة الآن: لا تاريخ مثبّت داخل الحاجز.
    """
    for key in ("D", "DATE"):
        env = (os.environ.get(key) or "").strip()
        path = ROOT / "web" / "kpis-totals" / f"{env}.json"
        if env and path.exists():
            return _load_json(path) or {}
    days = sorted(x.stem for x in (ROOT / "web" / "kpis-totals").glob("*.json")
                  if re.fullmatch(r"\d{4}-\d{2}-\d{2}", x.stem))
    for day in reversed(days):
        data = _load_json(ROOT / "web" / "kpis-totals" / f"{day}.json")
        if data:
            return data
    return {}


def _metric_by_id(kpis_totals: dict, metric_id: str) -> dict | None:
    return next((metric for metric in (kpis_totals.get("metrics") or [])
                 if isinstance(metric, dict) and metric.get("id") == metric_id), None)


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
        if component.get("class") == "sc-card":
            for counter in card["counters"]:
                required = ("row_label", "row_label_en", "target_title", "surface", "measurement", "anchor_rule")
                missing = [field for field in required if field not in counter]
                if missing:
                    raise ValueError(f"عداد {card.get('id')}.{counter.get('key')} بلا حقول حاكمة: {', '.join(missing)}")
                titles = counter.get("target_title")
                if not isinstance(titles, dict) or not titles.get("ar") or not titles.get("en"):
                    raise ValueError(f"عنوان هدف عداد غير صالح: {card.get('id')}.{counter.get('key')}")
                if counter.get("surface") not in {"report", "additions"}:
                    raise ValueError(f"سطح هدف عداد غير صالح: {card.get('id')}.{counter.get('key')}")
                if counter.get("measurement") not in {"table_body_rows", "visible_items"}:
                    raise ValueError(f"قياس هدف عداد غير معتمد: {card.get('id')}.{counter.get('key')}")
                if not isinstance(counter.get("anchor_rule"), dict) or counter["anchor_rule"].get("mode") not in {"section", "heading"}:
                    raise ValueError(f"قاعدة مرساة عداد غير صالحة: {card.get('id')}.{counter.get('key')}")
    return registry


def _registry_blacklist_errors(registry_path: Path) -> list[str]:
    """حاجز فشل مغلق (ك-449): السجل الحاكم لا يجوز أن يحمل لفظًا في القائمة السوداء.

    العطل الحقيقي: سجل البطاقات حمل «التحذيرات والنشرات الرسمية» — لفظ ممنوع بقرار
    المالك 2026-11-01 — فأوقف بناء الموقع اليومي عند بوابة العدّادات بعد أن كانت
    القائمة السوداء نفسها تُعلن أن الصواب «التحذيرات والتنبيهات النشطة».
    """
    blacklist = _load_json(ROOT / "appendices" / "style-blacklist.json") or {}
    terms: list[tuple[str, str]] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            term = node.get("term")
            replacement = node.get("replacement")
            if isinstance(term, str) and term.strip() and isinstance(replacement, str) and replacement.strip():
                terms.append((term.strip(), replacement.strip()))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(blacklist)
    if not terms:
        return []
    try:
        raw = registry_path.read_text(encoding="utf-8")
    except OSError:
        return []
    return [f"سجل البطاقات يحمل لفظًا ممنوعًا: «{term}» — الصواب «{replacement}»"
            for term, replacement in terms if term in raw]


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


def _count_visible_items(node: Node) -> int:
    """Count the first visible item structure in a rendered section.

    A section may deliberately be prose rather than a table/list. In that case
    each rendered paragraph is one visible item; the gate must measure it rather
    than inventing a table requirement.
    """
    lists = _nodes(node, "ul") + _nodes(node, "ol")
    if lists:
        return sum(1 for li in _nodes(lists[0], "li"))
    tables = _nodes(node, "table")
    if tables:
        return _count_table_rows(node)
    paragraphs = []
    for paragraph in _nodes(node, "p"):
        classes = set((paragraph.attrs.get("class") or "").split())
        if classes & {"sec-lede", "src-note"}:
            continue
        if paragraph.text():
            paragraphs.append(paragraph)
    return len(paragraphs)


def _serialize_node(node: Node) -> str:
    """Serialize the already-parsed rendered target for the shared measurer."""
    if isinstance(node, str):
        return html_lib.escape(node)
    attrs = "".join(
        f' {key}="{html_lib.escape(str(value), quote=True)}"'
        for key, value in node.attrs.items()
    )
    if node.tag in TreeParser.VOID:
        return f"<{node.tag}{attrs}>"
    return f"<{node.tag}{attrs}>" + "".join(_serialize_node(child) for child in node.children) + f"</{node.tag}>"


def _measure_rendered_target(source: str | Node, measurement: str, target_id: str | None = None) -> int:
    """Use the exact site measurement function for both card and target."""
    html_source = _serialize_node(source) if isinstance(source, Node) else source
    result = _shared_measure_rendered_target(html_source, measurement, target_id)
    return int(result["count"])


def _arabic_counter(text: str) -> tuple[int, str] | None:
    value = _norm(text)
    patterns = (
        (r"(?:^|\s)لا\s+(بنود|تحذيرات)(?=\s|$|·)", 0),
        (r"(?:^|\s)(بند|تحذير)\s+واحد(?=\s|$|·)", 1),
        (r"(?:^|\s)(بندان|تحذيران)(?=\s|$|·)", 2),
        (r"(?:^|\s)([3-9]\d*|\d{2,})\s+(بنود|تحذيرات)(?=\s|$|·)", None),
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


def _component_surface(card: dict, lang: str, sections_policy: dict | None,
                        title_map: dict[str, str]) -> tuple[str | None, str | None]:
    """Resolve a registered component's surface through the governing policy."""
    component = card["page_component"]
    declared = component.get("surface")
    declared_surfaces = component.get("surfaces")
    if isinstance(declared_surfaces, list) and declared_surfaces:
        allowed = [str(x) for x in declared_surfaces if str(x) in {"report", "additions"}]
    else:
        allowed = [declared] if declared in {"report", "additions"} else []
    if not allowed:
        return None, f"{lang}: سطح البطاقة غير مسجل: {card['id']}"
    if sections_policy is None:
        if declared not in {"report", "additions"}:
            return None, f"{lang}: سطح البطاقة غير مسجل: {card['id']}"
        return declared, None

    # سياسة الأسطح حاكمة بالعناوين العربية؛ لا ننشئ خريطة سطح مستقلة للإنجليزية.
    probe = _norm(component.get("aria_label", ""))
    report_titles = [str(title) for title in sections_policy.get("required_in_report", [])]
    additions_titles = [str(title) for title in sections_policy.get("required_in_additions", [])]
    report = [title for title in report_titles if _title_matches_policy(title, probe, "ar", title_map)]
    additions = [title for title in additions_titles if _title_matches_policy(title, probe, "ar", title_map)]
    if len(report) + len(additions) != 1:
        return None, f"{lang}: سطح البطاقة غير قابل للتعيين من السياسة: {card['id']}"
    surface = "report" if report else "additions"
    if surface not in allowed:
        return surface, f"{lang}: سجل البطاقة {card['id']} يعلن سطح {declared} لكن السياسة تسنده إلى {surface}"
    return surface, None


def _component_matches(card: dict, node: Node, lang: str, title_map: dict[str, str]) -> bool:
    component = card["page_component"]
    if not _same_title(node.attrs.get("aria-label", ""), _component_label(card, lang), lang, title_map):
        return False
    # بطاقة الأخبار هي البطاقة المسجلة ذات المعرّف المرئي؛ لا تقبل مطابقة aria-label وحدها.
    if component.get("class") == "sc-card" and node.attrs.get("data-kpi-id") != card["id"]:
        return False
    return True


def _class_nodes(root: Node, class_name: str) -> list[Node]:
    return [node for node in _nodes(root) if class_name in node.attrs.get("class", "").split()]


def _resolve_components(root: Node, cards: list[dict], lang: str, title_map: dict[str, str],
                        sections_policy: dict | None = None, surface: str = "report") -> tuple[dict[str, Node], list[str]]:
    errors: list[str] = []
    resolved: dict[str, Node] = {}
    registered_classes = {c["page_component"]["class"] for c in cards}
    for card in cards:
        component = card["page_component"]
        candidates = _class_nodes(root, component["class"])
        expected_surface, surface_error = _component_surface(card, lang, sections_policy, title_map)
        if surface_error and surface == "report":
            errors.append(surface_error)
        allowed_surfaces = component.get("surfaces") if isinstance(component.get("surfaces"), list) else None
        if expected_surface != surface and allowed_surfaces and surface in allowed_surfaces:
            # سطح إضافي معلَن في السجل: حضور المكوّن فيه اختياري (نسخة طباعة/شاشة)،
            # فلا يُطالب به، وإن ظهر يُحتسب ويُمنع بقاءه بلا تسجيل.
            extra_matches = [node for node in candidates if _component_matches(card, node, lang, title_map)]
            if extra_matches:
                resolved[card["id"]] = extra_matches
            continue
        if expected_surface != surface:
            wrong_surface = [node for node in candidates if _component_matches(card, node, lang, title_map)]
            if wrong_surface:
                errors.append(f"{lang}: البطاقة المسجّلة {card['id']} ظهرت على سطح {surface}؛ السياسة تسندها إلى {expected_surface}")
            continue
        matches = [node for node in candidates if _component_matches(card, node, lang, title_map)]
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
    return (counter.get("target_title") or {}).get("en" if lang == "en" else "ar", "")


def _title_matches_policy(policy_title: str, target_title: str, lang: str,
                          title_map: dict[str, str]) -> bool:
    raw_left = _norm(policy_title)
    raw_right = _norm(target_title)
    if raw_left == raw_right or raw_left in raw_right or raw_right in raw_left:
        return True
    if lang != "en":
        return False
    left = title_map.get(raw_left, raw_left).casefold()
    right = title_map.get(raw_right, raw_right).casefold()
    return left == right or left in right or right in left


def _counter_surface(counter: dict, lang: str, sections_policy: dict | None,
                     title_map: dict[str, str]) -> tuple[str | None, str | None]:
    # تعيين السطح يتم من العنوان العربي الحاكم؛ الترجمة تخص مطابقة العنوان
    # داخل الصفحة الإنجليزية فقط، ولا يجوز أن تنشئ خريطة سطح ثانية.
    probe = (counter.get("target_title") or {}).get("ar", "")
    declared = counter.get("surface")
    if sections_policy is None:
        if declared not in {"report", "additions"}:
            return None, f"{lang}: سطح هدف العداد غير مسجل: {probe}"
        return declared, None
    report = [title for title in sections_policy.get("required_in_report", [])
              if _title_matches_policy(str(title), probe, lang, title_map)]
    additions = [title for title in sections_policy.get("required_in_additions", [])
                 if _title_matches_policy(str(title), probe, lang, title_map)]
    if len(report) + len(additions) != 1:
        return None, f"{lang}: سطح هدف العداد غير قابل للتعيين من السياسة: {probe}"
    surface = "report" if report else "additions"
    if declared and declared != surface:
        return surface, f"{lang}: سجل العداد يعلن سطح {declared} لكن السياسة تسند {probe} إلى {surface}"
    return surface, None


def _section_ancestor(node: Node) -> Node | None:
    current = node
    while current is not None:
        if current.tag == "section":
            return current
        current = current.parent
    return None


def _section_matches_title(section: Node, title: str, lang: str, title_map: dict[str, str]) -> bool:
    if _same_title(section.attrs.get("aria-label", ""), title, lang, title_map):
        return True
    return _find_heading(section, title, ("h2", "h3", "h4"), lang, title_map) is not None


def _zone_inside_target_section(node: Node, title: str, lang: str,
                                title_map: dict[str, str]) -> bool:
    # عندما يكون المكوّن نفسه عنصر section (كما في المولّد الحالي)، يكون aria-label
    # عنوان القسم. وإذا وُجد قسم خارجي، فلا يكفي عنوان المكوّن وحده: يجب أن يطابق
    # أحد أسلافه عنوان القسم المستهدف حتى لا تمر بطاقة خرجت من نطاقها.
    outer_sections = []
    current = node.parent
    while current is not None:
        if current.tag == "section":
            outer_sections.append(current)
        current = current.parent
    if outer_sections:
        return any(_section_matches_title(section, title, lang, title_map)
                   for section in outer_sections)
    return node.tag == "section" and _section_matches_title(node, title, lang, title_map)


def _validate_news_card(card: dict, node: Node, report: Node, additions: Node, ar_report: Node, ar_additions: Node,
                        lang: str, title_map: dict[str, str],
                        sections_policy: dict | None = None) -> list[str]:
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
        title = _target_title(counter, lang)
        target_surface, surface_error = _counter_surface(counter, lang, sections_policy, title_map)
        if surface_error:
            errors.append(surface_error)
        if target_surface is None:
            continue
        href = row["href"]
        if "#" not in href:
            errors.append(f"{lang}: مرساة {label} بلا جزء معرف: {href}")
            continue
        frag = href.split("#", 1)[1]
        href_surface = "additions" if "additions" in href.split("#", 1)[0] else "report"
        if href_surface != target_surface:
            errors.append(f"{lang}: مرساة {label} في سطح {href_surface} والسياسة تسندها إلى {target_surface}")
        target = (ar_additions if lang != "en" else additions) if target_surface == "additions" else (ar_report if lang != "en" else report)
        target_node = _find_id(target, frag)
        if target_node is None:
            goto = row["goto"]
            if not goto or not _same_title(goto, title, lang, title_map):
                errors.append(f"{lang}: مرساة {label} غير موجودة: #{frag}")
                continue
            target_node = _find_heading(target, title, ("h2", "h3", "h4"), lang, title_map)
            if target_node is None:
                errors.append(f"{lang}: مرساة {label} غير موجودة في سطح {target_surface}: #{frag}")
                continue
        measurement = counter["measurement"]
        scope = target_node if target_node.tag == "section" else _section_ancestor(target_node) or target_node
        target_heading = _find_heading(scope, title, ("h2",), lang, title_map)
        rendered = _shared_measure_rendered_target(_serialize_node(scope), measurement)
        measured = int(rendered["count"])
        if measurement == "table_body_rows" and not rendered["has_table"]:
            errors.append(f"{lang}: قسم {title} ليس جدولًا")
        if target_heading is None:
            errors.append(f"{lang}: عنوان الهدف لا يطابق {label}: {title}")
        anchor_mode = counter["anchor_rule"]["mode"]
        if anchor_mode == "section" and target_node.tag != "section":
            errors.append(f"{lang}: مرساة {label} يجب أن تهبط على أعلى القسم «{title}»: {frag}")
        elif anchor_mode == "heading" and target_node.tag not in {"h2", "h3", "h4"}:
            errors.append(f"{lang}: مرساة {label} يجب أن تهبط مباشرة على عنوان الهدف «{title}»: {frag}")
        if row["count"] != measured:
            errors.append(f"{lang}: {label} ({key}) عداد البطاقة={row['count']} والهدف={measured}")
        if row["goto"] and not _same_title(row["goto"], title, lang, title_map):
            errors.append(f"{lang}: مرساة {label} بعنوان غير مطابق: {row['goto']} ≠ {title}")
    for row in rows:
        detail_text = _norm(row["text"])
        if row["label"] and detail_text.startswith(row["label"]):
            detail_text = detail_text[len(row["label"]):].strip()
        if "خلال 24 ساعة السابقة" in detail_text or "over the previous 24 hours" in detail_text:
            errors.append(f"{lang}: لفظ الفترة السابقة تسرب إلى تفاصيل بطاقة الفروع")
    card_text = _norm(node.text())
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
    if not _zone_inside_target_section(node, title, lang, title_map):
        errors.append(f"{lang}: مرساة بطاقة القطاعات خارج القسم المستهدف: {title}")
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


def _hero_contract(registry: dict) -> dict:
    contract = registry.get("hero_kpis")
    if not isinstance(contract, dict) or not isinstance(contract.get("cards"), list):
        raise ValueError("سجل المؤشرات مفقود أو غير صالح: hero_kpis.cards")
    return contract


def _hero_value(meta: dict, zones_data: dict, card: dict, kpis_totals: dict | None = None):
    source = card.get("source") or {}
    kind = source.get("kind")
    if kind == "zones_counter":
        return (zones_data.get("counter") or {}).get(source.get("key"))
    if kind == "zones_sum":
        ids = set(source.get("zone_ids") or [])
        return sum(int(z.get(source.get("field"), 0) or 0) for z in zones_data.get("zones", []) if z.get("id") in ids)
    if kind == "meta_path":
        value = meta
        for part in source.get("path", []):
            value = value[part]
        return value
    if kind == "kpis_totals":
        metric = _metric_by_id(kpis_totals or _default_kpis_totals(), str(source.get("id") or ""))
        return metric.get(source.get("field", "today")) if metric else None
    return None


def _hero_detail(meta: dict, zones_data: dict, card: dict) -> str:
    detail = card.get("detail") or {}
    if detail.get("kind") == "qualifying_composition":
        c = zones_data.get("counter") or {}
        return f"{c.get('confirmed') or 0} مؤكدة + {c.get('probable') or 0} مرجّحة + {c.get('unconfirmed_qualifying') or 0} غير مؤكدة مؤهلة"
    if detail.get("kind") == "unconfirmed_split":
        c = zones_data.get("counter") or {}
        total = int(c.get("unconfirmed_total") or 0)
        return (f"{format_arabic_count(total, card.get('number_format'))} · منها "
                f"{c.get('unconfirmed_qualifying') or 0} مؤهلة · تُذكر ولا تُحتسب")
    if detail.get("kind") == "fire_split":
        fire = (meta.get("hero_sources") or {}).get("fire") or {}
        return (f"المؤكد: {fire.get('confirmed') or 0} · "
                f"المرجّح: {fire.get('probable') or 0} · "
                f"غير المؤكد: {fire.get('unconfirmed') or 0}")
    return detail.get("ar", "")


def validate_hero_kpis(meta: dict, zones_data: dict, registry: dict, *, rendered_html: str | None = None,
                       previous_meta: dict | None = None, kpis_totals: dict | None = None) -> list[str]:
    """حواجز الصفين: عنوان ثابت، ثمانية مواضع حاضرة، وتفصيل مشتق من المصدر."""
    errors: list[str] = []
    try:
        contract = _hero_contract(registry)
    except ValueError as exc:
        return [str(exc)]
    cards = meta.get("hero_kpis")
    expected = contract["cards"]
    kpis_totals = kpis_totals or _default_kpis_totals()
    if not isinstance(cards, list):
        return ["حاجز وجود البطاقة: hero_kpis مفقود أو ليس قائمة"]
    if len(cards) != len(expected):
        errors.append(f"حاجز وجود البطاقة: عدد البطاقات={len(cards)} والملزم={len(expected)}")
    actual = {str(c.get("id")): c for c in cards if isinstance(c, dict) and c.get("id")}
    for expected_index, item in enumerate(expected):
        cid = item.get("id", "")
        card = actual.get(cid)
        if card is None:
            errors.append(f"حاجز وجود البطاقة: البطاقة مفقودة أو اختفى موضعها: {cid}")
            continue
        if card.get("title") != item.get("title"):
            errors.append(f"حاجز ثبات العنوان: {cid}: {card.get('title')} ≠ {item.get('title')}")
        if card.get("row") != item.get("row"):
            errors.append(f"حاجز وجود البطاقة: موضع {cid}={card.get('row')} والملزم={item.get('row')}")
        if card in cards and cards.index(card) != expected_index:
            errors.append(f"حاجز وجود البطاقة: ترتيب {cid}={cards.index(card)} والملزم={expected_index}")
        if card.get("tag") != item.get("tag"):
            errors.append(f"حاجز ثبات العنوان: وسم {cid} متغير أو مفقود")
        source = item.get("source") or {}
        metric = None
        if source.get("kind") == "kpis_totals":
            metric = _metric_by_id(kpis_totals, str(source.get("id") or ""))
            if metric is None:
                errors.append(f"حاجز مصدر المقياس: {cid} مقياس kpis_totals مفقود: {source.get('id')}")
            for layer_name, layer_spec in (item.get("layers") or {}).items():
                if (layer_spec.get("kind"), layer_spec.get("id")) != ("kpis_totals", source.get("id")):
                    errors.append(f"حاجز مصدر المقياس: {cid}.{layer_name} لا يستخدم المقياس نفسه")
                if metric is not None:
                    expected_layer = metric.get(layer_spec.get("field", layer_name))
                    actual_field = layer_name if layer_name in {"cumulative", "updated"} else layer_spec.get("field", layer_name)
                    if expected_layer is None or str(card.get(actual_field)) != str(expected_layer):
                        errors.append(f"حاجز طبقة البطاقة: {cid}.{layer_name} قيمة البطاقة={card.get(actual_field)} والمصدر={expected_layer}")
        expected_value = _hero_value(meta, zones_data, item, kpis_totals)
        if expected_value is not None and str(card.get("value")) != str(expected_value):
            errors.append(f"حاجز تفصيل البطاقة: {cid} قيمة البطاقة={card.get('value')} والمصدر={expected_value}")
        expected_detail = _hero_detail(meta, zones_data, item)
        if expected_detail and card.get("detail") != expected_detail:
            errors.append(f"حاجز تفصيل البطاقة: {cid} تفصيل البطاقة={card.get('detail')} والمصدر={expected_detail}")
        if item.get("source_label") and card.get("source") != item.get("source_label"):
            errors.append(f"حاجز تفصيل البطاقة: مصدر {cid} مفقود أو غير مطابق للسجل")
    rows = {int(k): int(v) for k, v in (contract.get("row_counts") or {}).items()}
    for row, count in rows.items():
        actual_count = sum(1 for c in cards if isinstance(c, dict) and c.get("row") == row)
        if actual_count != count:
            errors.append(f"حاجز وجود البطاقة: الصف {row} يحوي {actual_count}؛ الملزم={count}")
    patterns = contract.get("risk_patterns") or []
    if meta.get("hero_risk_patterns") != patterns:
        errors.append("حاجز وجود البطاقة: وسم أنماط الخطر مفقود أو تغيّر")
    if previous_meta:
        previous = {str(c.get("id")): c for c in (previous_meta.get("hero_kpis") or []) if isinstance(c, dict)}
        for item in expected:
            cid = item.get("id", "")
            if cid in previous and actual.get(cid, {}).get("title") != previous[cid].get("title"):
                errors.append(f"حاجز ثبات العنوان: تقلّب عنوان {cid} بين يومين")
    if rendered_html:
        root = parse_document(rendered_html)
        nodes = [n for n in _nodes(root) if "hero-kpis" in n.attrs.get("class", "").split()]
        surfaces = {
            "سطح التقرير/الطباعة": [n for n in nodes if not _has_ancestor_class(n, "sc-hero")],
            "سطح الشاشة (screen_layer)": [n for n in nodes if _has_ancestor_class(n, "sc-hero")],
        }
        for surface, surface_nodes in surfaces.items():
            if len(surface_nodes) != 1:
                errors.append(f"حاجز وجود البطاقة: {surface} يحوي {len(surface_nodes)} حاويات hero-kpis؛ الملزم=1")
                continue
            if len([n for n in _nodes(surface_nodes[0]) if "hero-kpi" in n.attrs.get("class", "").split()]) != len(expected):
                errors.append(f"حاجز وجود البطاقة: الصف أو بطاقة مؤشر مفقود من {surface}")
    return errors


def validate_imo_permanent_cards(meta: dict, registry: dict, kpis_totals: dict,
                                 *, rendered_html: str | None = None) -> list[str]:
    """حارس القرار 9: بطاقتا IMO الدائمتان، مصدر واحد، وظهور واحد على السطح."""
    errors: list[str] = []
    expected_ids = ("imo-confirmed-incidents", "imo-seafarer-deaths")
    source_url = "https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx"
    source_file = "appendices/imo-incidents.json"
    hero_contract = (registry.get("hero_kpis") or {}).get("cards") or []
    contract_by_id = {str(card.get("id")): card for card in hero_contract if isinstance(card, dict)}
    actual_hero = [card for card in (meta.get("hero_kpis") or []) if isinstance(card, dict)]
    actual_by_id = {str(card.get("id")): card for card in actual_hero if card.get("id")}
    kpi_metrics = {str(metric.get("id")): metric for metric in (kpis_totals or {}).get("metrics", [])
                   if isinstance(metric, dict) and metric.get("id")}

    all_ids = {str(card.get("id")) for card in actual_hero if card.get("id")}
    all_ids.update(str(card.get("id")) for card in (meta.get("official_cards") or [])
                   if isinstance(card, dict) and card.get("id"))
    all_ids.update(str(metric.get("id")) for metric in (kpis_totals or {}).get("metrics", [])
                   if isinstance(metric, dict) and metric.get("id"))
    if "imo-confirmed-attacks" in all_ids:
        errors.append("حاجز معرّف IMO القديم: imo-confirmed-attacks ما زال موجودًا")

    for cid in expected_ids:
        contract = contract_by_id.get(cid)
        card = actual_by_id.get(cid)
        if contract is None:
            errors.append(f"حاجز موضع بطاقة IMO: العقد مفقود: {cid}")
            continue
        if card is None:
            errors.append(f"حاجز موضع بطاقة IMO: البطاقة الدائمة مفقودة: {cid}")
            continue
        if card.get("row") != 2:
            errors.append(f"حاجز موضع بطاقة IMO: {cid} خارج الصف 2")
        if card.get("title") != contract.get("title"):
            errors.append(f"حاجز عنوان بطاقة IMO: {cid} متغير")
        if card.get("source_url") != source_url:
            errors.append(f"حاجز مصدر بطاقة IMO: {cid} بلا رابط IMO الرسمي")
        if source_file not in str(card.get("source") or ""):
            errors.append(f"حاجز مصدر بطاقة IMO: {cid} بلا appendices/imo-incidents.json")
        if source_url not in str(card.get("source") or ""):
            errors.append(f"حاجز مصدر بطاقة IMO: {cid} بلا رابط الصفحة الرسمية")
        metric_id = ((contract.get("source") or {}).get("id") or cid)
        metric = kpi_metrics.get(str(metric_id))
        if metric is None:
            errors.append(f"حاجز مصدر بطاقة IMO: مقياس {metric_id} مفقود")
            continue
        for field in ("today", "cumulative", "updated"):
            if str(card.get("value" if field == "today" else field)) != str(metric.get(field)):
                errors.append(f"حاجز طبقة بطاقة IMO: {cid}.{field} قيمة البطاقة={card.get('value' if field == 'today' else field)} والمصدر={metric.get(field)}")

    official_counts = {}
    for card in (meta.get("official_cards") or []):
        if isinstance(card, dict) and card.get("id") in expected_ids:
            official_counts[card["id"]] = official_counts.get(card["id"], 0) + 1
    for cid, count in official_counts.items():
        if count > 1:
            errors.append(f"حاجز تكرار مصدر IMO: {cid} مكرر {count} مرات في official_cards")

    rows = {int(k): int(v) for k, v in ((registry.get("hero_kpis") or {}).get("row_counts") or {}).items()}
    if rows.get(2) != 2 or sum(1 for card in actual_hero if card.get("row") == 2) != 2:
        errors.append("حاجز موضع بطاقات IMO: الصف الدائم يجب أن يحوي بطاقتين فقط")
    if rendered_html:
        root = parse_document(rendered_html)
        all_nodes = list(_nodes(root))
        # السطحان معرَّفان في المشروع: سطح التقرير/الطباعة، وسطح الشاشة (sc-hero).
        # وفي كل سطح يجب أن تظهر البطاقة الدائمة مرة واحدة فقط؛ التكرار داخل السطح نفسه ممنوع.
        surfaces = {
            "سطح التقرير/الطباعة": [n for n in all_nodes if not _has_ancestor_class(n, "sc-hero")],
            "سطح الشاشة (screen_layer)": [n for n in all_nodes if _has_ancestor_class(n, "sc-hero")],
        }
        for cid in expected_ids:
            for surface, nodes in surfaces.items():
                hero_nodes = [n for n in nodes if n.attrs.get("data-kpi-id") == cid]
                official_nodes = [n for n in nodes if n.attrs.get("data-official-card-id") == cid]
                if len(hero_nodes) != 1:
                    errors.append(f"حاجز تكرار مصدر IMO: {cid} ظاهر {len(hero_nodes)} مرة في {surface}")
                if official_nodes:
                    errors.append(f"حاجز تكرار مصدر IMO: {cid} مكرر في official-cards على {surface}")
    return errors


def _official_contract(registry: dict) -> dict:
    contract = registry.get("official_cards")
    if not isinstance(contract, dict) or not isinstance(contract.get("cards"), list):
        raise ValueError("سجل البطاقات الرسمية مفقود أو غير صالح: official_cards.cards")
    return contract


def _official_source_totals() -> dict:
    """أرقام القائمة الرسمية المحفوظة في المشروع — مصدر واحد لا يُخترع منه شيء."""
    p = ROOT / "appendices" / "imo-incidents.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    totals = d.get("totals") or {}
    return {"confirmed_incidents": str(totals.get("confirmed_incidents") or ""),
            "confirmed_seafarer_deaths": str(totals.get("confirmed_seafarer_deaths") or "")}


def validate_official_cards(meta: dict, registry: dict) -> list[str]:
    """يثبت وجود بطاقتي الوفيات والعبور وصدق حالات القراءة الثلاث."""
    errors: list[str] = []
    try:
        contract = _official_contract(registry)
    except ValueError as exc:
        return [str(exc)]
    actual_cards = meta.get("official_cards")
    expected_cards = contract["cards"]
    if not isinstance(actual_cards, list):
        return ["حاجز وجود البطاقات الرسمية: official_cards مفقود أو ليس قائمة"]
    expected_ids = [str(card.get("id")) for card in expected_cards]
    actual = {str(card.get("id")): card for card in actual_cards if isinstance(card, dict) and card.get("id")}
    if len(actual_cards) != len(expected_cards):
        errors.append(f"حاجز وجود البطاقات الرسمية: العدد={len(actual_cards)} والملزم={len(expected_cards)}")
    for expected in expected_cards:
        cid = str(expected.get("id"))
        card = actual.get(cid)
        if card is None:
            errors.append(f"حاجز وجود البطاقات الرسمية: البطاقة مفقودة: {cid}")
            continue
        if card.get("title") != expected.get("title"):
            errors.append(f"حاجز ثبات العنوان: {cid}: {card.get('title')} ≠ {expected.get('title')}")
        if expected.get("basis") and card.get("basis") != expected["basis"]:
            errors.append(f"حاجز المصدر الرسمي: أساس {cid} مفقود أو متغير")
        if expected.get("badges") and card.get("badges") != expected["badges"]:
            errors.append(f"حاجز المصدر الرسمي: أوسمة {cid} مفقودة أو متغيرة")
        layers = card.get("layers")
        if not isinstance(layers, dict):
            errors.append(f"حاجز الطبقات: {cid} بلا طبقات ثلاث")
            continue
        for key in contract.get("layer_keys", ["daily", "cumulative", "updated"]):
            layer = layers.get(key)
            if not isinstance(layer, dict):
                errors.append(f"حاجز الطبقات: {cid}.{key} مفقود")
                continue
            if layer.get("label") != expected.get("layers", {}).get(key, {}).get("label"):
                errors.append(f"حاجز ثبات العنوان: {cid}.{key} label متغير")
            if not str(layer.get("source") or "").strip():
                errors.append(f"حاجز المصدر الرسمي: {cid}.{key} بلا مصدر")
            state = layer.get("state")
            value = str(layer.get("value") or "")
            _tot = _official_source_totals()
            _want = {"imo-confirmed-incidents": _tot.get("confirmed_incidents"),
                     "imo-seafarer-deaths": _tot.get("confirmed_seafarer_deaths")}.get(cid)
            if _want and key == "cumulative" and value and value != _want:
                errors.append(f"حاجز مطابقة القائمة الرسمية: {cid}.{key} = {value} والمصدر الرسمي = {_want}")
            if state == "undisclosed" and value != "لم يُعلن":
                errors.append(f"حاجز منع الصفر الكاذب: {cid}.{key} يجب أن يكون «لم يُعلن» عند عدم الإفصاح")
            if state == "no_coverage" and value != "لا تغطية":
                errors.append(f"حاجز التغطية: {cid}.{key} يجب أن يكون «لا تغطية» عند غياب القراءة")
            if state == "denied" and value != "0":
                errors.append(f"حاجز النفي: {cid}.{key} يجب أن يكون «0» عند النفي الصريح")
            if key == "cumulative":
                if layer.get("label") != "المجموع منذ 28 فبراير 2026":
                    errors.append(f"حاجز الطبقات: {cid} تسمية المجموع غير معتمدة")
                if re.search(r"\b\d+\s+من\s+\d+\b|فجوة|\bأيام?\b", value):
                    errors.append(f"حاجز الطبقات: نص نقص أو أيام في مجموع {cid}")
        if cid == "imo-seafarer-deaths":
            daily = (layers.get("daily") or {}).get("value")
            if (layers.get("daily") or {}).get("state") == "undisclosed" and str(daily) == "0":
                errors.append("حاجز منع الصفر الكاذب: وفيات البحّارة بلا إفصاح لا تعرض 0")
        if cid == "imo-transit-september-2026":
            detail = " ".join(str(card.get(k) or "") for k in ("constraint", "period", "average", "high", "low"))
            # مصدر الحكم الواحد: الأوسمة تُقرأ من السجل الحاكم (official_cards) لا من قائمة مثبّتة في الكود،
            # لأن المالك أقرّ حذف وسم «للعلم العام» من كل الأسطح. الشرط يبقى فشلًا مغلقًا على أي فرق.
            if card.get("badges") != (expected.get("badges") or []):
                errors.append("حاجز العبور: الوسمان الرسميان مفقودان")
            if not all(token in detail for token in ("15.6", "25.8", "23 سبتمبر", "8.0", "3 سبتمبر")):
                errors.append("حاجز العبور: متوسط أو أعلى/أدنى قراءة سبتمبر مفقودة")
            if re.search(r"مناطق الانتظار|المؤشران\s*8\s*و?9|أرقام مناطق", detail):
                errors.append("حاجز العبور: أرقام مناطق الانتظار محظورة")
    for cid in set(actual) - set(expected_ids):
        errors.append(f"حاجز وجود البطاقات الرسمية: بطاقة غير مسجلة: {cid}")
    return errors


def validate_one(report_html: str, additions_html: str, *, ar_report_html: str | None = None,
                 ar_additions_html: str | None = None, title_map: dict[str, str] | None = None,
                 registry: dict | None = None, zones_data: dict | None = None,
                 sections_policy: dict | None = None, surface: str = "report") -> list[str]:
    report = parse_document(report_html)
    additions = parse_document(additions_html)
    lang = _lang(report)
    ar_report = parse_document(ar_report_html) if ar_report_html else report
    ar_additions = parse_document(ar_additions_html) if ar_additions_html else additions
    cards = [card for card in (registry or {}).get("cards", []) if (card.get("status") or {}).get("state") == "enabled"]
    root = report if surface == "report" else additions
    resolved, errors = _resolve_components(root, cards, lang, title_map or {}, sections_policy, surface)
    for card in cards:
        nodes = resolved.get(card["id"], [])
        if not nodes:
            continue
        component_class = card["page_component"]["class"]
        for node in nodes:
            if component_class == "sc-card":
                errors.extend(_validate_news_card(card, node, report, additions, ar_report, ar_additions,
                                                  lang, title_map or {}, sections_policy))
            elif component_class == "tz":
                errors.extend(_validate_zone_card(card, node, lang, zones_data, title_map or {}))
            else:
                errors.append(f"{lang}: مكوّن بطاقة غير معتمد في السجل: {component_class}")
    return errors


def validate_card_documents(*, ar_report: str, ar_additions: str, en_report: str | None = None,
                             en_additions: str | None = None, glossary_path: Path | None = None,
                             registry_path: Path | None = None, zones_data: dict | None = None,
                             meta_data: dict | None = None,
                             sections_policy: dict | None = None,
                             kpis_totals_data: dict | None = None) -> list[str]:
    try:
        registry = load_registry(registry_path)
    except ValueError as exc:
        return [str(exc)]
    title_map = _load_title_map(glossary_path)
    errors = validate_one(ar_report, ar_additions, title_map=title_map, registry=registry,
                          zones_data=zones_data, sections_policy=sections_policy, surface="report")
    errors.extend(validate_one(ar_report, ar_additions, title_map=title_map, registry=registry,
                               zones_data=zones_data, sections_policy=sections_policy, surface="additions"))
    if en_report:
        errors.extend(validate_one(en_report, en_additions or ar_additions, ar_report_html=ar_report,
                                   ar_additions_html=ar_additions, title_map=title_map,
                                   registry=registry, zones_data=zones_data,
                                   sections_policy=sections_policy, surface="report"))
        errors.extend(validate_one(en_report, en_additions or ar_additions, ar_report_html=ar_report,
                                   ar_additions_html=ar_additions, title_map=title_map,
                                   registry=registry, zones_data=zones_data,
                                   sections_policy=sections_policy, surface="additions"))
    if meta_data is not None and zones_data is not None:
        errors.extend(validate_hero_kpis(meta_data, zones_data, registry, rendered_html=ar_report,
                                         kpis_totals=kpis_totals_data))
    if meta_data is not None:
        errors.extend(validate_official_cards(meta_data, registry))
        if kpis_totals_data is not None:
            errors.extend(validate_imo_permanent_cards(meta_data, registry, kpis_totals_data,
                                                       rendered_html=ar_report))
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--dist-root", default=str(_default_dist_root()))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    args = parser.parse_args(argv)
    blacklist_errors = _registry_blacklist_errors(Path(args.registry))
    if blacklist_errors:
        for error in blacklist_errors:
            print(f"✘ {error}")
        return 2
    dist = Path(args.dist_root)
    paths = [dist / "reports" / f"{args.date}.html", dist / "additions.html",
             dist / "reports" / "en" / f"{args.date}.html", dist / "reports" / "en" / "additions.html"]
    for path in paths:
        if not path.is_file():
            print(f"✘ ملف مطلوب مفقود: {path}")
            return 2
    zone_path = dist.parent / "sources" / "zones" / f"{args.date}.json"
    zones_data = _load_json(zone_path)
    kpis_totals_path = ROOT / "web" / "kpis-totals" / f"{args.date}.json"
    kpis_totals_data = _load_json(kpis_totals_path)
    meta_path = dist.parent / "sources" / "meta" / f"{args.date}.json"
    meta_data = _load_json(meta_path)
    policy_path = dist.parent / "sources" / "report-sections-policy.json"
    sections_policy = _load_json(policy_path)
    if sections_policy is None:
        print(f"✘ سياسة أسطح الأقسام مفقودة أو غير صالحة: {policy_path}")
        return 2
    errors = validate_card_documents(
        ar_report=paths[0].read_text(encoding="utf-8"), ar_additions=paths[1].read_text(encoding="utf-8"),
        en_report=paths[2].read_text(encoding="utf-8"), en_additions=paths[3].read_text(encoding="utf-8"),
        glossary_path=dist.parent / "sources" / "i18n" / "en" / "glossary.json",
        registry_path=Path(args.registry), zones_data=zones_data, meta_data=meta_data,
        sections_policy=sections_policy, kpis_totals_data=kpis_totals_data,
    )
    if errors:
        for error in errors:
            print(f"✘ {error}")
        return 2
    enabled = [c["id"] for c in load_registry(Path(args.registry))["cards"] if c["status"]["state"] == "enabled"]
    print(CONTRACT_LINE)
    print(f"✔ حراسة البطاقات التصريحية: {len(enabled)} بطاقات مفعّلة ({'، '.join(enabled)})")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
