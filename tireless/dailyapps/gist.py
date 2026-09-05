"""Build narrative gist — tenets, tests, CX evolution — not a random dump."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from tireless.config import GISTS_DIR, GitHubConfig, ensure_dirs
from tireless.models import BuildGist, Session, TestCase


def build_gist_markdown(session: Session) -> BuildGist:
    objective = session.objective
    arts = session.artifacts
    unit = [TestCase.model_validate(t) for t in arts.get("unit_tests") or []]
    integ = [TestCase.model_validate(t) for t in arts.get("integration_tests") or []]
    prod = [TestCase.model_validate(t) for t in arts.get("production_tests") or []]

    tenets = [str(t) for t in (arts.get("tenets") or [])]
    cx_evolution = []
    if objective:
        cx_evolution.append(f"Initial thought: {session.root_prompt}")
        cx_evolution.append(f"Objective refined to: {objective.end_goal}")
        cx_evolution.append(f"Success definition: {objective.success_definition}")
    for i, fb in enumerate(session.feedback_history, start=1):
        cx_evolution.append(f"Iteration {i} feedback applied: {fb}")
    if arts.get("cx_notes"):
        cx_evolution.append(f"Latest CX: {arts['cx_notes']}")

    loops_run = [
        f"Loop {l.index}: {l.name} — {l.status.value} — {l.summary or l.purpose}"
        for l in session.loops
    ]
    guardrails = [
        "Stateful loops with objective exit criteria (not prompt theater)",
        "Quality gate rejects thin stubs and banned aesthetics",
        "Tests record evidence; theoretical green is treated as fail",
        "Slack updates stay short; details live in this gist",
    ]

    objectives = []
    if objective:
        objectives.append(objective.end_goal)
        objectives.extend(f"KR: {kr.description} ({kr.metric} → {kr.target})" for kr in objective.key_results)

    gist = BuildGist(
        title=session.title or session.slug or "dailyApps build",
        objectives=objectives,
        building_tenets=tenets,
        loops_run=loops_run,
        unit_tests=unit,
        integration_tests=integ,
        production_tests=prod,
        cx_evolution=cx_evolution,
        guardrails=guardrails,
        app_url=session.app_url,
    )
    gist.markdown = _render(gist, session)
    return gist


def persist_gist(session: Session, gist: BuildGist) -> BuildGist:
    ensure_dirs()
    GISTS_DIR.mkdir(parents=True, exist_ok=True)
    local = GISTS_DIR / f"{session.objective_id}.md"
    local.write_text(gist.markdown, encoding="utf-8")
    # also keep machine-readable sidecar
    (GISTS_DIR / f"{session.objective_id}.json").write_text(
        gist.model_dump_json(indent=2),
        encoding="utf-8",
    )
    gist.local_path = str(local)

    gh = GitHubConfig.from_env()
    if gh.configured:
        try:
            url = _publish_github_gist(gh, gist)
            gist.url = url
        except Exception:  # noqa: BLE001
            gist.url = local.as_uri()
    else:
        gist.url = local.as_uri()

    session.gist = gist
    session.artifacts["gist_url"] = gist.url
    session.artifacts["gist_path"] = gist.local_path
    return gist


def _publish_github_gist(gh: GitHubConfig, gist: BuildGist) -> str:
    payload = {
        "description": f"dailyApps build — {gist.title}",
        "public": gh.gist_public,
        "files": {
            "BUILD.md": {"content": gist.markdown},
        },
    }
    with httpx.Client(timeout=30) as client:
        r = client.post(
            "https://api.github.com/gists",
            headers={
                "Authorization": f"Bearer {gh.token}",
                "Accept": "application/vnd.github+json",
            },
            json=payload,
        )
        r.raise_for_status()
        return r.json()["html_url"]


def _render(gist: BuildGist, session: Session) -> str:
    def tests_md(tests: list[TestCase]) -> str:
        if not tests:
            return "_None_\n"
        lines = []
        for t in tests:
            lines.append(
                f"- **{t.name}** ({t.kind}): {t.result} — expected `{t.expected}` — evidence: {t.evidence}"
            )
        return "\n".join(lines) + "\n"

    return f"""# {gist.title}

Objective id: `{session.objective_id}`

## What we were building toward
{chr(10).join(f'- {o}' for o in gist.objectives) or '- (none)'}

## Building tenets
{chr(10).join(f'- {t}' for t in gist.building_tenets) or '- (none)'}

## Loops run
{chr(10).join(f'- {x}' for x in gist.loops_run) or '- (none)'}

## Guardrails (real, not theoretical)
{chr(10).join(f'- {g}' for g in gist.guardrails)}

## Unit tests
{tests_md(gist.unit_tests)}
## Integration tests
{tests_md(gist.integration_tests)}
## Production tests
{tests_md(gist.production_tests)}

## Customer experience evolution
{chr(10).join(f'- {c}' for c in gist.cx_evolution) or '- (none)'}

## Output
- App: {gist.app_url or session.app_url or '(pending)'}
- Slug: `{session.slug}`
"""
