# Post-Incident Report

## Incident Summary

| Field | Value |
|-------|-------|
| Date | 2025-11-12 |
| Duration | 45 minutes (08:15–09:00 UTC) |
| Severity | Sev-2 (major degradation, no total outage) |
| Services Affected | Edge video uploader, IPSec VPN tunnel stability, S3 uploads for SITE-2847 |
| Customer Impact | Video uploads stalled or severely delayed; backlog accumulated and local disk usage reached ~85–91%, risking buffer exhaustion |

## What Happened

A scheduled network maintenance change intended to enable jumbo frames for the camera VLAN was mistakenly applied to the edge device WAN/VPN interface (eno1). This increased eno1 MTU to 9000, while the upstream gateway path MTU remained 1500. Large IPSec packets could not traverse cleanly, triggering ICMP “fragmentation needed” messages and causing fragmentation/reassembly failures. As a result, VPN throughput degraded drastically, the VPN tunnel flapped due to DPD timeouts, and S3 multipart uploads began timing out. Once the NOC reverted the MTU on eno1 back to 1500, uploads resumed immediately and the tunnel stabilized.

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 08:00 | Systems normal. Upload success rate 100%. |
| 08:15 | Network maintenance applied; eno1 MTU changed from 1500 to 9000. |
| 08:18 | ICMP “fragmentation needed” from gateway 10.50.1.1 appears; S3 upload timeouts begin. |
| 08:20 | CloudWatch upload error metric spikes (0 → 18 per 5-minute window). |
| 08:21 | IPSec tunnel flaps DOWN then UP (DPD timeout). Upload retries still fail. |
| 08:22 | App logs show throughput ~1.8 Mbps and flags likely MTU issue. |
| 08:30 | Backlog reaches 22 chunks; disk usage hits ~85%. NOC alerted. |
| 08:45 | NOC begins investigation. |
| 09:00 | MTU reverted to 1500 on eno1; fragmentation stops, tunnel stabilizes, uploads resume. |

## Root Cause

The edge device netplan change was applied to the wrong interface. Jumbo frames were intended for the camera VLAN interface (eno2), but the MTU was increased on the management/WAN interface (eno1) that carries the AWS IPSec tunnel. The site gateway and path MTU were 1500, causing fragmentation issues and VPN instability which led to S3 upload failures.

## Resolution

The NOC reverted eno1 MTU from 9000 back to 1500. After the change:
- VPN tunnel stabilized (DPD normal)
- packet fragmentation warnings stopped
- S3 uploads resumed and error metric returned to 0

## Impact

- Upload success rate dropped to near 0% during the window for large chunks.
- Queue backlog grew to at least 22 chunks and oldest chunk age exceeded 20 minutes.
- Edge disk usage rose from ~52% to ~85–91% before recovery.
- Customer dashboards and downstream processing relying on timely video availability were delayed during the incident window.
- No evidence of permanent data loss was observed, but the risk of local buffer exhaustion increased significantly.

## Action Items

| Action | Owner | Priority | Due Date |
|--------|-------|----------|----------|
| Add automated guardrail: alert if eno1 MTU deviates from 1500 on sites where gateway MTU is 1500 | Networking / NOC | P0 | 2 weeks |
| Update change procedure to explicitly validate interface mapping (eno1 vs eno2) before and after netplan apply | NOC | P0 | 1 week |
| Add monitoring for ICMP “fragmentation needed” rate and IPSec DPD flap frequency | Platform SRE | P1 | 3 weeks |
| Improve edge health checks to include a large-payload upload test or MTU sanity test | Edge Team | P1 | 3 weeks |
| Add backpressure controls: throttle ingest when upload queue grows and disk exceeds threshold | Edge Team | P1 | 4 weeks |
| Document site MTU requirements and standardize configs per site type | Networking | P2 | 6 weeks |

## Lessons Learned

### What went well

- Monitoring detected the error spike and triggered an alert before disk fully exhausted.
- VPN tunnel re-established automatically, reducing total outage time once MTU was corrected.
- The system recovered quickly after reverting MTU.

### What could be improved

- Change control should have prevented applying jumbo frames to the VPN uplink interface.
- Health checks were too shallow and did not reflect real upload behavior.
- Faster MTU/fragmentation-specific alerting would have shortened investigation time.