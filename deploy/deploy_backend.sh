#!/usr/bin/env bash
# Deploy FinLearn backend to AWS EC2: pull latest and restart service.
# Usage:
#   FINLEARN_EC2_HOST=1.2.3.4 ./deploy/deploy_backend.sh
#   FINLEARN_EC2_HOST=1.2.3.4 FINLEARN_EC2_KEY_PATH=~/.ssh/my.pem ./deploy/deploy_backend.sh

set -e

HOST="${FINLEARN_EC2_HOST:-}"
KEY="${FINLEARN_EC2_KEY_PATH:-}"

if [ -z "$HOST" ]; then
  echo "Set FINLEARN_EC2_HOST (e.g. your EC2 public IP)."
  exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)
[ -n "$KEY" ] && SSH_OPTS+=(-i "$KEY")

REMOTE="ubuntu@${HOST}"
echo "Deploying backend to $REMOTE ..."

ssh "${SSH_OPTS[@]}" "$REMOTE" "cd ~/FinLearnAI && git pull origin main && sudo systemctl restart finlearn && sudo systemctl status finlearn --no-pager"

echo "Done."
