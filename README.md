# homework-3

DSO 429 Homework 3, The Hourly Quiz. One answer file per round in [`answers/`](answers/).

**Live status:** [STATUS.md](STATUS.md) lists every graded round, when GitHub received its answers, and who pushed them.

## How it works

- [`solver.py`](solver.py) computes each question's answer and picks the matching option. It answers all 1,200 practice questions correctly ([`check_practice.py`](check_practice.py)).
- [`run.py`](run.py) downloads the latest `questions.csv` and writes `answers/round-NNNN.json` for every round not yet answered. Rounds released in the last 3 hours are re-solved on every run.
- Two GitHub Actions chains, [`answer.yml`](.github/workflows/answer.yml) and [`answer-backup.yml`](.github/workflows/answer-backup.yml), run `run.py` every 4 minutes on GitHub's servers and push new answers. Each run lasts about 5h40m and queues its own successor. They stop once round 168 is in.
- [`status.py`](status.py) builds STATUS.md from GitHub's push records.
- [`local_push.sh`](local_push.sh) does the same job from a laptop, as a manual fallback.
