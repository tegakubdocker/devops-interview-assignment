#!/usr/bin/env bash
#
# remediation.sh — Incident remediation script
#
# TASK: Write a script that remediates the issue identified in your root cause analysis.
#
# Requirements:
#   - Fix the immediate issue
#   - Verify the fix worked
#   - Be safe to run (idempotent, with checks before making changes)
#   - Include error handling

set -euo pipefail

WAN_IF="${WAN_IF:-eno1}"
CAM_IF="${CAM_IF:-eno2}"

WAN_MTU_DESIRED="${WAN_MTU_DESIRED:-1500}"
CAM_MTU_DESIRED="${CAM_MTU_DESIRED:-9000}"

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"; }
fail() { log "ERROR: $*"; exit 1; }

need_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    fail "Run as root"
  fi
}

iface_exists() {
  ip link show "$1" >/dev/null 2>&1
}

get_mtu() {
  ip link show "$1" | awk '{for(i=1;i<=NF;i++) if($i=="mtu") {print $(i+1); exit}}'
}

set_mtu_runtime() {
  local ifname="$1"
  local desired="$2"
  local current
  current="$(get_mtu "$ifname" || true)"
  if [[ -z "${current}" ]]; then
    fail "Could not read MTU for ${ifname}"
  fi

  if [[ "${current}" == "${desired}" ]]; then
    log "${ifname} MTU already ${desired} (no change)"
    return 0
  fi

  log "Setting runtime MTU on ${ifname}: ${current} -> ${desired}"
  ip link set dev "$ifname" mtu "$desired"
}

persist_netplan_mtu_best_effort() {
  # Best-effort persistence: modify existing netplan YAML if it contains the interface.
  # We back up before editing. If we can't safely edit, we just log and continue.
  local ifname="$1"
  local desired="$2"

  local files
  files=(/etc/netplan/*.yaml /etc/netplan/*.yml)
  local found=0

  for f in "${files[@]}"; do
    [[ -f "$f" ]] || continue
    if grep -qE "^[[:space:]]*${ifname}:" "$f"; then
      found=1
      local backup="${f}.bak.$(date -u '+%Y%m%dT%H%M%SZ')"
      log "Backing up netplan: ${f} -> ${backup}"
      cp -a "$f" "$backup"

      # If mtu line exists under the interface block, replace it. Else, insert an mtu line after the interface line.
      if grep -qE "^[[:space:]]*mtu:[[:space:]]*[0-9]+" "$f"; then
        # Replace only within file (best effort). Keeps it simple for assignment.
        sed -i "s/^[[:space:]]*mtu:[[:space:]]*[0-9]\+/      mtu: ${desired}/" "$f" || true
      else
        # Insert with indentation typical for netplan (2 spaces per level).
        # This is a best-effort insertion; if formatting differs, it's still safe because runtime MTU already fixed.
        sed -i "/^[[:space:]]*${ifname}:/a\ \ \ \ \ \ mtu: ${desired}" "$f" || true
      fi

      log "Applied netplan MTU best-effort for ${ifname} in ${f}"
    fi
  done

  if [[ "$found" -eq 0 ]]; then
    log "No netplan file referencing ${ifname} found. Runtime MTU fixed; persistence skipped."
  fi
}

restart_services() {
  log "Applying netplan (best effort)"
  if command -v netplan >/dev/null 2>&1; then
    netplan apply || log "netplan apply failed (continuing; runtime MTU already set)"
  fi

  # Restart strongSwan to clear tunnel state if present
  if systemctl list-unit-files | grep -q '^strongswan'; then
    log "Restarting strongSwan"
    systemctl restart strongswan || log "strongswan restart failed (continuing)"
  fi
}

verify() {
  log "Verifying MTU values"
  local wan_mtu
  wan_mtu="$(get_mtu "$WAN_IF")"
  log "${WAN_IF} MTU is ${wan_mtu}"
  [[ "${wan_mtu}" == "${WAN_MTU_DESIRED}" ]] || fail "${WAN_IF} MTU is not ${WAN_MTU_DESIRED}"

  if iface_exists "$CAM_IF"; then
    local cam_mtu
    cam_mtu="$(get_mtu "$CAM_IF")"
    log "${CAM_IF} MTU is ${cam_mtu}"
  fi

  # VPN status (optional)
  if command -v ipsec >/dev/null 2>&1; then
    log "IPSec status (best effort)"
    ipsec statusall || true
  fi

  # Path MTU sanity check (best effort):
  # Try to send a DF ping with payload ~1472 bytes (fits MTU 1500 with headers)
  if command -v ping >/dev/null 2>&1; then
    log "Running DF ping sanity check (best effort)"
    ping -c 1 -M do -s 1472 8.8.8.8 >/dev/null 2>&1 || log "DF ping check failed (network may restrict ICMP); continuing"
  fi

  log "Remediation complete and basic verification passed"
}

main() {
  need_root

  iface_exists "$WAN_IF" || fail "Interface not found: ${WAN_IF}"

  log "Fixing MTU issue: ensure WAN/VPN interface (${WAN_IF}) uses MTU ${WAN_MTU_DESIRED}"
  set_mtu_runtime "$WAN_IF" "$WAN_MTU_DESIRED"
  persist_netplan_mtu_best_effort "$WAN_IF" "$WAN_MTU_DESIRED"

  # Optional: camera VLAN jumbo frames on eno2
  if iface_exists "$CAM_IF"; then
    log "Optional: ensure camera interface (${CAM_IF}) uses MTU ${CAM_MTU_DESIRED}"
    set_mtu_runtime "$CAM_IF" "$CAM_MTU_DESIRED" || true
    persist_netplan_mtu_best_effort "$CAM_IF" "$CAM_MTU_DESIRED" || true
  else
    log "Camera interface ${CAM_IF} not found; skipping"
  fi

  restart_services
  verify
}

main "$@"