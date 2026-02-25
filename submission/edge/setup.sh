#!/usr/bin/env bash
#
# setup.sh — Edge device provisioning script
#
# TASK: Implement a provisioning script for a new edge device.
# Reference data/site_spec.json for hardware and requirements.
#
# Requirements:
#   - Error handling (set -euo pipefail, trap for cleanup)
#   - Docker installation and configuration
#   - NTP configuration for time synchronization
#   - Log rotation setup
#   - Systemd service for the video ingest container
#   - GPU driver setup (NVIDIA)
#   - Basic security hardening

set -euo pipefail

SITE_ID="${SITE_ID:-SITE-UNKNOWN}"
LOG_FILE="/var/log/edge-setup-${SITE_ID}.log"
SERVICE_USER="${SERVICE_USER:-edge}"
VIDEO_BUFFER_DIR="${VIDEO_BUFFER_DIR:-/var/lib/video-buffer}"
CONFIG_DIR="/etc/video-analytics"
ENV_FILE="${CONFIG_DIR}/video-ingest.env"
SYSTEMD_UNIT="/etc/systemd/system/video-ingest.service"

cleanup() {
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Cleanup complete. Logs: ${LOG_FILE}" || true
}
trap cleanup EXIT

log() {
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $1" | tee -a "$LOG_FILE"
}

need_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "ERROR: run as root"
    exit 1
  fi
}

log "Starting edge device setup for site: $SITE_ID"
need_root

mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

export DEBIAN_FRONTEND=noninteractive

# ============================================
# SECTION 1: System Updates and Base Packages
# ============================================
log "Updating system and installing prerequisites"
apt-get update -y
apt-get upgrade -y
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg lsb-release jq \
  chrony ufw fail2ban logrotate \
  pciutils build-essential

# Create service user
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  log "Creating service user: $SERVICE_USER"
  useradd -m -s /bin/bash "$SERVICE_USER"
fi

mkdir -p "$VIDEO_BUFFER_DIR"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$VIDEO_BUFFER_DIR"

mkdir -p "$CONFIG_DIR"
chmod 0750 "$CONFIG_DIR"

# ============================================
# SECTION 2: Docker Installation
# ============================================
log "Installing Docker CE (if not present)"
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update -y
  apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
  log "Docker already installed"
fi

log "Configuring Docker daemon settings"
mkdir -p /etc/docker
cat >/etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  },
  "storage-driver": "overlay2"
}
EOF

systemctl enable docker
systemctl restart docker

# Add user to docker group
if getent group docker >/dev/null 2>&1; then
  usermod -aG docker "$SERVICE_USER" || true
fi

# ============================================
# SECTION 3: NVIDIA GPU Drivers and Container Toolkit
# ============================================
log "Installing NVIDIA drivers and container toolkit"
apt-get install -y --no-install-recommends ubuntu-drivers-common

if ! command -v nvidia-smi >/dev/null 2>&1; then
  log "Installing recommended NVIDIA driver"
  ubuntu-drivers autoinstall || true
else
  log "nvidia-smi already available"
fi

if ! dpkg -l | grep -q nvidia-container-toolkit; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit.gpg
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit.gpg] https://#g' \
    > /etc/apt/sources.list.d/nvidia-container-toolkit.list

  apt-get update -y
  apt-get install -y --no-install-recommends nvidia-container-toolkit
else
  log "nvidia-container-toolkit already installed"
fi

# Configure Docker to use NVIDIA runtime
if command -v nvidia-ctk >/dev/null 2>&1; then
  log "Configuring NVIDIA runtime for Docker"
  nvidia-ctk runtime configure --runtime=docker || true
  systemctl restart docker
else
  log "nvidia-ctk not found, skipping runtime auto-config"
fi

# ============================================
# SECTION 4: NTP Configuration
# ============================================
log "Configuring NTP"
# Use NTP_SERVER env var if provided (from site_spec.json via config mgmt)
NTP_SERVER="${NTP_SERVER:-}"
if [[ -n "$NTP_SERVER" ]]; then
  log "Using site NTP server: $NTP_SERVER"
  cat >/etc/chrony/chrony.conf <<EOF
pool pool.ntp.org iburst
server ${NTP_SERVER} iburst prefer
driftfile /var/lib/chrony/chrony.drift
makestep 1.0 3
rtcsync
logdir /var/log/chrony
EOF
else
  log "NTP_SERVER not set; using default chrony configuration"
fi

systemctl enable chrony
systemctl restart chrony

# ============================================
# SECTION 5: Log Rotation
# ============================================
log "Configuring logrotate"
cat >/etc/logrotate.d/video-analytics-edge <<EOF
/var/log/edge-setup-*.log /var/log/video-ingest*.log {
  daily
  rotate 14
  compress
  delaycompress
  missingok
  notifempty
  copytruncate
}
EOF

# Docker container logs are limited via /etc/docker/daemon.json

# ============================================
# SECTION 6: Systemd Service
# ============================================
log "Creating systemd service for video-ingest container"

cat >"$ENV_FILE" <<EOF
SITE_ID=${SITE_ID}
VIDEO_BUFFER_DIR=${VIDEO_BUFFER_DIR}
# Fill these via config management per site:
# CAMERA_SUBNET=
# S3_BUCKET=
# SQS_QUEUE_URL=
# AWS_REGION=us-east-1
EOF

chmod 0640 "$ENV_FILE"
chown root:"$SERVICE_USER" "$ENV_FILE" || true

cat >"$SYSTEMD_UNIT" <<EOF
[Unit]
Description=Video Ingest Container (Edge)
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=${ENV_FILE}
Restart=always
RestartSec=5

ExecStartPre=/usr/bin/mkdir -p ${VIDEO_BUFFER_DIR}
ExecStartPre=/usr/bin/chown -R ${SERVICE_USER}:${SERVICE_USER} ${VIDEO_BUFFER_DIR}

ExecStart=/usr/bin/docker run --rm --name video-ingest \\
  --gpus all \\
  --network host \\
  -v ${VIDEO_BUFFER_DIR}:${VIDEO_BUFFER_DIR} \\
  -v /etc/localtime:/etc/localtime:ro \\
  --env-file ${ENV_FILE} \\
  111111111111.dkr.ecr.us-east-1.amazonaws.com/video-ingest:1.0.0

ExecStop=/usr/bin/docker stop video-ingest

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable video-ingest.service

# Do not force-start; leave for operator after config is set
log "Systemd unit installed. Start when config is ready: systemctl start video-ingest.service"

# ============================================
# SECTION 7: Security Hardening
# ============================================
log "Applying basic security hardening"

# Disable root SSH login and password auth
if [[ -f /etc/ssh/sshd_config ]]; then
  sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
  sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
  systemctl restart ssh || systemctl restart sshd || true
fi

# UFW baseline
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw --force enable

# Fail2ban
systemctl enable fail2ban
systemctl restart fail2ban

log "Edge device setup complete for site: $SITE_ID"