#!/bin/bash
# Local backup for the GitHub Actions workflow: answer any new rounds and push.
cd "$(dirname "$0")" || exit 1
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin"
echo "=== $(date -u +%FT%TZ)"
git pull -q --rebase origin main || exit 1
/usr/bin/python3 run.py || exit 1
git add answers
if git diff --cached --quiet; then echo "nothing new"; exit 0; fi
git commit -q -m "Answer new rounds (local)"
git push -q origin main && echo "pushed"
