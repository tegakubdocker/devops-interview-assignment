#!/usr/bin/env bash
#
# firewall_rules.sh — Edge device firewall configuration
#
# Implements iptables rules for edge device based on requirements.
#
# Hints used:
#   - Management VLAN: 10.50.1.0/24
#   - Edge interfaces: eno1 (mgmt/WAN), eno2 (camera VLAN)
#
# NOTE: Adjust CAMERA_VLAN_CIDR and CORPORATE_VLAN_CIDR to match site_plan.md / site_spec.json.

set -euo pipefail

MGMT_VLAN_CIDR="10.50.1.0/24"
CAMERA_VLAN_CIDR="${CAMERA_VLAN_CIDR:-10.50.20.0/24}"
# If you know corp VLAN, set it. Otherwise keep empty.
CORPORATE_VLAN_CIDR="${CORPORATE_VLAN_CIDR:-}"

MGMT_IF="eno1"
CAMERA_IF="eno2"

# --- Flush existing rules ---
iptables -F
iptables -X
iptables -t nat -F
iptables -t mangle -F

# --- Default policies ---
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# --- Loopback ---
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# --- Established/Related ---
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# --- ICMP ---
iptables -A INPUT -p icmp -j ACCEPT

# --- SSH from management VLAN only ---
iptables -A INPUT -i "$MGMT_IF" -p tcp -s "$MGMT_VLAN_CIDR" --dport 22 -m conntrack --ctstate NEW -j ACCEPT

# --- RTSP from camera VLAN only ---
iptables -A INPUT -i "$CAMERA_IF" -p tcp -s "$CAMERA_VLAN_CIDR" --dport 554 -m conntrack --ctstate NEW -j ACCEPT
iptables -A INPUT -i "$CAMERA_IF" -p udp -s "$CAMERA_VLAN_CIDR" --dport 554 -j ACCEPT

# --- HTTPS outbound ---
# OUTPUT default is ACCEPT; explicitly allow and keep readable for reviewers
iptables -A OUTPUT -p tcp --dport 443 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
iptables -A INPUT  -p tcp --sport 443 -m conntrack --ctstate ESTABLISHED -j ACCEPT

# --- Camera VLAN isolation (block camera-to-management/corporate) ---
# Block camera VLAN from reaching management VLAN via forwarding
iptables -A FORWARD -i "$CAMERA_IF" -o "$MGMT_IF" -s "$CAMERA_VLAN_CIDR" -d "$MGMT_VLAN_CIDR" -j DROP

# Block camera VLAN reaching corporate VLAN if defined
if [[ -n "$CORPORATE_VLAN_CIDR" ]]; then
  iptables -A FORWARD -i "$CAMERA_IF" -o "$MGMT_IF" -s "$CAMERA_VLAN_CIDR" -d "$CORPORATE_VLAN_CIDR" -j DROP
fi

# Allow camera VLAN to talk only to the edge device itself (already handled by INPUT rules),
# and do NOT forward camera traffic elsewhere by default (FORWARD policy DROP).

# --- Logging for dropped packets (optional but recommended) ---
iptables -A INPUT -m limit --limit 10/min --limit-burst 20 -j LOG --log-prefix "iptables-drop-input: " --log-level 4
iptables -A FORWARD -m limit --limit 10/min --limit-burst 20 -j LOG --log-prefix "iptables-drop-forward: " --log-level 4

echo "Firewall rules applied successfully"