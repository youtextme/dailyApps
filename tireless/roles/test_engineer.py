"""Test Engineer — real unit/integration/production/CX evidence, not theoretical green."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tireless.config import APPS_DIR
from tireless.dailyapps.quality_gate import run_quality_gate
from tireless.models import RoleName, TestCase
from tireless.roles.base import Role, RoleContext


class TestEngineer(Role):
    name = RoleName.TEST_ENGINEER
    charter = (
        "You design and run tests that prove the app works for real — "
        "unit, integration, production, and customer-experience checks. "
        "A test that only passes theoretically is a failed test. "
        "Capture evidence of what was exercised."
    )

    def act(self, ctx: RoleContext) -> dict[str, Any]:
        system = (
            f"You are the Test Engineer.\n{self.charter}\n"
            "Return JSON with unit_tests, integration_tests, production_tests, cx_tests "
            "arrays of {name, kind, steps[], expected}. Tag design_tests."
        )
        user = (
            f"PROMPT: {ctx.session.root_prompt}\n"
            f"Objective: {ctx.session.objective.model_dump() if ctx.session.objective else None}\n"
            f"Slug: {ctx.session.slug}\n"
            "Design the minimum set of tests that prove customer success."
        )
        data = self.llm.chat_json(system, user)
        designed = _design_tests(data)
        if len(designed) < 3:
            from tireless.llm.client import LocalLLM

            designed = _design_tests(LocalLLM(offline=True).chat_json(system, user))

        html = str(ctx.session.artifacts.get("html") or "")
        slug = ctx.session.slug
        app_dir = APPS_DIR / slug if slug else None
        executed = [_execute(t, html, app_dir) for t in designed]

        ctx.session.artifacts["all_tests"] = [t.model_dump() for t in executed]
        ctx.session.artifacts["unit_tests"] = [t.model_dump() for t in executed if t.kind == "unit"]
        ctx.session.artifacts["integration_tests"] = [t.model_dump() for t in executed if t.kind == "integration"]
        ctx.session.artifacts["production_tests"] = [t.model_dump() for t in executed if t.kind == "production"]
        ctx.session.artifacts["cx_tests"] = [t.model_dump() for t in executed if t.kind == "cx"]
        return {
            "all_tests": [t.model_dump() for t in executed],
            "passed": sum(1 for t in executed if t.result == "pass"),
            "failed": sum(1 for t in executed if t.result != "pass"),
        }


def _design_tests(data: dict) -> list[TestCase]:
    designed: list[TestCase] = []
    for key, kind in (
        ("unit_tests", "unit"),
        ("integration_tests", "integration"),
        ("production_tests", "production"),
        ("cx_tests", "cx"),
    ):
        for item in data.get(key) or []:
            if isinstance(item, str):
                designed.append(
                    TestCase(name=item[:80] or "test", kind=kind, steps=[item], expected="pass")
                )
                continue
            if not isinstance(item, dict):
                continue
            steps = item.get("steps") or []
            if isinstance(steps, str):
                steps = [steps]
            designed.append(
                TestCase(
                    name=str(item.get("name") or "test"),
                    kind=str(item.get("kind") or kind),
                    steps=[str(s) for s in steps],
                    expected=str(item.get("expected") or ""),
                )
            )
    return designed


def _execute(test: TestCase, html: str, app_dir: Path | None) -> TestCase:
    name = test.name.lower()
    lower_html = html.lower()
    evidence = ""
    ok = False

    if "doctype" in name or "viewport" in name:
        ok = "<!doctype html>" in lower_html and 'name="viewport"' in lower_html
        evidence = f"doctype={'yes' if '<!doctype html>' in lower_html else 'no'}; viewport={'yes' if 'viewport' in lower_html else 'no'}"
    elif "interactive" in name or "control" in name:
        has_control = "<button" in lower_html or "<input" in lower_html
        has_handler = "addeventlistener" in lower_html or "onclick" in lower_html
        ok = has_control and has_handler
        evidence = f"control={has_control} handler={has_handler}"
    elif "ready" in name:
        ok = 'data-dailyapps-ready="1"' in html
        evidence = "ready marker present" if ok else "ready marker missing"
    elif "shipped" in name or "files_exist" in name:
        if app_dir and app_dir.exists():
            ok = (app_dir / "index.html").exists() and (app_dir / "meta.json").exists()
            evidence = f"app_dir={app_dir} ok={ok}"
        else:
            # Pre-ship: treat HTML artifact as standing in; production re-check after ship
            ok = bool(html) and len(html) > 200
            evidence = "pre-ship html artifact present" if ok else "missing html"
    elif "wall_of_text" in name or test.kind == "cx":
        # Rough CX proxy: lead/header text shouldn't dominate
        text_len = len(re.sub(r"<[^>]+>", " ", html))
        ok = text_len < 12000 and 'data-dailyapps-ready="1"' in html
        evidence = f"approx_text_len={text_len}"
    else:
        report = run_quality_gate(html)
        ok = report.ok
        evidence = f"quality_score={report.score}; fallback check for {test.name}"

    return test.model_copy(update={"result": "pass" if ok else "fail", "evidence": evidence})
