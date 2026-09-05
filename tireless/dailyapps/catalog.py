"""Maintain root index.html catalog of shipped apps."""

from __future__ import annotations

import json
from pathlib import Path


def refresh_catalog(repo_root: Path) -> Path:
    apps_dir = repo_root / "apps"
    entries: list[tuple[str, str]] = []
    if apps_dir.exists():
        for meta_path in sorted(apps_dir.glob("*/meta.json")):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            slug = meta.get("slug") or meta_path.parent.name
            title = meta.get("title") or slug
            entries.append((slug, title))

    items = "\n".join(
        f'<li><a href="apps/{slug}/">{_escape(title)}</a></li>' for slug, title in entries
    ) or "<li>No apps shipped yet.</li>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>dailyApps</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@600&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet"/>
<style>
  :root {{ --ink:#1c1917; --muted:#57534e; --accent:#0f766e; }}
  body {{
    margin:0; min-height:100vh; color:var(--ink);
    font-family:"Source Sans 3", Georgia, serif;
    background:
      radial-gradient(900px 480px at 0% 0%, #99f6e4 0%, transparent 55%),
      radial-gradient(800px 420px at 100% 0%, #fed7aa 0%, transparent 50%),
      #fffbeb;
  }}
  main {{ max-width:40rem; margin:0 auto; padding: clamp(2.5rem, 8vw, 5rem) 1.25rem; }}
  h1 {{
    font-family: Fraunces, Georgia, serif;
    font-size: clamp(2.5rem, 7vw, 4rem);
    margin:0 0 0.35rem; line-height:1.05;
  }}
  p {{ color:var(--muted); font-size:1.125rem; }}
  a {{ color:var(--accent); }}
  ul {{ padding-left:1.1rem; line-height:1.8; }}
</style>
</head>
<body>
<main>
  <header>
    <h1>dailyApps</h1>
    <p>Interactive apps shipped from Slack via stateful local-LLM loops.</p>
  </header>
  <ul>
{items}
  </ul>
</main>
</body>
</html>
"""
    path = repo_root / "index.html"
    path.write_text(html, encoding="utf-8")
    return path


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
