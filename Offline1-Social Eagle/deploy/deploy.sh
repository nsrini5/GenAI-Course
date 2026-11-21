#!/usr/bin/env bash
# Run ON THE VPS, from inside the project folder of the cloned GenAI Course repo:
#   cd ~/genai-course/"Offline1-Social Eagle" && bash deploy/deploy.sh
set -euo pipefail

REPO_URL="${1:-}"
SCRIPT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$SCRIPT_ROOT/docker-compose.yml" ]; then
  APP_DIR="${APP_DIR:-$SCRIPT_ROOT}"
else
  APP_DIR="${APP_DIR:-$HOME/genai-course/Offline1-Social Eagle}"
fi

# 1. Docker (Ubuntu/Debian) if missing
if ! command -v docker >/dev/null 2>&1; then
  echo ">> Installing Docker"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  echo ">> Docker installed. Log out and back in once, then re-run this script."
  exit 0
fi

# 2. Fetch code
if [ ! -f "$APP_DIR/docker-compose.yml" ]; then
  [ -z "$REPO_URL" ] && { echo "Usage: bash deploy.sh <git-repo-url>"; exit 1; }
  git clone "$REPO_URL" "$HOME/genai-course"
fi
cd "$APP_DIR"
git pull --ff-only 2>/dev/null || echo ">> (git pull skipped)"

# 3. Env file
if [ ! -f .env ]; then
  cp .env.example .env
  sed -i "s/^API_KEY=.*/API_KEY=$(openssl rand -hex 24)/" .env
  sed -i "s/^NEO4J_PASSWORD=.*/NEO4J_PASSWORD=$(openssl rand -hex 16)/" .env
  echo ">> Created .env with random API_KEY and NEO4J_PASSWORD. Add your LLM key, then re-run."
  grep -E '^(API_KEY|NEO4J_PASSWORD)=' .env
  exit 0
fi

# 4. Build + (re)start
docker compose up -d --build
docker image prune -f >/dev/null

echo ">> Waiting for health check..."
for i in $(seq 1 30); do
  if curl -fsS "http://localhost:${HOST_PORT:-8000}/health"; then echo; echo ">> Up."; exit 0; fi
  sleep 5
done
echo ">> Not healthy yet - check: docker compose logs -f rag"; exit 1
