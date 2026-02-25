# Site Network Plan

Review `data/site_spec.json` for the customer site specification.

## VLAN Design

| VLAN ID | Name | Subnet | Purpose |
|---------|------|--------|---------|
| 10 | CAMERA_VLAN | 10.50.20.0/24 | Isolated camera network. RTSP/ONVIF traffic from cameras to edge only. No access to mgmt/corp. |
| 20 | MGMT_VLAN | 10.50.1.0/24 | Management access to edge device (SSH) and uplink toward WAN/VPN. |
| 30 | CORP_VLAN (optional) | 10.50.2.0/24 | Customer corporate network. No camera VLAN access allowed. |

Notes:
- Camera VLAN should remain isolated from Management and Corporate VLANs.
- Edge device is the only dual-homed component.

## IP Addressing Scheme

### Static assignments
- Edge device `eno2` (camera VLAN): `10.50.20.10/24`
- Edge device `eno1` (mgmt VLAN): `10.50.1.10/24`
- Default gateway (mgmt VLAN): `10.50.1.1`

### DHCP ranges
- Cameras (CAMERA_VLAN): `10.50.20.100` to `10.50.20.250`
- Reserve `.1` to `.50` for infrastructure (switch, NVR if any, future edge devices)

## Camera Network Isolation

- Cameras reside on CAMERA_VLAN and have no routed access to MGMT_VLAN or CORP_VLAN.
- Firewall policy on the edge:
  - Allow RTSP (554 tcp/udp) from CAMERA_VLAN to the edge device
  - Block forwarding from CAMERA_VLAN to MGMT/CORP
- Switch configuration:
  - CAMERA_VLAN ports are access ports for cameras only
  - MGMT_VLAN ports are access ports for management workstation/jump host
  - Trunk to edge only if required; otherwise keep as simple access ports per NIC

## Edge Device Network Configuration

- `eno2` connects to CAMERA_VLAN switch ports (camera-only).
  - IP: `10.50.20.10/24`
  - No default route on this interface.
- `eno1` connects to MGMT/WAN network.
  - IP: `10.50.1.10/24`
  - Default route via `10.50.1.1`
- Routing:
  - All outbound internet/VPN traffic uses `eno1`.
  - No forwarding between interfaces by default.
- Security:
  - SSH allowed only from `10.50.1.0/24`.
  - Cameras are not allowed to initiate connections into MGMT/CORP networks.

## Traffic Flow

1. Cameras stream RTSP to the edge device over CAMERA_VLAN.
2. Edge device performs ingest and AI inference locally.
3. Edge device uploads video fragments and metadata to AWS over the VPN via MGMT/WAN (`eno1`).
4. If VPN drops, edge continues processing locally and buffers data for later upload (disk spool).