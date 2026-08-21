# AGENTS.md — dailyApps

This workspace is `youtextme/dailyApps`. Slack home is **#dailyapps**.

Load skill `slack-jobs` on every Slack job. Then `outcome-os`. For multi-story features, `prd` then `ralph`. Before claiming done, `code-review-and-quality` and `verification-before-completion`.

## Slack is the job

The inbound text is the work. Do not narrate that you were mentioned. Use tools. Reply in the thread with evidence (paths, URLs, what to click). Ask only when blocked.

- New top-level @mention → new parallel job (new thread session)
- Reply in an existing thread → continue that job (no extra @mention)

## Ship shape

Pages live in `apps/<slug>/index.html` + `meta.json`. Must be interactive (button or input + handler). No Inter/Roboto. No purple/indigo hero. See `quality/ANTI_SLOP.md`. Update `index.html` and `README.md` when you add an app.

GitHub: `youtextme/dailyApps`. Pages: `https://youtextme.github.io/dailyApps/apps/<slug>/`
