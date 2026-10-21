"""Deterministic solver for the DSO 429 hourly quiz question templates."""
import re
from datetime import date, timedelta

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}


def num(s):
    return float(s.replace("$", "").replace(",", "").replace("%", "").replace("units", "").strip())


def nums(text):
    return [num(m) for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]


def parse_date(s):
    d, m, y = s.strip().split()
    return date(int(y), MONTHS[m], int(d))


def compute(q):
    """Return the expected value for a question (a number or a date), or None."""
    t = q
    n = nums(t)
    if "compounded" in t:
        p, r, years = n[0], n[1] / 100, n[2]
        per = {"annually": 1, "semi-annually": 2, "semiannually": 2, "quarterly": 4,
               "monthly": 12, "daily": 365}
        k = next((v for w, v in per.items() if f"compounded {w}" in t), 1)
        return p * (1 + r / k) ** (k * years)
    if "gross margin" in t:
        rev, cogs = n[0], n[1]
        return (rev - cogs) / rev * 100
    if "discounted by" in t:
        return n[0] * (1 - n[1] / 100)
    if "euros per US dollar" in t or "per US dollar" in t:
        return n[0] * n[1]
    if "break even" in t:
        fixed, price, var = n[0], n[1], n[2]
        return round(fixed / (price - var))
    if "overall average" in t:
        n1, a1, n2, a2 = n[0], n[1], n[2], n[3]
        return (n1 * a1 + n2 * a2) / (n1 + n2)
    if "total revenue" in t:
        return n[0] * n[1]
    if "percentage change" in t:
        return (n[1] - n[0]) / n[0] * 100
    if "probability" in t:
        return n[0] / (n[0] + n[1] + n[2]) * 100
    if "ratio" in t and "split" in t:
        total = n[0]
        a, b = map(int, re.search(r"ratio (\d+):(\d+)", t).groups())
        return total * a / (a + b)
    if "series runs" in t:
        seq = [int(x) for x in re.search(r"runs ([\d, ]+?)\. ", t).group(1).split(",")]
        d = [b - a for a, b in zip(seq, seq[1:])]
        if len(set(d)) == 1:
            return seq[-1] + d[0]
        if all(a and b % a == 0 for a, b in zip(seq, seq[1:])) and len({b // a for a, b in zip(seq, seq[1:])}) == 1:
            return seq[-1] * (seq[1] // seq[0])
        dd = [b - a for a, b in zip(d, d[1:])]
        if len(set(dd)) == 1:
            return seq[-1] + d[-1] + dd[0]
        return None
    if "settlement period" in t:
        m = re.search(r"signed on (\d+ \w+ \d{4}) has a (\d+)-day", t)
        return parse_date(m.group(1)) + timedelta(days=int(m.group(2)))
    return None


def solve(q, options):
    """Pick the option letter closest to the computed value. Returns (letter, confident)."""
    letters = "ABCD"
    v = compute(q)
    if v is None:
        return None, False
    if isinstance(v, date):
        for L, o in zip(letters, options):
            try:
                if parse_date(o) == v:
                    return L, True
            except Exception:
                pass
        return None, False
    vals = []
    for o in options:
        try:
            vals.append(num(o))
        except ValueError:
            vals.append(float("inf"))
    diffs = [abs(x - v) for x in vals]
    best = min(range(4), key=lambda i: diffs[i])
    tol = max(0.06 if "%" in options[best] else 0.011, abs(v) * 0.002)
    return letters[best], diffs[best] <= tol
