"""Ship apps into apps/<slug>/ and refresh catalog."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tireless.config import APPS_DIR, PAGES_BASE_URL
from tireless.dailyapps.catalog import refresh_catalog
from tireless.dailyapps.quality_gate import run_quality_gate
from tireless.models import Session


def ship_session(session: Session, *, repo_root: Path | None = None) -> dict:
    apps_dir = (repo_root / "apps") if repo_root else APPS_DIR
    apps_dir.mkdir(parents=True, exist_ok=True)

    slug = session.slug or "daily-app"
    title = session.title or slug
    html = str(session.artifacts.get("html") or "")
    if not html:
        raise RuntimeError("No HTML artifact to ship")

    report = run_quality_gate(html)
    if not report.ok:
        raise RuntimeError(f"quality gate failed: {report.violations} score={report.score}")

    app_dir = apps_dir / slug
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "index.html").write_text(html, encoding="utf-8")

    meta_path = app_dir / "meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}

    now = datetime.now(timezone.utc).isoformat()
    meta.update(
        {
            "slug": slug,
            "title": title,
            "objective_id": session.objective_id,
            "created_at": meta.get("created_at") or now,
            "quality_score": report.score,
        }
    )
    if session.feedback_history:
        meta["last_feedback"] = session.feedback_history[-1]
        meta["last_feedback_at"] = now
        (app_dir / "FEEDBACK.md").write_text(
            f"# Feedback\n\n{session.feedback_history[-1]}\n\nUpdated: {now}\n",
            encoding="utf-8",
        )

    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    catalog_root = repo_root if repo_root else apps_dir.parent
    refresh_catalog(catalog_root)

    app_url = f"{PAGES_BASE_URL.rstrip('/')}/apps/{slug}/"
    session.app_path = str(app_dir)
    session.app_url = app_url
    session.artifacts["app_url"] = app_url
    session.artifacts["quality_score"] = report.score
    return {"slug": slug, "app_dir": str(app_dir), "app_url": app_url, "quality_score": report.score}
