# Root Cause Analysis

Review all files in `data/debug_scenario/` to investigate the incident.

## Summary

On 2025-11-12, SITE-2847 experienced sustained video upload failures from the edge device to S3. A scheduled network maintenance change intended to enable jumbo frames for the camera VLAN was mistakenly applied to the WAN and VPN interface (eno1). This changed the MTU from 1500 to 9000 on the interface used by the IPSec tunnel. The site gateway path MTU was 1500 and did not support jumbo frames, causing fragmentation issues, degraded IPSec throughput, repeated DPD timeouts, VPN tunnel flaps, and S3 multipart upload timeouts. When the MTU was reverted back to 1500 on eno1, uploads recovered immediately and the tunnel stabilized.

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 08:00 | Uploads normal. Multiple successful batches at ~41–44 Mbps. |
| 08:15 | Change applied: netplan configuration updated. eno1 MTU changed 1500 -> 9000 (intended for camera VLAN only). |
| 08:15–08:18 | Upload batch begins (12 chunks, 847MB). S3 PutObject becomes slow then times out. |
| 08:18 | Edge syslog shows repeated ICMP “fragmentation needed” from gateway 10.50.1.1 (path MTU 1500). |
| 08:18–08:20 | Upload timeouts repeat. CloudWatch upload errors spike (2 then 18 then 24 per 5-min). |
| 08:21 | IPSec tunnel flaps DOWN/UP due to DPD timeout. Upload retries continue but fail. |
| 08:22 | App detects throughput collapse to ~1.8 Mbps and flags possible MTU/fragmentation issue. |
| 08:30 | Backlog grows (22 chunks). Edge disk usage rises sharply (85%+). NOC alert triggered. |
| 08:35–08:50 | Additional VPN flaps and packet loss observed. Upload errors remain high. |
| 09:00 | MTU reverted 9000 -> 1500 on eno1. Fragmentation stops, tunnel stabilizes, upload errors drop back to 0 and uploads resume. |

## Root Cause

**Incorrect MTU change applied to eno1 (management/WAN + VPN interface) instead of eno2 (camera VLAN).**

Evidence from multiple sources:

- NOC timeline explicitly states a netplan change applied to eno1 with “Enable jumbo frames” ticket NET-4521, but gateway MTU is 1500 and jumbo frames were intended only for camera VLAN. Reverting MTU fixed the incident immediately.
- Edge syslog shows: `device eno1: MTU changed from 1500 to 9000 via netplan apply` at 08:15:03, followed by repeated `ICMP: 10.50.1.1: fragmentation needed and DF set, mtu=1500` at 08:18 and later.
- VPN logs show warnings about packet size exceeding path MTU and sustained fragmentation and reassembly failures. DPD timeouts occur after MTU change, causing tunnel flaps.
- App logs show S3 multipart PutObject timeouts beginning shortly after MTU change, with retries failing and throughput falling to ~1.8 Mbps while small health checks still pass (classic “large packets fail, small packets succeed” symptom).

This combination indicates PMTU / fragmentation issues on the IPSec path after the MTU was incorrectly increased on the interface carrying the tunnel.

## Contributing Factors

- Change control error: ticket intended to apply jumbo frames to camera VLAN interface (eno2) only, but it was applied to eno1.
- Insufficient pre-change validation: no automated guardrail to prevent MTU > 1500 on the VPN uplink where the path does not support jumbo frames.
- Health checks were not representative: container “healthcheck passed” continued while large S3 uploads failed (health checks likely small HTTP requests).
- Limited early detection: monitoring captured upload errors, but not direct MTU mismatch / fragmentation-needed rate as a first-class alert.
- Backpressure behavior: uploader queue backed up and disk usage climbed rapidly, increasing risk of local buffer exhaustion.

## Evidence

Key excerpts referenced from `data/debug_scenario/`:

- App logs: S3 multipart PutObject “slow” then `java.net.SocketTimeoutException: Read timed out` starting around 08:15–08:19, repeated retries, throughput warning ~1.8 Mbps, and explicit “Possible MTU/fragmentation issue”.
- CloudWatch metrics: `VideoChunkUploadErrors` spikes from 0 to 18–24 per 5-minute window; note indicates recovery after MTU reverted at 09:00.
- Edge syslog: eno1 MTU change 1500 -> 9000 via netplan; repeated ICMP fragmentation-needed messages from gateway 10.50.1.1; uploader backlog and disk usage warnings.
- VPN status log: warnings about packet size exceeding path MTU; ESP fragmentation/reassembly failures; DPD timeouts and repeated tunnel DOWN/UP cycles; fragmentation stopping once MTU restored to 1500.