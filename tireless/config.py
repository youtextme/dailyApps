"""Runtime configuration for dailyApps / tireless."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
# Machine-local secret store (never commit). Shared across repos on this host/snapshot.
load_dotenv(Path.home() / ".config" / "tireless" / "secrets.env", override=False)

REPO_ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = REPO_ROOT / "apps"
TEMPLATES_DIR = REPO_ROOT / "templates"
DATA_DIR = Path(os.getenv("TIRELESS_DATA_DIR", REPO_ROOT / "data"))
SESSIONS_DIR = DATA_DIR / "sessions"
GISTS_DIR = DATA_DIR / "gists"
CATALOG_PATH = REPO_ROOT / "index.html"

MAX_PARALLEL_SESSIONS = int(os.getenv("TIRELESS_MAX_PARALLEL", "20"))
PAGES_BASE_URL = os.getenv(
    "DAILYAPPS_PAGES_URL",
    "https://youtextme.github.io/dailyApps",
)


@dataclass(frozen=True)
class LLMConfig:
    """OpenAI-compatible local router (ollama / tireless-router / vLLM)."""

    base_url: str
    api_key: str
    model: str
    timeout_s: float = 120.0

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            base_url=os.getenv("TIRELESS_LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/"),
            api_key=os.getenv("TIRELESS_LLM_API_KEY", "local"),
            model=os.getenv("TIRELESS_LLM_MODEL", "llama3.2"),
            timeout_s=float(os.getenv("TIRELESS_LLM_TIMEOUT", "90")),
        )


@dataclass(frozen=True)
class SlackConfig:
    bot_token: str
    app_token: str
    signing_secret: str
    channel: str

    @classmethod
    def from_env(cls) -> "SlackConfig":
        return cls(
            bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
            app_token=os.getenv("SLACK_APP_TOKEN", ""),
            signing_secret=os.getenv("SLACK_SIGNING_SECRET", ""),
            channel=os.getenv("SLACK_DAILYAPPS_CHANNEL", "dailyApps"),
        )

    @property
    def configured(self) -> bool:
        return bool(self.bot_token and (self.app_token or self.signing_secret))


@dataclass(frozen=True)
class GitHubConfig:
    token: str
    gist_public: bool = True

    @classmethod
    def from_env(cls) -> "GitHubConfig":
        return cls(
            token=os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or "",
            gist_public=os.getenv("TIRELESS_GIST_PUBLIC", "1") not in {"0", "false", "False"},
        )

    @property
    def configured(self) -> bool:
        return bool(self.token)


def ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    GISTS_DIR.mkdir(parents=True, exist_ok=True)
    APPS_DIR.mkdir(parents=True, exist_ok=True)
