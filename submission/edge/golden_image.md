# Golden Image Strategy

## Overview

We use a golden image to make edge device provisioning repeatable, fast, and consistent across customer sites. The image contains the OS, GPU drivers, container runtime, security baselines, and system services required to run the video ingest stack. Site specific configuration is not baked into the image and is applied at provisioning time so the same image can be used for many sites.

Goals:
- Consistent runtime and driver versions across the fleet
- Minimal on site steps
- Safe upgrades with staged rollout and rollback
- Easy validation with health checks

## Base Image

Included in the base image:
- Ubuntu 22.04 LTS with latest security updates at build time
- Docker CE installed and configured
  - json-file log driver with size and file rotation limits
  - overlay2 storage driver
- NVIDIA GPU driver compatible with the target hardware
- NVIDIA container toolkit so containers can use the GPU
- Time sync service (chrony)
- Logrotate config for application logs
- Security baseline
  - root SSH login disabled
  - password authentication disabled
  - ufw baseline rules
  - fail2ban enabled
- Systemd service definitions
  - video-ingest.service installed but not started until config is present
- Health check tooling
  - healthcheck.sh to validate docker, GPU availability, disk buffer space

Not included in the base image (site specific):
- SITE_ID
- Camera subnet details and discovery config
- VPN configuration and credentials
- S3 bucket and prefixes
- SQS queue URL
- Any customer identifiers, secrets, API keys, certificates

## Image Creation Process

1. Start from Ubuntu 22.04 LTS base
2. Apply OS updates
3. Install required packages
   - docker, chrony, ufw, fail2ban, logrotate
4. Install GPU stack
   - NVIDIA driver
   - nvidia-container-toolkit
   - configure docker runtime
5. Add edge service assets
   - systemd unit for video ingest container
   - env file template under /etc/video-analytics/
   - healthcheck script
6. Apply security hardening defaults
   - SSH hardening
   - ufw baseline
   - fail2ban enable
7. Validation
   - reboot and confirm services
   - docker works
   - nvidia-smi works when GPU is present
   - systemd unit loads cleanly
8. Version and publish
   - tag the image with semantic version and build date
   - publish to a private image repository or managed image registry

Tools:
- Packer or an equivalent imaging pipeline is preferred for repeatability
- If not available, use a scripted process and capture all steps in version control

## Configuration Management

Per site configuration is applied after imaging using one of these approaches:
- cloud-init user-data for automated setup on first boot
- a config bundle pulled from a secure endpoint using a device identity
- a signed configuration file delivered on site and verified before use

Configuration should be stored in:
- /etc/video-analytics/video-ingest.env for environment variables
- /etc/strongswan/ or equivalent for VPN settings (if VPN terminates on the edge)

Secrets handling:
- never bake secrets into the image
- rotate credentials per site
- store secrets in a central system and deliver them only at provisioning time

Validation step after config:
- run healthcheck.sh
- verify camera discovery
- verify local buffering path exists and has space
- verify successful upload and queue publish on a test run

## Patching and Updates

We use an image based update process:
- Create a new golden image version with OS security patches and updated container runtime or GPU drivers as needed
- Stage rollouts
  - canary one device
  - small batch per region
  - then full fleet
- Measure health signals
  - VPN stability
  - camera availability
  - ingest error rate
  - upload success rate
  - buffer disk utilization
- Application updates are primarily done by updating container image tags
- OS and driver updates are done by publishing a new golden image version

Operational policy:
- regular patch cadence, for example monthly
- emergency patch process for critical CVEs

## Rollback

Rollback strategy has two layers:
1. Application rollback
   - revert video ingest container to last known good tag
   - restart systemd service
2. Image rollback
   - keep the previous golden image version available
   - if canary fails, stop rollout immediately
   - revert affected devices by reinstalling the previous image or switching boot target if using A B partitions

Rollback trigger examples:
- healthcheck fails after update
- GPU runtime fails or driver mismatch
- persistent upload failures or crash loops

For safety:
- maintain a per device record of last known good image version
- require explicit approval for large fleet wide rollouts