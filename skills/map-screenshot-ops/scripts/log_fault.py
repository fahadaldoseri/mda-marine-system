#!/usr/bin/env python3
"""Fault ledger for this skill (self-learning hook). 12 fixed columns, tab separated.
Modes:  --add <12 fields...>   append one fault (rejects malformed rows)
        --check               validate the whole ledger (every row 12 cols, guard+evidence present)
        --list                print id / class / symptom
Exit 0 = ok. Exit 2 = rejected or ledger invalid (fails closed)."""
import argparse, datetime, os, re, sys

COLS = ["id", "date", "axis", "class", "symptom", "root_cause", "fix", "guard", "linked_tool", "evidence", "status", "lesson"]
CLASSES = {"scope", "gate-semantics", "derivation", "schema", "dependency", "data", "process", "tooling"}
EVID = re.compile(r"(خرج\s*(0|2|70)|رمز\s*(0|2|70)|فاشل\s*(0|صفر)|exit[= ](0|2|70)|rc=(0|2|70))")
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "fault_ledger.tsv")


def read(path):
    if not os.path.exists(path):
        return []
    rows = []
    for i, line in enumerate(open(path, encoding="utf-8")):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        if line.split("\t")[0] == COLS[0]:
            continue
        rows.append((i + 1, line.split("\t")))
    return rows


def check(path):
    rows = read(path)
    bad = []
    ids = set()
    if not rows:
        bad.append("empty ledger: at least one fault must be recorded")
    for ln, cells in rows:
        if len(cells) != 12:
            bad.append(f"line {ln}: {len(cells)} columns, want 12")
            continue
        d = dict(zip(COLS, cells))
        for k in COLS:
            if not d[k].strip():
                bad.append(f"line {ln}: empty field '{k}'")
        if "|" in "\t".join(cells):
            bad.append(f"line {ln}: a '|' character would split the row")
        if d["id"] in ids:
            bad.append(f"line {ln}: duplicate id {d['id']}")
        ids.add(d["id"])
        if d["class"] not in CLASSES:
            bad.append(f"line {ln}: class '{d['class']}' not in {sorted(CLASSES)}")
        if not EVID.search(d["evidence"]):
            bad.append(f"line {ln}: evidence not runnable-proof: {d['evidence'][:60]}")
        if d["guard"] in ("none", "-", "None", "لا شيء"):
            bad.append(f"line {ln}: guard '{d['guard']}' means the fault can repeat")
    for m in bad:
        print("INVALID:", m, file=sys.stderr)
    print(f"checked {len(rows)} fault row(s): {len(bad)} violation(s)")
    return 2 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--add", nargs=12, metavar=COLS)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.add:
        vals = [v.strip() for v in a.add]
        vals[1] = vals[1] or datetime.date.today().isoformat()
        row = dict(zip(COLS, vals))
        if not row["date"]:
            row["date"] = datetime.date.today().isoformat()
        cells = [row[c] or (datetime.date.today().isoformat() if c == "date" else "") for c in COLS]
        if any("\t" in c for c in cells):
            print("INVALID: tab inside a field", file=sys.stderr); return 2
        tmp = row
        for c in COLS:
            if not tmp[c].strip() and c != "date":
                print(f"INVALID: empty field '{c}'", file=sys.stderr); return 2
        if tmp["class"] not in CLASSES:
            print(f"INVALID: class '{tmp['class']}'", file=sys.stderr); return 2
        if not EVID.search(tmp["evidence"]):
            print("INVALID: evidence must contain a command and its exit marker "
                  "(e.g. 'تحقق حي 2026-11-11: python3 x.py -> exit 0'), got: " + tmp["evidence"], file=sys.stderr)
            return 2
        if tmp["guard"] in ("none", "-", "None", "لا شيء"):
            print("INVALID: a fault may not be closed without a guard", file=sys.stderr); return 2
        rows = read(a.ledger)
        if any(r[1][0] == tmp["id"] for r in rows if len(r[1]) == 12):
            print(f"INVALID: duplicate id {tmp['id']}", file=sys.stderr); return 2
        new = not os.path.exists(a.ledger)
        with open(a.ledger, "a", encoding="utf-8") as fh:
            if new:
                fh.write("# " + " | ".join(COLS) + "\n")
                fh.write("\t".join(COLS) + "\n")
            fh.write("\t".join(cells) + "\n")
        print(f"appended {tmp['id']} to {a.ledger}")
        return check(a.ledger)
    if a.list:
        for ln, cells in read(a.ledger):
            print(f"{cells[0]:>6} {cells[3]:<15} {cells[4][:80]}" if len(cells) == 12 else f"line {ln}: {len(cells)} cols")
        return 0
    return check(a.ledger)


if __name__ == "__main__":
    sys.exit(main())
