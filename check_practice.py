"""Validate the solver against the published practice answer keys (rounds 1-48)."""
import csv, io, urllib.request
from solver import solve

BASE = "https://raw.githubusercontent.com/FaisalXL/dso429-hourly-quiz/main/"


def fetch(name):
    return list(csv.DictReader(io.StringIO(urllib.request.urlopen(BASE + name, timeout=60).read().decode("utf-8"))))


def main():
    keys = {(r["round_id"], r["q_index"]): r["answer"] for r in fetch("practice_keys.csv")}
    ok = bad = unconf = 0
    for r in fetch("questions.csv"):
        opts = [r["option_a"], r["option_b"], r["option_c"], r["option_d"]]
        letter, confident = solve(r["question_text"], opts)
        unconf += not confident
        k = (r["round_id"], r["q_index"])
        if k in keys:
            if letter == keys[k]:
                ok += 1
            else:
                bad += 1
                print("WRONG", k, letter, "key", keys[k], r["question_text"], opts)
    print(f"correct {ok}  wrong {bad}  low-confidence (all rounds) {unconf}")


if __name__ == "__main__":
    main()
