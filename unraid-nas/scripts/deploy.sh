#!/bin/bash
# Deploy compose stacks and VM configs to NAS
# Usage: ./scripts/deploy.sh [stack]
#   ./scripts/deploy.sh          # deploy all stacks
#   ./scripts/deploy.sh media    # deploy only media stack

NAS="ssh -p 28853 root@192.168.0.4"
NAS_COMPOSE_DIR="/mnt/user/appdata/compose"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

deploy_stack() {
  local stack="$1"
  local src="$SCRIPT_DIR/compose/$stack/docker-compose.yml"

  if [ ! -f "$src" ]; then
    echo "ERROR: $src not found"
    return 1
  fi

  echo "→ Deploying $stack..."
  $NAS "mkdir -p $NAS_COMPOSE_DIR/$stack"
  scp -P 28853 "$src" "root@192.168.0.4:$NAS_COMPOSE_DIR/$stack/docker-compose.yml"
  $NAS "cd $NAS_COMPOSE_DIR/$stack && docker compose pull && docker compose up -d"
  echo "✓ $stack deployed"
}

if [ -n "$1" ]; then
  deploy_stack "$1"
else
  for stack in "$SCRIPT_DIR/compose"/*/; do
    deploy_stack "$(basename "$stack")"
  done
fi
