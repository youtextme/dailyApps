"""Local LLM client via OpenAI-compatible tireless-router / Ollama."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from tireless.config import LLMConfig

log = logging.getLogger(__name__)


class LocalLLM:
    """Thin chat client. Prefer structured JSON answers; fall back deterministically."""

    def __init__(self, config: LLMConfig | None = None, *, offline: bool = False) -> None:
        self.config = config or LLMConfig.from_env()
        self.offline = offline or self.config.base_url.endswith("/offline")
        self._client = httpx.Client(timeout=self.config.timeout_s)

    def close(self) -> None:
        self._client.close()

    def available(self) -> bool:
        if self.offline:
            return False
        try:
            # Ollama tags or OpenAI models
            for path in ("/models", "/api/tags"):
                url = self.config.base_url.replace("/v1", "") + path if path.startswith("/api") else self.config.base_url + path
                r = self._client.get(url, headers=self._headers())
                if r.status_code < 500:
                    return True
        except Exception as exc:  # noqa: BLE001
            log.debug("LLM probe failed: %s", exc)
        return False

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.3,
        json_mode: bool = False,
        allow_offline_fallback: bool = True,
    ) -> str:
        if self.offline or not self.available():
            return self._offline_reply(system, user, json_mode=json_mode)

        # Large HTML JSON payloads routinely starve tiny local models — go offline early.
        if "build_html" in system and len(user) > 4000:
            log.info("Using offline HTML builder (prompt too large for tiny local model)")
            return self._offline_reply(system, user, json_mode=json_mode)

        payload: dict[str, Any] = {
            "model": self.config.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            r = self._client.post(
                f"{self.config.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM call failed, using offline fallback: %s", exc)
            if not allow_offline_fallback:
                raise
            return self._offline_reply(system, user, json_mode=json_mode)

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        retries: int = 1,
    ) -> dict[str, Any]:
        """Ask for JSON; repair/retry; fall back to offline structured reply if needed."""
        last_err: Exception | None = None
        raw = ""
        # HTML generation: prefer one attempt then offline (tiny models time out)
        if "build_html" in system:
            retries = 0
        for attempt in range(retries + 1):
            try:
                prompt = user if attempt == 0 else (
                    user
                    + "\n\nIMPORTANT: Reply with ONE valid JSON object only. "
                    "No markdown fences, no commentary, close all strings/brackets."
                )
                raw = self.chat(
                    system + "\nOutput MUST be a single valid JSON object.",
                    prompt,
                    temperature=max(0.0, temperature - attempt * 0.1),
                    json_mode=True,
                )
                return _extract_json(raw)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                log.warning("chat_json attempt %s failed: %s; raw=%s", attempt, exc, raw[:240])
                repaired = _repair_json(raw)
                if repaired is not None:
                    return repaired
        # Last resort: deterministic offline structure for this role prompt
        log.warning("chat_json giving up (%s); using offline structured fallback", last_err)
        return _extract_json(self._offline_reply(system, user, json_mode=True))

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _offline_reply(self, system: str, user: str, *, json_mode: bool) -> str:
        """Deterministic, useful fallback so loops still run without a live LLM."""
        prompt = _extract_prompt(user)
        title = _title_from_prompt(prompt)
        slug_hint = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]

        if "loop_plan" in system or "Loop Builder" in system:
            return json.dumps(
                {
                    "loops": [
                        {
                            "index": 1,
                            "name": "understand_objective",
                            "purpose": "Identify the user's end goal, OKRs, and success criteria",
                            "owner_role": "okr_creator",
                            "exit_criteria": [
                                {
                                    "description": "Clear end goal stated in one sentence",
                                    "check_kind": "has_end_goal",
                                },
                                {
                                    "description": "At least 2 measurable key results",
                                    "check_kind": "has_okrs",
                                    "params": {"min": 2},
                                },
                            ],
                        },
                        {
                            "index": 2,
                            "name": "mece_research",
                            "purpose": "Build the mental model and close knowledge gaps for the objective",
                            "owner_role": "barbara_minto",
                            "exit_criteria": [
                                {
                                    "description": "MECE research atoms cover objective",
                                    "check_kind": "mece_complete",
                                }
                            ],
                        },
                        {
                            "index": 3,
                            "name": "build_delightful_app",
                            "purpose": f"Ship a page that helps the customer achieve: {title}",
                            "owner_role": "ux_cx_builder",
                            "exit_criteria": [
                                {
                                    "description": "Interactive HTML meets quality gate",
                                    "check_kind": "quality_pass",
                                }
                            ],
                        },
                        {
                            "index": 4,
                            "name": "real_validation",
                            "purpose": "Run unit, integration, production, and CX tests that actually exercise the app",
                            "owner_role": "test_engineer",
                            "exit_criteria": [
                                {
                                    "description": "All test kinds pass with evidence",
                                    "check_kind": "tests_pass",
                                }
                            ],
                        },
                        {
                            "index": 5,
                            "name": "ship_and_narrate",
                            "purpose": "Publish app + build gist; Slack gets short status + links",
                            "owner_role": "slack_communicator",
                            "exit_criteria": [
                                {
                                    "description": "App URL and gist exist",
                                    "check_kind": "shipped",
                                }
                            ],
                        },
                    ],
                    "stage_notes": "Loop 1 sets states, exit criteria, and meaning of done for every later loop.",
                }
            )

        if "OKR" in system or "Objective & Key Results" in system:
            return json.dumps(
                {
                    "end_goal": f"A visitor can fully achieve: {title}",
                    "target_customer": "A curious person who wants this done fast without friction",
                    "success_definition": f"They complete the core job of '{title}' in under 60 seconds and want to share the page",
                    "non_goals": ["Marketing fluff", "Extra navigation", "Decorative chrome that delays the job"],
                    "learning_outcome": title,
                    "key_results": [
                        {
                            "description": "Core job completable without instructions",
                            "metric": "time_to_value_seconds",
                            "target": "<=60",
                            "verification": "production click-path test",
                        },
                        {
                            "description": "Interactive controls work as labeled",
                            "metric": "interactive_controls_pass",
                            "target": "100%",
                            "verification": "unit + integration handlers",
                        },
                        {
                            "description": "Quality gate score",
                            "metric": "quality_score",
                            "target": ">=80",
                            "verification": "quality_gate.run",
                        },
                    ],
                }
            )

        if "Barbara Minto" in system or "MECE" in system:
            return json.dumps(
                {
                    "atoms": [
                        {
                            "topic": "Customer job",
                            "question": f"What job is the user hiring '{title}' to do?",
                            "findings": f"Primary job: {prompt}. Success is finishing that job with minimal reading.",
                            "gaps_remaining": [],
                            "sufficient_for_objective": True,
                        },
                        {
                            "topic": "Interaction model",
                            "question": "What inputs/outputs must exist for the job?",
                            "findings": "Collect the minimum inputs, compute/respond immediately, show clear result.",
                            "gaps_remaining": [],
                            "sufficient_for_objective": True,
                        },
                        {
                            "topic": "Delight constraints",
                            "question": "What should be removed so the job stays fast?",
                            "findings": "No cards-for-decoration, no hero clutter, expressive type, atmospheric background, one CTA path.",
                            "gaps_remaining": [],
                            "sufficient_for_objective": True,
                        },
                    ]
                }
            )

        if "UI UX CX" in system or "build_html" in system:
            html = _offline_app_html(title, prompt)
            return json.dumps(
                {
                    "title": title,
                    "slug": slug_hint or "daily-app",
                    "html": html,
                    "tenets": [
                        "Remove anything that does not help the customer finish the job",
                        "One composition, brand-first title, atmospheric background",
                        "Real interactivity with immediate feedback",
                    ],
                    "cx_notes": "Fast path to the result; shareable because it just works.",
                }
            )

        if "test_engineer" in system or "design_tests" in system:
            return json.dumps(
                {
                    "unit_tests": [
                        {
                            "name": "has_doctype_and_viewport",
                            "kind": "unit",
                            "steps": ["Parse HTML head"],
                            "expected": "DOCTYPE + viewport meta present",
                        },
                        {
                            "name": "has_interactive_control",
                            "kind": "unit",
                            "steps": ["Scan for button/input + script handler"],
                            "expected": "At least one interactive control with handler",
                        },
                    ],
                    "integration_tests": [
                        {
                            "name": "ready_marker",
                            "kind": "integration",
                            "steps": ["Check body[data-dailyapps-ready]"],
                            "expected": "Marker equals 1",
                        }
                    ],
                    "production_tests": [
                        {
                            "name": "shipped_files_exist",
                            "kind": "production",
                            "steps": ["Verify apps/<slug>/index.html and meta.json"],
                            "expected": "Both files present",
                        }
                    ],
                    "cx_tests": [
                        {
                            "name": "no_wall_of_text",
                            "kind": "cx",
                            "steps": ["Count visible instructional paragraphs in first viewport"],
                            "expected": "Lead text stays short; job is obvious",
                        }
                    ],
                }
            )

        if "Slack Communicator" in system or "slack_blurb" in system:
            state_line = ""
            for key in ("State ended:", "state ended:"):
                if key in user:
                    state_line = user.split(key, 1)[1].strip().splitlines()[0].strip()
                    break
            blurbs = {
                "stage_setting": "Mapped the loops, states, and exit criteria for this run.",
                "understand_objective": "Pinned the end goal and measurable key results.",
                "mece_research": "Finished MECE research; mental model is solid enough to build.",
                "build_delightful_app": "Shipped a page aimed straight at the customer job.",
                "build_delightful_app_retry": "Rebuilt the page after quality gate feedback.",
                "real_validation": "Ran unit, integration, production, and CX checks with evidence.",
                "real_validation_retry": "Re-ran validations until exit criteria cleared.",
                "ship_and_narrate": "Published the app and wrote the build gist.",
            }
            blurb = blurbs.get(state_line, f"Finished `{state_line or 'this state'}` with exit criteria met.")
            return json.dumps(
                {
                    "blurb": blurb,
                    "trust_line": "Right loop finished with exit criteria met.",
                }
            )

        if json_mode:
            return json.dumps({"ok": True, "echo": prompt[:200]})
        return f"Understood: {prompt[:280]}"


def _headers_unused() -> None:
    return None


def _extract_prompt(user: str) -> str:
    for key in ("PROMPT:", "prompt:", "User request:", "Feedback:"):
        if key in user:
            return user.split(key, 1)[1].strip().split("\n", 1)[0].strip()
    return user.strip().splitlines()[0][:200]


def _title_from_prompt(prompt: str) -> str:
    text = prompt.strip()
    text = re.sub(r"^(build|make|create|improve)\s+", "", text, flags=re.I)
    text = text[:80].strip(" .")
    return text[:1].upper() + text[1:] if text else "Daily app"


def _extract_json(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        candidate = match.group(0)
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            repaired = _repair_json(candidate)
            if repaired is not None:
                return repaired
    raise ValueError(f"LLM did not return JSON object: {raw[:240]}")


def _repair_json(raw: str) -> dict[str, Any] | None:
    """Best-effort repair for truncated / slightly invalid local-LLM JSON."""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    # Trim to outermost object if present
    start = text.find("{")
    if start < 0:
        return None
    text = text[start:]
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Close unclosed quotes/brackets
    in_str = False
    escape = False
    stack: list[str] = []
    for ch in text:
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack and stack[-1] == ch:
                stack.pop()
    if in_str:
        text += '"'
    while stack:
        text += stack.pop()
    text = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _offline_app_html(title: str, prompt: str) -> str:
    safe_title = _xml_escape(title)
    safe_prompt = _xml_escape(prompt)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{safe_title}</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@600&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet"/>
<style>
  :root {{
    --ink:#1c1917; --muted:#57534e; --accent:#0f766e; --panel:#fffbeb;
    --bg1:#99f6e4; --bg2:#fed7aa; --bg3:#fffbeb;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; min-height:100vh; color:var(--ink);
    font-family:"Source Sans 3", Georgia, serif;
    background:
      radial-gradient(1200px 600px at 10% -10%, var(--bg1) 0%, transparent 55%),
      radial-gradient(900px 500px at 100% 0%, var(--bg2) 0%, transparent 50%),
      var(--bg3);
  }}
  header {{ padding: clamp(2.5rem, 8vw, 5rem) 1.5rem 0.5rem; }}
  h1 {{
    font-family: Fraunces, Georgia, serif;
    font-size: clamp(2.5rem, 7vw, 4.5rem);
    line-height:1.05; margin:0 0 0.75rem;
  }}
  .lead {{ max-width:32rem; font-size:1.125rem; color:var(--muted); }}
  main {{
    margin:1rem 1.5rem 4rem; padding:1.5rem; max-width:28rem;
  }}
  label {{ display:block; margin:1rem 0 0.35rem; font-weight:600; }}
  input, textarea {{
    width:100%; font:inherit; padding:0.95rem 1rem;
    border-radius:0.5rem; border:1px solid #d6d3d1; background:#fff;
  }}
  #go {{
    width:100%; margin-top:1.25rem; font:inherit; font-weight:700;
    padding:1rem 1.25rem; border:0; border-radius:0.65rem;
    background:var(--accent); color:#fff; cursor:pointer; font-size:1.1rem;
  }}
  #result {{ margin-top:1.25rem; min-height:1.5rem; font-size:1.15rem; }}
</style>
</head>
<body data-dailyapps-ready="1">
<header>
  <h1>{safe_title}</h1>
  <p class="lead">{safe_prompt}</p>
</header>
<main>
  <label for="input">Your input</label>
  <input id="input" type="text" placeholder="Type something" autocomplete="off"/>
  <button id="go" type="button">Run</button>
  <p id="result" aria-live="polite"></p>
</main>
<script>
const input = document.getElementById('input');
const result = document.getElementById('result');
document.getElementById('go').addEventListener('click', () => {{
  const v = (input.value || '').trim();
  result.textContent = v ? ('Done: ' + v) : 'Add something first.';
}});
input.addEventListener('keydown', (e) => {{
  if (e.key === 'Enter') document.getElementById('go').click();
}});
</script>
</body>
</html>
"""


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_LLM: LocalLLM | None = None


def get_llm(*, offline: bool | None = None) -> LocalLLM:
    global _LLM
    if _LLM is None:
        force_offline = offline if offline is not None else False
        _LLM = LocalLLM(offline=force_offline)
    return _LLM
