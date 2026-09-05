# Secrets management (Cursor, Devin, local dev)

This repo uses a **single contract** for secret names (`.env.example`) and **three injection points** for values. Real tokens never go in git.

## Quick start

1. Copy the contract: `cp .env.example .env.local`
2. Obtain Slack tokens (see below) and paste into `.env.local`
3. Register the same names in [Cursor Cloud Secrets](https://cursor.com/dashboard/cloud-agents) and [Devin Secrets](https://app.devin.ai/secrets)
4. Verify: `./scripts/check-secrets.sh`

## Slack tokens (bot + app)

Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps):

| Secret | Where to get it | Format |
|--------|-----------------|--------|
| `SLACK_BOT_TOKEN` | **OAuth & Permissions** → Install to workspace → **Bot User OAuth Token** | `xoxb-...` |
| `SLACK_APP_TOKEN` | **Basic Information** → **App-Level Tokens** → Create with scope `connections:write` (Socket Mode) | `xapp-...` |
| `SLACK_SIGNING_SECRET` | **Basic Information** → **Signing Secret** | hex string |

Recommended bot scopes for dailyApps / tireless-router:

- `app_mentions:read`, `channels:history`, `channels:read`, `chat:write`, `files:read`, `reactions:write`

Enable **Socket Mode** under **Settings → Socket Mode** and use the app token above.

Invite the bot to `#dailyApps` (or set `SLACK_CHANNEL_ID`).

## Where to store values

| Context | Store values in | Type / notes |
|---------|-----------------|--------------|
| **Local Cursor IDE** | `.env.local` (gitignored) | Loaded by your shell or tireless; never commit |
| **Cursor Cloud Agents** | [Dashboard → Cloud Agents → Secrets](https://cursor.com/dashboard/cloud-agents) | Use **Runtime Secret** for tokens (redacted in transcripts). Scope to this repo or environment. |
| **Devin** | [app.devin.ai/secrets](https://app.devin.ai/secrets) | **Organization** or **Repository** scope; one Raw Secret per variable name |
| **Devin (optional direnv)** | `.envrc` (gitignored) | `export SLACK_BOT_TOKEN=...` — see `.envrc.example` |

### Cursor Cloud secret types

- **Runtime Secret** — API keys, Slack tokens, DB passwords. Process can read `$VAR`; model sees `[REDACTED]`.
- **Environment Variable** — non-sensitive config only (`TIRELESS_ROUTER_URL`, public URLs).
- **Build Secret** — install-time only (private npm/PyPI); not available at agent runtime.

After adding or rotating secrets in Cursor or Devin, **start a new agent session** so injection picks up changes.

## Adding a new secret (standard for all repos)

1. Add the variable name and placeholder to `.env.example` with a short comment.
2. If required for Slack bot or CI, add the name to `REQUIRED` in `scripts/check-secrets.sh`.
3. Add the real value to:
   - `.env.local` (local)
   - Cursor Cloud Secrets (Runtime Secret)
   - Devin Secrets (Raw Secret, org or repo scope)
4. Do **not** add values to `.cursor/environment.json`, README, or committed files.

## Security rules

- `.env.local`, `.env`, `.envrc` are in `.gitignore`.
- `.cursorignore` blocks agents from indexing env files.
- Never paste tokens in issues, PRs, or agent prompts.
- Rotate at [api.slack.com](https://api.slack.com/apps) if a token was exposed.
- Prefer a dedicated Slack app for agents (not personal user tokens).

## tireless-router integration

From the **tirelessLocalLLM** workspace:

```powershell
python -m tireless --setup-dailyapps
python -m tireless --serve-slack-bot
```

Ensure `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, and `SLACK_SIGNING_SECRET` are in the environment (via `.env.local` locally, or dashboard secrets in cloud).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Cloud agent can't reach Slack | Confirm secrets are **Runtime Secret**, repo scope includes `dailyApps`, new session started |
| Devin missing vars | Secret added **before** session start; check org vs repo scope |
| `./scripts/check-secrets.sh` fails locally | Fill `.env.local` from `.env.example` |
| Stale token after rotation | Update all three stores (local, Cursor, Devin) and restart sessions |
