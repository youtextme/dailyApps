# dailyApps

Tiny interactive pages shipped from Slack **#dailyapps** via **stateful objective loops** and local LLMs (tireless-router / Ollama).

This repo is both the GitHub Pages catalog (`apps/<slug>/`) and the `tireless` engine that runs the loops.

Live: https://youtextme.github.io/dailyApps/

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
2. Bot acknowledges and starts a **stateful** objective loop (not a one-shot prompt)
3. **Loop 1 / stage setting** — Loop Builder + OKR Creator define the end goal, key results, later loops, exit criteria, and what each state update means
4. Later loops run with recruited consultants (behaviors, not static rule sheets):
   - **Barbara Minto Researcher** — MECE mental model + gap analysis
   - **UI/UX/CX Builder** — remove everything that does not help the customer finish the job
   - **Test Engineer** — unit / integration / production / CX tests with real evidence
   - **Slack Communicator** — ~15 word status + link after every state
5. App lands in `apps/<slug>/`, catalog refreshes, build gist narrates tenets / tests / CX evolution
6. Reply in the same Slack thread to iterate — session context is reloaded (same `objective_id`)
7. Up to **20** prompts process in parallel, each with its own session

## Ops

```bash
python -m pip install -e ".[dev,slack]"
cp .env.example .env.local   # fill Slack + local LLM endpoints
```

From the tirelessLocalLLM workspace (legacy runner):

```powershell
python -m tireless --setup-dailyapps
python -m tireless --dailyapps-live-tests
python -m tireless --run-prompt "build a tip calculator that splits bills" --offline
python -m tireless --serve-slack-bot
```

### Local LLM

Point `TIRELESS_LLM_BASE_URL` at any OpenAI-compatible server (Ollama default `http://127.0.0.1:11434/v1`).  
If the router is down, `--offline` uses deterministic loop fallbacks so the state machine still exercises end-to-end.

### Slack

Socket Mode: `SLACK_BOT_TOKEN` + `SLACK_APP_TOKEN`.  
Top-level messages start sessions; thread replies reload the prior session and continue the loops.

### Secrets

All agents (Cursor IDE, Cursor Cloud, Devin) use the same variable names from `.env.example`. Values live in `.env.local` locally and in each platform's secrets dashboard — never in git.

```bash
cp .env.example .env.local   # fill Slack bot/app tokens + signing secret
./scripts/check-secrets.sh
```

## Pages

Push to `main` deploys with `.github/workflows/pages.yml`.

Public URL shape: `https://youtextme.github.io/dailyApps/apps/<slug>/`

## Package layout

```
tireless/
  roles/          # Loop Builder, OKR, Minto, UX/CX, Test, Slack Communicator
  loops/engine.py # stateful objective loop runner
  slack/bot.py    # Slack ingress + parallel sessions
  dailyapps/      # quality_gate, shipper, gist, catalog
  llm/client.py   # local OpenAI-compatible client
```