#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.yml"
SERVICE="bot"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[deploy]${NC} $*"; }
err()  { echo -e "${RED}[deploy]${NC} $*" >&2; }

cd "$(dirname "$0")"

# ── Preflight checks ──────────────────────────────────────
if ! command -v docker &>/dev/null; then
    err "docker not found. Install Docker first."
    exit 1
fi

if ! docker compose version &>/dev/null && ! docker-compose version &>/dev/null; then
    err "docker compose not found."
    exit 1
fi

# Detect compose command
if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

# ── Actions ───────────────────────────────────────────────
action="${1:-deploy}"

case "$action" in
    deploy|update)
        log "Pulling latest code..."
        git pull --rebase

        log "Building image..."
        $COMPOSE build --no-cache

        log "Restarting bot..."
        $COMPOSE up -d --force-recreate $SERVICE

        log "Waiting for startup..."
        sleep 3

        if $COMPOSE ps $SERVICE | grep -q "Up"; then
            log "Bot is running."
        else
            err "Bot failed to start. Check logs: ./deploy.sh logs"
            exit 1
        fi
        ;;

    restart)
        log "Restarting bot..."
        $COMPOSE restart $SERVICE
        log "Done."
        ;;

    stop)
        log "Stopping bot..."
        $COMPOSE stop $SERVICE
        log "Done."
        ;;

    start)
        log "Starting bot..."
        $COMPOSE up -d $SERVICE
        log "Done."
        ;;

    logs)
        $COMPOSE logs -f --tail=100 $SERVICE
        ;;

    status)
        $COMPOSE ps $SERVICE
        ;;

    rebuild)
        log "Full rebuild (no cache)..."
        $COMPOSE down $SERVICE
        $COMPOSE build --no-cache
        $COMPOSE up -d $SERVICE
        log "Done."
        ;;

    test)
        log "Running tests..."
        if [ -d ".venv" ]; then
            .venv/bin/python -m pytest tests/ -v
        else
            python3 -m pytest tests/ -v
        fi
        ;;

    *)
        echo "Usage: $0 {deploy|restart|stop|start|logs|status|rebuild|test}"
        echo ""
        echo "  deploy   - git pull + rebuild + restart (default)"
        echo "  restart  - restart the bot container"
        echo "  stop     - stop the bot"
        echo "  start    - start the bot"
        echo "  logs     - tail bot logs"
        echo "  status   - show container status"
        echo "  rebuild  - full rebuild from scratch"
        echo "  test     - run pytest suite"
        exit 1
        ;;
esac
