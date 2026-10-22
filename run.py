"""Fetch questions.csv, answer every round not yet answered, write answers/round-NNNN.json.

Rounds released within the last REVISE_HOURS are re-solved on every run, so a
question corrected upstream, or a round that was only partly published when we
first saw it, gets fixed while that round can still be resubmitted. A row that
can't be read is skipped with a warning instead of stopping the other rounds.

Usage: python3 run.py [--all]   (--all rewrites every round, not just missing ones)
"""
import csv, io, json, os, sys, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from solver import solve

URL = "https://raw.githubusercontent.com/FaisalXL/dso429-hourly-quiz/main/questions.csv"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "answers")
REVISE_HOURS = 3
OPTION_KEYS = ("option_a", "option_b", "option_c", "option_d")


def parse_time(s):
    try:
        t = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def parse_int(s):
    try:
        return int(float(s.strip()))
    except (AttributeError, ValueError, OverflowError):
        return None


def fetch_questions():
    """Yield (round_id, q_index, released_at, question_text, options) for every readable row."""
    req = urllib.request.Request(URL, headers={"Cache-Control": "no-cache"})
    raw = urllib.request.urlopen(req, timeout=60).read()
    text = raw.decode("utf-8-sig", errors="replace").replace("\x00", "")
    for r in csv.DictReader(io.StringIO(text)):
        rid, q = parse_int(r.get("round_id")), parse_int(r.get("q_index"))
        if rid is None or q is None or not 1 <= q <= 25:
            print(f"WARN skipping unreadable row: {list(r.values())[:3]}", file=sys.stderr)
            continue
        opts = [r.get(k) or "" for k in OPTION_KEYS]
        yield rid, q, parse_time(r.get("released_at")), r.get("question_text") or "", opts


def main():
    rewrite_all = "--all" in sys.argv
    now = datetime.now(timezone.utc)
    rounds = defaultdict(dict)
    released = {}
    for rid, q, rel, text, opts in fetch_questions():
        if released.get(rid) is None:
            released[rid] = rel
        letter, confident = solve(text, opts)
        if not confident:
            print(f"WARN round {rid} q{q}: low confidence ({letter})", file=sys.stderr)
        rounds[rid][q] = letter or "A"
    os.makedirs(OUT, exist_ok=True)
    written = []
    for rid in sorted(rounds):
        path = os.path.join(OUT, f"round-{rid:04d}.json")
        # A round whose release time can't be read is always re-solved; that only costs a no-op write.
        recent = released[rid] is None or now - released[rid] < timedelta(hours=REVISE_HOURS)
        if os.path.exists(path) and not (rewrite_all or recent):
            continue
        if len(rounds[rid]) < 25:
            print(f"WARN round {rid}: only {len(rounds[rid])} of 25 questions published so far", file=sys.stderr)
        answers = {f"q{i}": rounds[rid].get(i, "A") for i in range(1, 26)}
        content = json.dumps({"round_id": rid, "answers": answers}, indent=2) + "\n"
        if os.path.exists(path):
            with open(path) as f:
                if f.read() == content:
                    continue
        with open(path, "w") as f:
            f.write(content)
        written.append(rid)
    print(f"wrote {len(written)} rounds: {written}")


if __name__ == "__main__":
    main()
