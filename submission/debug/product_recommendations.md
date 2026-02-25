# Product & Engineering Recommendations

Based on your investigation of the debug scenario, provide recommendations for improving the platform.

## Monitoring Improvements

1. MTU and fragmentation monitoring
- Add an edge metric for interface MTU (eno1 and eno2) and alert on unexpected values.
- Alert on kernel ICMP “fragmentation needed and DF set” message rate.

2. VPN stability monitoring
- Alert on strongSwan DPD timeouts, tunnel DOWN/UP flaps per hour, and ESP packet loss.
- Track effective tunnel throughput (expected vs actual).

3. Upload pipeline monitoring
- Track upload success rate, retry rate, and per-chunk latency percentiles.
- Add an alert for “large upload failures while health checks pass” pattern.

4. Buffer health monitoring
- Alert earlier on disk usage growth rate, not only absolute threshold.
- Alert on queue backlog age (oldest chunk age) to catch sustained failure quickly.

## Automated Detection

1. Automatic MTU safeguard
- On edge boot and after any netplan apply, run an automated MTU sanity check:
  - If eno1 MTU > 1500 and the gateway path MTU is 1500, automatically revert and notify NOC.

2. Smarter health checks
- Add a periodic synthetic transaction:
  - upload a small and a medium sized payload through the same VPN path
  - treat failures as an early warning even if container liveness is fine

3. Self-healing actions
- If upload retries exceed threshold and fragmentation-needed messages appear:
  - temporarily reduce MTU on WAN interface to 1500
  - restart strongSwan
  - re-run synthetic upload check before resuming normal behavior

## Platform Changes

1. Improve resilience to partial network failures
- Implement adaptive chunk sizing or retry strategy:
  - if large multipart uploads repeatedly timeout, temporarily reduce chunk size or adjust socket timeouts and concurrency

2. Backpressure controls
- When upload backlog grows and disk rises:
  - slow down ingest rate
  - drop non-critical streams first (policy-based)
  - protect disk from exhaustion

3. Change management and validation
- Require “pre and post change” validation steps for any network change:
  - interface mapping verification (eno1 vs eno2)
  - MTU readback check
  - VPN throughput quick test

## Edge Device Improvements

1. Configuration management
- Maintain a single source of truth for edge network configuration with interface mapping.
- Store expected MTU per interface as policy and validate continuously.

2. Change control
- Add a staged rollout process for network changes:
  - canary one edge device
  - verify metrics (throughput, fragmentation, VPN stability)
  - expand rollout only after success

3. Automated validation
- After applying netplan:
  - automatically run a validation checklist (MTU, route, VPN, synthetic upload)
  - block or rollback changes if validation fails