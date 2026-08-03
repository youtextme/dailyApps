#!/usr/bin/env bash
# Verify required secrets are present in the environment (never prints values).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Load local dev secrets if present (gitignored).
if [[ -f .env.local ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
elif [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

REQUIRED=(
  SLACK_BOT_TOKEN
  SLACK_APP_TOKEN
  SLACK_SIGNING_SECRET
)

OPTIONAL=(
  SLACK_CHANNEL_ID
  GITHUB_TOKEN
  TIRELESS_ROUTER_URL
  OPENAI_API_KEY
  ANTHROPIC_API_KEY
)

missing=()
placeholder=()

is_placeholder() {
  local v="$1"
  [[ -z "$v" ]] && return 0
  [[ "$v" == *"replace-me"* ]] && return 0
  [[ "$v" == "xoxb-" ]] && return 0
  [[ "$v" == "xapp-" ]] && return 0
  return 1
}

for key in "${REQUIRED[@]}"; do
  val="${!key-}"
  if is_placeholder "$val"; then
    if [[ -z "$val" ]]; then
      missing+=("$key")
    else
      placeholder+=("$key")
    fi
  fi
done

echo "=== dailyApps secrets check ==="
echo "Context: ${CURSOR_CLOUD_AGENT:-local}"
echo

if ((${#missing[@]})); then
  echo "MISSING (required):"
  printf '  - %s\n' "${missing[@]}"
fi

if ((${#placeholder[@]})); then
  echo "PLACEHOLDER (replace in .env.local or dashboard):"
  printf '  - %s\n' "${placeholder[@]}"
fi

if ((${#missing[@]} == 0 && ${#placeholder[@]} == 0)); then
  echo "OK: all required Slack secrets are set."
else
  echo
  echo "See docs/SECRETS.md for setup in Cursor Cloud, Devin, and local dev."
  exit 1
fi

echo
echo "Optional (unset is fine for static Pages-only work):"
for key in "${OPTIONAL[@]}"; do
  val="${!key-}"
  if is_placeholder "$val"; then
    echo "  - $key: not set"
  else
    echo "  - $key: set"
  fi
done
