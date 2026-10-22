"""Report when each graded round's answer file reached GitHub, and its timing credit.

Push times come from GitHub's repository activity API (the times GitHub records
for each push, which is what grading uses); the local git history shows which
answer files each push changed.

Usage: python3 status.py           print the report
       python3 status.py --write   also write STATUS.md (the cloud job does this)
"""
import json, os, re, subprocess, sys, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from run import fetch_questions
from solver import solve

REPO = os.environ.get("GITHUB_REPOSITORY", "kirtisub/homework-3")
HERE = os.path.dirname(os.path.abspath(__file__))
FIRST_GRADED, LAST_GRADED, DROPPED = 49, 168, 6
PT = timezone(timedelta(hours=-7), "PDT")  # every assignment date falls in PDT


def parse_time(s):
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))


def credit(hours):
    if hours <= 3:
        return 1.0
    if hours >= 12:
        return 0.0
    return round(1.0 - 0.1 * (int(hours - 3) + 1), 1)


def api(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "X-GitHub-Api-Version": "2022-11-28"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp), resp.headers.get("Link", "")


def pushes():
    url = (f"https://api.github.com/repos/{REPO}/activity"
           "?ref=refs/heads/main&activity_type=push&per_page=100")
    out = []
    while url:
        data, link = api(url)
        out += data
        m = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = m.group(1) if m else None
    return out


def git(*args):
    return subprocess.run(["git", "-C", HERE, *args], capture_output=True, text=True)


def answer_files_changed(before, after):
    r = git("diff", "--name-only", before, after, "--", "answers")
    if r.returncode:
        return []
    return [int(m.group(1)) for m in re.finditer(r"answers/round-(\d+)\.json", r.stdout)]


def fmt(t):
    t = t.astimezone(PT)
    return t.strftime("%b %d %I:%M %p").replace(" 0", " ")


def fmt_delay(td):
    minutes = max(0, int(td.total_seconds() // 60))
    return f"{minutes // 60} h {minutes % 60:02d} m"


def build():
    git("fetch", "-q", "origin", "main")
    released, unsure = {}, defaultdict(list)
    for rid, q, rel, text, opts in fetch_questions():
        if released.get(rid) is None:
            released[rid] = rel
        if not solve(text, opts)[1]:
            unsure[rid].append(q)

    received = defaultdict(list)  # round -> [(push time, who pushed)]
    for p in pushes():
        when = parse_time(p["timestamp"])
        for rid in answer_files_changed(p["before"], p["after"]):
            received[rid].append((when, p["actor"]["login"] if p.get("actor") else "?"))
    on_main = set(int(m.group(1)) for m in re.finditer(
        r"round-(\d+)\.json", git("ls-tree", "--name-only", "origin/main", "answers/").stdout))

    rows, credits, waiting = [], {}, []
    for rid in range(LAST_GRADED, FIRST_GRADED - 1, -1):
        if rid not in released:
            continue
        rel = released[rid]
        got = sorted(received.get(rid, []))
        if rel is None:
            state = "on GitHub" if rid in on_main else "**not pushed yet**"
            if rid not in on_main:
                waiting.append(rid)
            rows.append(f"| {rid} | unreadable release time | {state} | | | |")
            continue
        if not got:
            state = "on main, waiting for GitHub's push record" if rid in on_main else "**not pushed yet**"
            waiting.append(rid)
            rows.append(f"| {rid} | {fmt(rel)} | {state} | | | |")
            continue
        within = [g for g in got if g[0] - rel <= timedelta(hours=3)]
        when, who = within[-1] if within else got[0]
        c = credit((when - rel).total_seconds() / 3600)
        credits[rid] = c
        rows.append(f"| {rid} | {fmt(rel)} | {fmt(when)} | {who} | {fmt_delay(when - rel)} | {c:.0%} |")

    graded_released = [r for r in released if FIRST_GRADED <= r <= LAST_GRADED]
    unreleased = (LAST_GRADED - FIRST_GRADED + 1) - len(graded_released)
    best = sorted(list(credits.values()) + [1.0] * (len(waiting) + unreleased), reverse=True)
    best_final = sum(best[:len(best) - DROPPED]) / (len(best) - DROPPED)
    full = sum(1 for c in credits.values() if c == 1.0)
    partial = sum(1 for c in credits.values() if 0 < c < 1)
    zero = sum(1 for c in credits.values() if c == 0)
    attention = [f"- Round {r}: not on GitHub yet" for r in waiting if r not in on_main]
    attention += [f"- Round {r}: solver unsure about questions {', '.join(map(str, q))}"
                  for r, q in sorted(unsure.items()) if r >= FIRST_GRADED]

    lines = [
        "# Hourly quiz status",
        "",
        "Generated by `status.py` from GitHub's own push records. Times are Pacific (PDT).",
        "Rows pushed by `github-actions[bot]` were answered and pushed by the cloud job, with no laptop involved.",
        "",
        f"- Newest round released: **{max(released, default='none')}** · newest answer file on GitHub: **{max(on_main, default='none')}**",
        f"- Graded rounds released: **{len(graded_released)} of {LAST_GRADED - FIRST_GRADED + 1}**",
        f"- Within 3 hours (full credit): **{full}** · partial credit: **{partial}** · zero credit: **{zero}** · waiting: **{len(waiting)}**",
        f"- Best possible final grade (every answer correct, every remaining round on time, lowest {DROPPED} dropped): **{best_final:.1%}**",
        "",
        "## Needs attention",
        "",
        *(attention or ["Nothing."]),
        "",
        "## Rounds",
        "",
        "| Round | Released | Graded push | Pushed by | After release | Timing credit |",
        "|---|---|---|---|---|---|",
        *rows,
        "",
    ]
    return "\n".join(lines)


def main():
    report = build()
    if "--write" in sys.argv:
        with open(os.path.join(HERE, "STATUS.md"), "w") as f:
            f.write(report)
    print(report)


if __name__ == "__main__":
    main()
