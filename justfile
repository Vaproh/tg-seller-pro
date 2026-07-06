# TG Seller Bot — justfile

# List available commands
default:
    @just --list

# Run the bot
run:
    uv run main.py

# Run the bot in dev mode (with debug logging)
dev:
    uv run python -c "import logging; logging.basicConfig(level=logging.DEBUG); exec(open('main.py').read())"

# Run tests
test:
    uv run pytest tests/ -v

# Run tests with coverage
test-cov:
    uv run pytest tests/ -v --tb=short

# Install/update dependencies
install:
    uv sync

# Add a dependency
add *ARGS:
    uv add {{ ARGS }}

# Remove a dependency
remove *ARGS:
    uv remove {{ ARGS }}

# Format code
fmt:
    uv run python -m black . 2>/dev/null || true
    uv run python -m ruff format . 2>/dev/null || true

# Lint code
lint:
    uv run python -m ruff check . 2>/dev/null || true

# Clean build artifacts, caches, and temp files
clean:
    rm -rf .venv/
    rm -rf __pycache__/ **/__pycache__/
    rm -rf *.pyc **/*.pyc
    rm -rf .pytest_cache/ **/.pytest_cache/
    rm -rf dist/ build/ *.egg-info/
    rm -rf .mypy_cache/
    rm -rf data/*.db-wal data/*.db-shm
    rm -rf logs/*.log
    echo "✨ Cleaned"

# Deep clean (remove everything including DB backups and env)
clean-all: clean
    rm -rf data/
    rm -rf logs/
    rm -f .env
    echo "🧹 Deep cleaned"

# Format + lint + test (full check)
check: fmt lint test

# Docker: deploy (pull + build + restart)
deploy:
    ./deploy.sh deploy

# Docker: restart
docker-restart:
    ./deploy.sh restart

# Docker: stop
docker-stop:
    ./deploy.sh stop

# Docker: start
docker-start:
    ./deploy.sh start

# Docker: tail logs
docker-logs:
    ./deploy.sh logs

# Docker: full rebuild
docker-rebuild:
    ./deploy.sh rebuild

# Backup database
backup:
    cp data/reddit_seller.db data/reddit_seller.db.bak 2>/dev/null && echo "📦 Backup created" || echo "⚠️ No database found"
