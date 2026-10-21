"""Fetch questions.csv, answer every round not yet answered, write answers/round-NNNN.json.

Rounds released within the last REVISE_HOURS are re-solved on every run, so a
question corrected upstream, or a round that was only partly published when we
first saw it, gets fixed while that round can still be resubmitted.

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


def parse_time(s):
    try:
        return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def main():
    rewrite_all = "--all" in sys.argv
    now = datetime.now(timezone.utc)
    req = urllib.request.Request(URL, headers={"Cache-Control": "no-cache"})
    text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    rounds = defaultdict(dict)
    released = {}
    for r in csv.DictReader(io.StringIO(text)):
        rid = int(r["round_id"])
        released.setdefault(rid, parse_time(r["released_at"]))
        opts = [r["option_a"], r["option_b"], r["option_c"], r["option_d"]]
        letter, confident = solve(r["question_text"], opts)
        if not confident:
            print(f"WARN round {rid} q{r['q_index']}: low confidence ({letter})", file=sys.stderr)
        rounds[rid][int(r["q_index"])] = letter or "A"
    os.makedirs(OUT, exist_ok=True)
    written = []
    for rid in sorted(rounds):
        path = os.path.join(OUT, f"round-{rid:04d}.json")
        recent = released[rid] is not None and now - released[rid] < timedelta(hours=REVISE_HOURS)
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
