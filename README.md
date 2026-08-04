# dailyApps

Interactive apps shipped from Slack `#dailyApps` via local LLMs (tireless-router).

## Flow

1. Post a prompt in Slack `#dailyApps`
2. Objective runner breaks work into subtasks
3. Best-of-N local LLM loops + quality/anti-slop gates
4. App lands in `apps/<slug>/` and deploys to GitHub Pages

## Secrets (Slack, GitHub, LLM keys)

All agents (Cursor IDE, Cursor Cloud, Devin) use the same variable names from `.env.example`. Values live in `.env.local` locally and in each platform’s secrets dashboard — never in git.

```bash
cp .env.example .env.local   # fill Slack bot/app tokens + signing secret
./scripts/check-secrets.sh
```

See [docs/SECRETS.md](docs/SECRETS.md) for Slack app setup and Cursor/Devin registration.

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
