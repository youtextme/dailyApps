# Agent instructions (dailyApps)

## Project

Static HTML apps under `apps/<slug>/`, deployed via GitHub Pages. Prompts originate in Slack `#dailyApps` via tireless-router (separate repo).

## Secrets

**Never commit or echo secret values.** Read names from `.env.example` only.

Required for Slack bot work:

- `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_SIGNING_SECRET`

Check availability without printing values:

```bash
./scripts/check-secrets.sh
```

Full setup: [docs/SECRETS.md](docs/SECRETS.md)

## Cursor Cloud specific instructions

- Secrets are injected via [Cursor Cloud Agents → Secrets](https://cursor.com/dashboard/cloud-agents), not from this repo.
- Use **Runtime Secret** for Slack tokens and API keys.
- Environment config lives in `.cursor/environment.json` (no secrets in that file).
- After rotating secrets, start a new cloud agent run.

## Devin specific instructions

- Add the same variable names as Raw Secrets at [app.devin.ai/secrets](https://app.devin.ai/secrets) (org or repo scope).
- Optional: user maintains `.envrc` from `.envrc.example` (gitignored).
- New Devin sessions only see secrets added before session creation.

## Quality

Follow [quality/ANTI_SLOP.md](quality/ANTI_SLOP.md) for shipped apps.
