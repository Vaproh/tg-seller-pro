#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[install]${NC} $*"; }
warn() { echo -e "${YELLOW}[install]${NC} $*"; }
err()  { echo -e "${RED}[install]${NC} $*" >&2; }

cd "$(dirname "$0")"

# ── Check uv ──────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    log "uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# ── Create .env if missing ────────────────────────────────
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        warn "Created .env from .env.example — edit it with your BOT_TOKEN and ADMIN_USER_ID"
    else
        cat > .env <<'EOF'
BOT_TOKEN=
ADMIN_USER_ID=
EOF
        warn "Created empty .env — fill in BOT_TOKEN and ADMIN_USER_ID"
    fi
fi

# ── Install dependencies ──────────────────────────────────
log "Installing dependencies..."
uv sync

# ── Create data and logs dirs ─────────────────────────────
mkdir -p data logs

log "Done! Next steps:"
echo ""
echo "  1. Edit .env with your BOT_TOKEN and ADMIN_USER_ID"
echo "  2. Run: uv run main.py"
echo ""
