# dailyApps

Interactive apps shipped from Slack `#dailyApps` via local LLMs (tireless-router).

## Flow

1. Post a prompt in Slack `#dailyApps`
2. Objective runner breaks work into subtasks
3. Best-of-N local LLM loops + quality/anti-slop gates
4. App lands in `apps/<slug>/` and deploys to GitHub Pages

## Ops

```powershell
# From tirelessLocalLLM workspace
python -m tireless --setup-dailyapps
python -m tireless --dailyapps-live-tests
python -m tireless --serve-slack-bot
```

## GitHub Pages

```powershell
cd dailyApps
gh auth login
gh repo create dailyApps --public --source=. --remote=origin --push
# Enable Pages: Settings → Pages → GitHub Actions (workflow pages.yml)
```

Public URL shape: `https://<user>.github.io/dailyApps/apps/<slug>/`
