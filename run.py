"""Fetch questions.csv, answer every round not yet answered, write answers/round-NNNN.json.

Usage: python3 run.py [--all]   (--all rewrites every round, not just missing ones)
"""
import csv, io, json, os, sys, urllib.request
from collections import defaultdict
from solver import solve

URL = "https://raw.githubusercontent.com/FaisalXL/dso429-hourly-quiz/main/questions.csv"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "answers")


def main():
    rewrite = "--all" in sys.argv
    req = urllib.request.Request(URL, headers={"Cache-Control": "no-cache"})
    text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    rounds = defaultdict(dict)
    for r in csv.DictReader(io.StringIO(text)):
        opts = [r["option_a"], r["option_b"], r["option_c"], r["option_d"]]
        letter, confident = solve(r["question_text"], opts)
        if not confident:
            print(f"WARN round {r['round_id']} q{r['q_index']}: low confidence ({letter})", file=sys.stderr)
        rounds[int(r["round_id"])][int(r["q_index"])] = letter or "A"
    os.makedirs(OUT, exist_ok=True)
    written = []
    for rid in sorted(rounds):
        path = os.path.join(OUT, f"round-{rid:04d}.json")
        if os.path.exists(path) and not rewrite:
            continue
        answers = {f"q{i}": rounds[rid].get(i, "A") for i in range(1, 26)}
        with open(path, "w") as f:
            json.dump({"round_id": rid, "answers": answers}, f, indent=2)
            f.write("\n")
        written.append(rid)
    print(f"wrote {len(written)} rounds: {written}")


if __name__ == "__main__":
    main()
