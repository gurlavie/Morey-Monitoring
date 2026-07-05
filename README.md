# Moiry Watch — Cabane de Moiry availability monitor

Monitors availability for **18 & 19 September 2026** via the hut's public
availability API (no login, no credentials, no secrets). Alerts by opening a
GitHub issue, which GitHub emails to you.

- 🚨 Issue when **Sept 19 opens** (currently full — hunting 3 places)
- ⚠️ Issue when **Sept 18 counts change**
- Silent otherwise; history appended to `log.csv` on each change

## Setup (~3 minutes)

1. Create a **public** repo on github.com (e.g. `moiry-watch`). Public = free
   unlimited Actions minutes; there are no secrets in this code.
2. Upload the contents of this folder to the repo root, keeping the structure:
   - `monitor.py`, `state.json`, `README.md`
   - `.github/workflows/monitor.yml` (create the folders via "Add file → Create
     new file" and type `.github/workflows/monitor.yml` as the name)
3. Go to the **Actions** tab and enable workflows if prompted.
4. Click the "Moiry availability watch" workflow → **Run workflow** to test.
   The run log should print a line like `sept18=65+19 sept19=0+0`.
5. Make sure you get emails: repo **Watch → All Activity**, and in
   github.com/settings/notifications have "Issues" email notifications on.
   For a louder ping, install the GitHub mobile app (push notifications).

## How it works

- GitHub cron fires every 5 minutes (its minimum); each job then checks
  5 times with 60-second sleeps → effectively ~every minute.
- Note: GitHub schedules are not exact — runs can be delayed a few minutes
  during busy periods. `concurrency` prevents overlapping jobs.
- State is committed back to the repo only when counts change.

## Stopping it

Actions tab → "Moiry availability watch" → ⋯ menu → **Disable workflow**.
Scheduled workflows also auto-disable after 60 days without repo activity —
irrelevant here (season ends before that), but good to know.

## Test locally (optional)

```bash
python3 monitor.py   # prints counts; skips issue creation without GITHUB_TOKEN
```
