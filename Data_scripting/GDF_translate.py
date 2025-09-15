#!/usr/bin/env python3
import csv
import re
from dataclasses import dataclass
from typing import List, Union, Tuple, Optional

# ---------- Tokenization ----------
QUAL_PAT = re.compile(r'(y\d{4}|M(1[0-2]|0?[1-9])|d(3[01]|[12]?\d)|t[1-7]|h(2[0-3]|[01]?\d)|m([1-5]?\d))')
DUR_PAT  = re.compile(r'(y\d+|M\d+|d\d+|h\d+|m\d+)')

# Match [(...){...}] or [(...)] (duration optional) with the correct bracket order
SNIPPET_PAT = re.compile(r"\[\([^\)\]]+\)(?:\{[^\}]+\})?\]")

# Detect special PERM/TEMP patterns that appear as plain text
SPECIAL_PAT = re.compile(r"\b(PERM_CLOSED|TEMP_CLOSED)\s*:\s*\[(.*?)\]")

WEEKDAY_MAP = {
    1: "Sunday", 2: "Monday", 3: "Tuesday", 4: "Wednesday",
    5: "Thursday", 6: "Friday", 7: "Saturday",
}
MONTH_MAP = {
    1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
    7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"
}

# ---- Business-hours helpers ----
def _to_minutes(h: int, m: int) -> int:
    return h * 60 + m

def _fmt_range(start_min: int, end_min: int) -> str:
    def _fmt(mins: int) -> str:
        mins = max(0, min(24*60, mins))
        h = mins // 60
        m = mins % 60
        ampm = 'am' if h < 12 else 'pm'
        hh = h % 12
        if hh == 0:
            hh = 12
        return f"{hh}:{m:02d} {ampm}"
    return f"{_fmt(start_min)}–{_fmt(end_min)}"

def _iso_date_from_quals(quals: List[str]) -> Optional[str]:
    y = next((int(q[1:]) for q in quals if q.startswith('y')), None)
    M = next((int(q[1:]) for q in quals if q.startswith('M')), None)
    d = next((int(q[1:]) for q in quals if q.startswith('d')), None)
    if y and M and d:
        return f"{y:04d}-{M:02d}-{d:02d}"
    return None

def _weekday_list_from_quals(quals: List[str], duration_tokens: List[str]) -> List[int]:
    ts = [int(q[1:]) for q in quals if q.startswith('t')]
    d_days = next((int(d[1:]) for d in duration_tokens if d.startswith('d')), None)
    if ts and d_days:
        start = ts[0]
        return [((start + i - 1) % 7) + 1 for i in range(d_days)]
    if ts:
        return ts
    # default: all days
    return [1,2,3,4,5,6,7]

def _start_minutes_from_quals(quals: List[str]) -> Optional[int]:
    hh = next((int(q[1:]) for q in quals if q.startswith('h')), None)
    mm = next((int(q[1:]) for q in quals if q.startswith('m')), 0)
    if hh is None and mm == 0:
        return None
    return _to_minutes(hh or 0, mm or 0)

def _duration_minutes(duration_tokens: List[str]) -> int:
    total = 0
    for tok in duration_tokens:
        if tok.startswith('h'):
            total += int(tok[1:]) * 60
        elif tok.startswith('m'):
            total += int(tok[1:])
        elif tok.startswith('d'):
            # day duration is only for weekday spans, not business hours length
            continue
    return total

# ---------- AST ----------
@dataclass
class Atom:
    qualifiers: List[str]
    duration: List[str]

@dataclass
class UnionNode:
    parts: List['Node']

@dataclass
class IntersectNode:
    left: 'Node'
    right: 'Node'

@dataclass
class SubtractNode:
    left: 'Node'
    right: 'Node'

Node = Union[Atom, UnionNode, IntersectNode, SubtractNode]

# ---- Evaluate to weekly schedule: dict[int weekday 1..7] -> list[(start_min, end_min)] ----
from collections import defaultdict

def _eval_atom(a: Atom) -> dict:
    sched = defaultdict(list)
    start = _start_minutes_from_quals(a.qualifiers)
    dur = _duration_minutes(a.duration)
    if start is None or dur <= 0:
        return sched
    end = start + dur
    days = _weekday_list_from_quals(a.qualifiers, a.duration)
    for t in days:
        sched[t].append((start, min(end, 24*60)))
    return sched

def _merge_ranges(ranges: List[tuple]) -> List[tuple]:
    if not ranges:
        return []
    rs = sorted(ranges)
    merged = [rs[0]]
    for s,e in rs[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s,e))
    return merged

def _intersect_day_ranges(A: List[tuple], B: List[tuple]) -> List[tuple]:
    out = []
    i=j=0
    A = sorted(A)
    B = sorted(B)
    while i < len(A) and j < len(B):
        s1,e1 = A[i]; s2,e2 = B[j]
        s = max(s1,s2); e = min(e1,e2)
        if e > s:
            out.append((s,e))
        if e1 < e2:
            i += 1
        else:
            j += 1
    return out

def _subtract_day_ranges(A: List[tuple], B: List[tuple]) -> List[tuple]:
    # subtract B from A
    out = []
    for s1,e1 in sorted(A):
        cur = [(s1,e1)]
        for s2,e2 in sorted(B):
            tmp = []
            for x,y in cur:
                # no overlap
                if e2 <= x or y <= s2:
                    tmp.append((x,y))
                else:
                    if x < s2:
                        tmp.append((x, max(x, s2)))
                    if e2 < y:
                        tmp.append((max(e2, x), y))
            cur = tmp
        out.extend(cur)
    return _merge_ranges(out)

def _union_sched(A: dict, B: dict) -> dict:
    out = defaultdict(list)
    for t in set(A.keys()) | set(B.keys()):
        out[t] = _merge_ranges((A.get(t) or []) + (B.get(t) or []))
    return out

def _intersect_sched(A: dict, B: dict) -> dict:
    out = defaultdict(list)
    for t in set(A.keys()) & set(B.keys()):
        out[t] = _intersect_day_ranges(A.get(t) or [], B.get(t) or [])
    return out

def _subtract_sched(A: dict, B: dict) -> dict:
    out = defaultdict(list)
    for t in set(A.keys()) | set(B.keys()):
        out[t] = _subtract_day_ranges(A.get(t) or [], B.get(t) or [])
    return out

def evaluate_weekly(node: Node) -> dict:
    if isinstance(node, Atom):
        return _eval_atom(node)
    if isinstance(node, UnionNode):
        cur = defaultdict(list)
        for p in node.parts:
            cur = _union_sched(cur, evaluate_weekly(p))
        return cur
    if isinstance(node, IntersectNode):
        return _intersect_sched(evaluate_weekly(node.left), evaluate_weekly(node.right))
    if isinstance(node, SubtractNode):
        return _subtract_sched(evaluate_weekly(node.left), evaluate_weekly(node.right))
    return defaultdict(list)

# ---------- Parsing for [(...){...}] ----------
def parse_atom(s: str, i: int) -> Tuple[Atom, int]:
    if s[i:i+2] != '[(':
        raise ValueError(f"Expected '[(' at {i}")
    i += 2
    end_paren = s.index(')', i)
    inner = s[i:end_paren]
    flat_quals = [m.group(0) for m in QUAL_PAT.finditer(inner)]
    j = end_paren + 1
    durs = []
    if j < len(s) and s[j] == '{':
        j += 1
        end_brace = s.index('}', j)
        dur_str = s[j:end_brace]
        durs = [m.group(0) for m in DUR_PAT.finditer(dur_str)]
        k = end_brace + 1
        if s[k] != ']':
            raise ValueError(f"Expected ']' at {k}")
        k += 1
    else:
        # No explicit duration; require closing ']' immediately
        if s[j] != ']':
            raise ValueError(f"Expected ']' at {j}")
        k = j + 1
    return Atom(flat_quals, durs), k

def skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i].isspace():
        i += 1
    return i

def parse_expression(s: str, i: int = 0) -> Tuple[Node, int]:
    def parse_factor(s, i):
        i = skip_ws(s, i)
        if s[i:i+2] == '[(':
            return parse_atom(s, i)
        if s[i] == '[':
            # group like [[...]]
            depth = 0
            start = i + 1
            j = start
            while j < len(s):
                if s[j] == '[': depth += 1
                elif s[j] == ']':
                    if depth == 0: break
                    depth -= 1
                j += 1
            inner = s[start:j]
            node, _ = parse_expression(inner, 0)
            return node, j + 1
        raise ValueError(f"Unexpected at pos {i}: {s[i:i+10]}")

    def parse_term(s, i):
        node, i = parse_factor(s, i)
        while True:
            i = skip_ws(s, i)
            if i >= len(s) or s[i] in ']+':
                break
            if s[i] == '*':
                rhs, i = parse_factor(s, i+1)
                node = IntersectNode(node, rhs)
            elif s[i] == '-':
                rhs, i = parse_factor(s, i+1)
                node = SubtractNode(node, rhs)
            else:
                break
        return node, i

    node, i = parse_term(s, i)
    while True:
        i = skip_ws(s, i)
        if i >= len(s) or s[i] == ']':
            break
        if s[i] == '+':
            rhs, i = parse_term(s, i+1)
            if isinstance(node, UnionNode):
                node.parts.append(rhs)
            else:
                node = UnionNode([node, rhs])
        else:
            break
    return node, i

# ---------- Rendering ----------
def weekday_range_text(start_t: int, days: int) -> Optional[str]:
    if days <= 0: 
        return None
    seq = [(start_t + i - 1) % 7 + 1 for i in range(days)]
    return f"{WEEKDAY_MAP[seq[0]]} through {WEEKDAY_MAP[seq[-1]]}" if days > 1 else WEEKDAY_MAP[seq[0]]

def duration_to_text(durs: List[str]) -> str:
    total = {"y":0,"M":0,"d":0,"h":0,"m":0}
    for d in durs:
        total[d[0]] += int(d[1:])
    parts = []
    if total["y"]: parts.append(f'{total["y"]} year{"s" if total["y"]!=1 else ""}')
    if total["M"]: parts.append(f'{total["M"]} month{"s" if total["M"]!=1 else ""}')
    if total["d"]: parts.append(f'{total["d"]} day{"s" if total["d"]!=1 else ""}')
    if total["h"]: parts.append(f'{total["h"]} hour{"s" if total["h"]!=1 else ""}')
    if total["m"]: parts.append(f'{total["m"]} minute{"s" if total["m"]!=1 else ""}')
    return " and ".join(parts) if parts else "0 minutes"

def fmt_time(h: int, m: int) -> str:
    ampm = "AM" if h < 12 else "PM"
    hh = h % 12
    if hh == 0: hh = 12
    return f"{hh}:{m:02d} {ampm}"

def format_date_from_quals(quals: List[str]) -> str:
    year = next((int(q[1:]) for q in quals if q.startswith('y')), None)
    month = next((int(q[1:]) for q in quals if q.startswith('M')), None)
    day = next((int(q[1:]) for q in quals if q.startswith('d')), None)
    parts = []
    if month is not None and day is not None:
        parts.append(f"{MONTH_MAP.get(month, f'Month {month}')} {day}")
    elif month is not None:
        parts.append(MONTH_MAP.get(month, f"Month {month}"))
    elif day is not None:
        parts.append(f"day {day}")
    if year is not None:
        if parts:
            parts[-1] = f"{parts[-1]}, {year}"
        else:
            parts.append(str(year))
    return parts[0] if parts else ""

def when_phrase(when: str) -> str:
    if not when:
        return ""
    return when if when.startswith("in ") else "on " + when

def quals_to_text(quals: List[str], duration: List[str]) -> Tuple[str, str]:
    years      = [int(q[1:]) for q in quals if q.startswith('y')]
    months     = [int(q[1:]) for q in quals if q.startswith('M')]
    month_days = [int(q[1:]) for q in quals if q.startswith('d')]
    weekdays   = [int(q[1:]) for q in quals if q.startswith('t')]
    hours      = [int(q[1:]) for q in quals if q.startswith('h')]
    minutes    = [int(q[1:]) for q in quals if q.startswith('m')]

    # start time
    start_time = ""
    if hours or minutes:
        h = hours[0] if hours else 0
        m = minutes[0] if minutes else 0
        ampm = "AM" if h < 12 else "PM"
        hh = h % 12
        if hh == 0: hh = 12
        start_time = f"{hh}:{m:02d} {ampm}"

    # weekday range if paired with day-duration
    d_days = next((int(d[1:]) for d in duration if d.startswith('d')), None)
    parts = []

    if weekdays and d_days:
        parts.append(weekday_range_text(weekdays[0], d_days))
    elif weekdays:
        names = [WEEKDAY_MAP.get(t, f"t{t}") for t in weekdays]
        parts.append(", ".join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else names[0])

    # specific day of month + month name
    months_used = False
    if month_days and months:
        parts.append(f"{MONTH_MAP.get(months[0], f'Month {months[0]}')} {month_days[0]}")
        months_used = True
    elif month_days:
        parts.append(f"day {month_days[0]}")

    # month + year
    if months and not months_used:
        if years:
            parts.append(f"in {MONTH_MAP.get(months[0], f'Month {months[0]}')} {years[0]}")
        else:
            parts.append(f"in {MONTH_MAP.get(months[0], f'Month {months[0]}')}")
    elif years:
        parts.append(f"in {years[0]}")

    # put "in ..." at the end for readability
    bare_in = [p for p in parts if p.startswith("in ")]
    others  = [p for p in parts if not p.startswith("in ")]
    when = ", ".join(others + bare_in)
    return start_time, when

def describe_atom(a: Atom) -> str:
    start_time, when = quals_to_text(a.qualifiers, a.duration)
    dtext = duration_to_text(a.duration)
    if start_time and when:
        return f"{start_time} for {dtext} {when_phrase(when)}"
    if start_time:
        return f"{start_time} for {dtext}"
    if when:
        return f"{dtext} {when_phrase(when)}"
    return dtext

def describe(node: Node) -> str:
    if isinstance(node, Atom):
        return describe_atom(node)
    if isinstance(node, UnionNode):
        return " and ".join(describe(p) for p in node.parts)
    if isinstance(node, IntersectNode):
        return f"{describe(node.left)} limited to {describe(node.right)}"
    if isinstance(node, SubtractNode):
        return f"{describe(node.left)} except {describe(node.right)}"
    return "Unknown"

def translate_gdf(expr: str) -> str:
    node, _ = parse_expression(expr.strip())
    text = describe(node)
    return re.sub(r'\s+', ' ', text).replace("12:00 AM","midnight").strip()

def translate_specials(cell_text: str) -> Optional[str]:
    # Handles e.g. PERM_CLOSED:[(y2025M1d1)] or TEMP_CLOSED:[(y2025M1d1)(y2025M3d28)]
    m = SPECIAL_PAT.search(cell_text)
    if not m:
        return None
    kind = m.group(1)
    inside = m.group(2)
    # inside may look like (y2025M1d1)(y2025M3d28)
    parens = re.findall(r"\(([^)]+)\)", inside)
    dates = []
    for p in parens:
        quals = [q.group(0) for q in QUAL_PAT.finditer(p)]
        dates.append(format_date_from_quals(quals))
    if kind == 'PERM_CLOSED' and dates:
        return f"Permanently closed on {dates[0]}"
    if kind == 'TEMP_CLOSED' and len(dates) >= 2:
        return f"Temporarily closed from {dates[0]} to {dates[1]}"
    # Fallback
    return None

def extract_full_gdf_expression(text: str) -> Optional[str]:
    """Find the first top-level GDF bracketed expression like [[...]] or [(...){...}] in a messy cell string.
    We choose the first '[' whose next char is '(' or '[' and then return the balanced bracket span.
    """
    if not text:
        return None
    n = len(text)
    i = 0
    while i < n:
        if text[i] == '[' and i + 1 < n and text[i+1] in '([':
            # capture balanced brackets starting at i
            depth = 0
            j = i
            while j < n:
                if text[j] == '[':
                    depth += 1
                elif text[j] == ']':
                    depth -= 1
                    if depth == 0:
                        return text[i:j+1]
                j += 1
            # if we fall through, unbalanced — give up
            return None
        i += 1
    return None

def translate_cell(cell_text: str) -> str:
    cell_text = (cell_text or '').strip()
    if not cell_text:
        return ''
    # 1) Permanent closure wins
    m = SPECIAL_PAT.search(cell_text)
    if m and m.group(1) == 'PERM_CLOSED':
        inside = m.group(2)
        par = re.search(r"\(([^)]+)\)", inside)
        iso = None
        if par:
            quals = [q.group(0) for q in QUAL_PAT.finditer(par.group(1))]
            iso = _iso_date_from_quals(quals)
        if iso:
            return f"No (Closed permanently on {iso})"
        return "No (Closed permanently)"

    # 2) Try full expression; otherwise gather snippets
    expr = extract_full_gdf_expression(cell_text)
    nodes = []
    if expr:
        try:
            n,_ = parse_expression(expr)
            nodes.append(n)
        except Exception:
            pass
    if not nodes:
        for snip in SNIPPET_PAT.findall(cell_text):
            try:
                n,_ = parse_expression(snip)
                nodes.append(n)
            except Exception:
                continue
    # Evaluate combined union of all found nodes
    from collections import defaultdict
    sched = defaultdict(list)
    for n in nodes:
        sched = _union_sched(sched, evaluate_weekly(n))

    # Format 7-day block; if a day has multiple ranges, join by ", "
    lines = []
    for t in [1,2,3,4,5,6,7]:
        lines.append(WEEKDAY_MAP[t])
        ranges = _merge_ranges(sched.get(t, []))
        if not ranges:
            lines.append("Closed")
        else:
            lines.append(", ".join(_fmt_range(s,e) for s,e in ranges))
    return "\n".join(lines)

# ---------- CSV helper ----------

def _normalize_header(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).lower()

def _resolve_column_name(requested: str, fieldnames: List[str]) -> str:
    """Resolve the requested column against CSV headers, case/space-insensitively.
    Falls back to numeric index (1-based) if requested is a digit.
    Raises ValueError with a helpful message if not found.
    """
    if not fieldnames:
        raise ValueError("CSV has no headers (empty file?)")
    # Exact match first
    if requested in fieldnames:
        return requested
    norm_req = _normalize_header(requested)
    norm_map = {_normalize_header(h): h for h in fieldnames}
    if norm_req in norm_map:
        return norm_map[norm_req]
    # Try as a 1-based index
    if requested.isdigit():
        idx = int(requested) - 1
        if 0 <= idx < len(fieldnames):
            return fieldnames[idx]
    # Not found: build a readable list of headers
    pretty = ", ".join(fieldnames)
    raise ValueError(f"Column '{requested}' not found. Available headers: {pretty}")

def translate_csv(in_path: str, out_path: str, column: str, output_column: str = "translated"):
    with open(in_path, newline='', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        fieldnames_in = reader.fieldnames or []
        # Resolve the requested column against actual headers
        resolved_col = _resolve_column_name(column, fieldnames_in)
        rows = []
        for row in reader:
            raw = (row.get(resolved_col) or "").strip()
            try:
                row[output_column] = translate_cell(raw)
            except Exception as e:
                row[output_column] = f"[parse error] {e}"
            rows.append(row)
    # Preserve original header order and append output column if needed
    fieldnames_out = fieldnames_in.copy()
    if output_column not in fieldnames_out:
        fieldnames_out.append(output_column)
    with open(out_path, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames_out)
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Translate GDF time-domain expressions to readable text.")
    p.add_argument("input_csv", help="Path to input CSV")
    p.add_argument("column", nargs="+", help="Column name containing GDF expressions (can include spaces)")
    p.add_argument("-o", "--output-csv", default="translated.csv", help="Where to write output CSV")
    p.add_argument("--out-col", default="translated", help="Name of the new translated column")
    args = p.parse_args()
    # Allow column names with spaces passed without shell quotes
    args.column = " ".join(args.column)
    translate_csv(args.input_csv, args.output_csv, args.column, args.out_col)