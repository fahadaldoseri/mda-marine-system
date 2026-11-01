#!/usr/bin/env python3
"""قياس واحد للبنود الظاهرة في HTML المرسوم.

تستخدمه طبقة بناء البطاقة وبوابة العدادات نفسها. لا يقرأ Markdown ولا قيم
meta؛ المدخل دائمًا هو HTML الذي سيظهر على السطح، مع معرّف الهدف عند الحاجة.
"""
from __future__ import annotations

from html.parser import HTMLParser


_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_SKIP_PARAGRAPH_CLASSES = {"sec-lede", "src-note"}


class _RenderedCounter(HTMLParser):
    def __init__(self, target_id: str | None = None):
        super().__init__(convert_charrefs=True)
        self.target_id = target_id
        self.depth = 0
        self.target_depth: int | None = 0 if target_id is None else None
        self.target_found = target_id is None
        self.list_depth = 0
        self.table_depth = 0
        self.tbody_depth = 0
        self.list_items = 0
        self.table_rows = 0
        self.paragraphs = 0
        self.has_table = False

    def _in_target(self) -> bool:
        return self.target_found and self.target_depth is not None and self.depth >= self.target_depth

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.target_id and not self.target_found and attrs.get("id") == self.target_id:
            self.target_found = True
            self.target_depth = self.depth
        if self._in_target():
            if tag in {"ul", "ol"}:
                self.list_depth += 1
            elif tag == "li" and self.list_depth == 1:
                self.list_items += 1
            elif tag == "table":
                self.has_table = True
            elif tag == "tbody":
                self.tbody_depth += 1
            elif tag == "tr" and self.tbody_depth:
                self.table_rows += 1
            elif tag == "p":
                classes = set((attrs.get("class") or "").split())
                if not classes.intersection(_SKIP_PARAGRAPH_CLASSES):
                    self.paragraphs += 1
        if tag not in _VOID:
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag not in _VOID and self.depth:
            if self._in_target():
                if tag in {"ul", "ol"} and self.list_depth:
                    self.list_depth -= 1
                elif tag == "tbody" and self.tbody_depth:
                    self.tbody_depth -= 1
            self.depth -= 1

    def count(self, measurement: str) -> int:
        if not self.target_found:
            return 0
        if measurement == "table_body_rows":
            return self.table_rows
        if measurement == "visible_items":
            if self.list_items:
                return self.list_items
            if self.table_rows:
                return self.table_rows
            return self.paragraphs
        raise ValueError(f"قياس غير معتمد: {measurement}")


def measure_rendered_target(source: str, measurement: str, target_id: str | None = None) -> dict[str, int | bool]:
    """أعدّ بنية الهدف المرسومة فعليًا من HTML واحد.

    النتيجة تحمل count وhas_table وtarget_found حتى تستخدم البوابة نفس القراءة
    في تقريرها، ويستخدم المولد count نفسه عند إنشاء البطاقة.
    """
    counter = _RenderedCounter(target_id)
    counter.feed(source)
    counter.close()
    return {
        "count": counter.count(measurement),
        "has_table": counter.has_table,
        "target_found": counter.target_found,
    }


def count_rendered_fragment(fragment: str, measurement: str) -> int:
    """اختصار المولد: عدّ مقطع HTML الذي سيُدرج داخل القسم."""
    return int(measure_rendered_target(fragment, measurement)["count"])
