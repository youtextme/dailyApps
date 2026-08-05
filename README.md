# dailyApps

Interactive apps shipped from Slack `#dailyApps` via **stateful objective loops** and local LLMs (tireless-router / Ollama).

This repo is both the GitHub Pages catalog (`apps/<slug>/`) and the `tireless` engine that runs the loops.

## Flow

1. Post a prompt in Slack `#dailyApps` (or `python -m tireless --run-prompt "..."`)
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
cp .env.example .env   # fill Slack + local LLM endpoints

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

## GitHub Pages

Public URL shape: `https://<user>.github.io/dailyApps/apps/<slug>/`

Workflow: `.github/workflows/pages.yml` deploys the repo root on push to `main`.

## Package layout

```
tireless/
  roles/          # Loop Builder, OKR, Minto, UX/CX, Test, Slack Communicator
  loops/engine.py # stateful objective loop runner
  slack/bot.py    # Slack ingress + parallel sessions
  dailyapps/      # quality_gate, shipper, gist, catalog
  llm/client.py   # local OpenAI-compatible client
```
