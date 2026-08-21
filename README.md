# dailyApps

Tiny interactive pages shipped from Slack **#dailyapps**.

Live: https://youtextme.github.io/dailyApps/

Repo: https://github.com/youtextme/dailyApps

## How to use the Slack channel (never-ending session)

The channel is the project. It does not expire.

1. **Start a job** — top-level message that @mentions OpenClaw with one outcome.
2. **Walk away** — OpenClaw works in a **thread**. That thread is its own session.
3. **Answer only if asked** — reply in the same thread. You do not need to @mention again.
4. **Start another job in parallel** — another top-level @mention. New thread, new session, same channel.

Do not pile three features into one message if you want them in parallel.

### Good job

```text
@OpenClaw Build a page that explains dailyApps. Put it in apps/what-is-dailyapps/. Reply here when live.
```

### Bad job

```text
@OpenClaw do the readme and xyz and the explain page
```

That is one session, not three.

## What already ships here

- [What is dailyApps](https://youtextme.github.io/dailyApps/apps/what-is-dailyapps/) — the explain page
- [XYZ](https://youtextme.github.io/dailyApps/apps/xyz/) — toggle X / Y / Z
- Older Slack-shipped apps under `apps/`

## Flow (agent)

1. Post one outcome in #dailyapps (@OpenClaw)
2. Agent uses the same review bar as Cursor (Outcome OS, Ralph-sized stories, code review, verify)
3. Page lands in `apps/<slug>/` and deploys via GitHub Pages

## Ops

```powershell
# From tirelessLocalLLM workspace (legacy runner)
python -m tireless --setup-dailyapps
python -m tireless --dailyapps-live-tests
python -m tireless --serve-slack-bot
```

OpenClaw on this machine is the current Slack agent (local Ollama + GitHub MCP). Tireless remains available as the older loop.

## Pages

Push to `main` deploys with `.github/workflows/pages.yml`.

Public URL shape: `https://youtextme.github.io/dailyApps/apps/<slug>/`
