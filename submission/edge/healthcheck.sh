#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="video-ingest"
BUFFER_DIR="${VIDEO_BUFFER_DIR:-/var/lib/video-buffer}"

ok() { echo "OK: $1"; }
warn() { echo "WARN: $1"; }
fail() { echo "FAIL: $1"; exit 2; }

# Docker present
command -v docker >/dev/null 2>&1 || fail "docker not installed"

# Container running (best-effort)
if docker ps --format '{{.Names}}' | grep -q "^${SERVICE_NAME}$"; then
  ok "container ${SERVICE_NAME} is running"
else
  warn "container ${SERVICE_NAME} is not running"
fi

# Disk buffer dir exists and has space
if [[ -d "$BUFFER_DIR" ]]; then
  ok "buffer dir exists: $BUFFER_DIR"
  avail_kb=$(df -Pk "$BUFFER_DIR" | awk 'NR==2 {print $4}')
  if [[ "${avail_kb:-0}" -lt 1048576 ]]; then
    warn "low disk space in buffer dir (less than ~1GB free)"
  else
    ok "disk space looks fine"
  fi
else
  warn "buffer dir missing: $BUFFER_DIR"
fi

# NVIDIA health (optional)
if command -v nvidia-smi >/dev/null 2>&1; then
  if nvidia-smi >/dev/null 2>&1; then
    ok "nvidia-smi OK"
  else
    warn "nvidia-smi failed"
  fi
else
  warn "nvidia-smi not installed (GPU checks skipped)"
fi

exit 0