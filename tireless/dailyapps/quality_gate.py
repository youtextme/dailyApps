"""Code-enforced anti-slop / shipping quality gate."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class QualityReport:
    score: float
    violations: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.score >= 80 and not any(v.startswith("fatal:") for v in self.violations)


def run_quality_gate(html: str) -> QualityReport:
    violations: list[str] = []
    score = 100.0
    lower = html.lower()

    if not html or len(html.strip()) < 80:
        return QualityReport(score=0, violations=["fatal:too_thin", "empty or tiny html"])

    if "<!doctype html>" not in lower:
        violations.append("missing doctype")
        score -= 20
    if 'name="viewport"' not in lower:
        violations.append("missing viewport")
        score -= 15
    if not re.search(r"<h1[\s>]", lower):
        violations.append("missing h1")
        score -= 15

    # interactivity
    has_control = bool(re.search(r"<(button|input|select|textarea)\b", lower))
    has_handler = "addeventlistener" in lower or "onclick=" in lower
    if not (has_control and has_handler):
        violations.append("fatal:not_interactive")
        score -= 40

    if 'data-dailyapps-ready="1"' not in html:
        violations.append("missing data-dailyapps-ready")
        score -= 10

    # banned aesthetics / fonts
    if re.search(r"font-family:\s*['\"]?(inter|roboto|arial)\b", lower):
        violations.append("banned primary font (Inter/Roboto/Arial)")
        score -= 15
    if re.search(r"purple|#7c3aed|#6366f1|indigo", lower):
        # soft penalty — purple/indigo gradient aesthetic
        if "gradient" in lower:
            violations.append("purple/indigo gradient aesthetic")
            score -= 10
    if "#f4f1ea" in lower:
        violations.append("cream #F4F1EA default")
        score -= 10

    # images need alt
    for img in re.findall(r"<img\b[^>]*>", html, flags=re.I):
        if not re.search(r"\balt\s*=", img, flags=re.I):
            violations.append("img missing alt")
            score -= 5

    # thin stub detection: tiny body text + generic scaffold cues
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    words = [w for w in text.split() if w.strip()]
    if len(words) < 12 and "your input" in lower and "ready" in lower:
        violations.append("fatal:too_thin")
        score -= 50

    score = max(0.0, min(100.0, score))
    return QualityReport(score=score, violations=violations)
