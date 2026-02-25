# Monitoring and Observability Setup

## Metrics

The monitoring system collects metrics from edge devices, Kubernetes workloads, and AWS infrastructure.

### Application Metrics

Video processing services expose Prometheus metrics.

Key metrics:

- Request latency for API endpoints
- Error rate for API requests
- Kafka consumer lag
- Fragment processing rate
- Video chunk upload latency
- Upload success rate
- Upload queue backlog size

These metrics help detect processing slowdowns and upload failures.

---

### Infrastructure Metrics

Collected via CloudWatch and Prometheus node exporters.

Key metrics:

- CPU utilization for EKS nodes and edge devices
- Memory usage
- Disk utilization
- Network throughput
- Packet loss
- VPN tunnel status

Disk usage on edge devices is critical because upload failures cause local buffering.

---

### Business Metrics

Business-level metrics reflect customer-facing system behavior.

Key metrics:

- Video chunks processed per minute
- Cameras online per site
- Upload success percentage
- Average video ingestion delay
- Active customer sites

These metrics help detect customer-impacting issues early.

---

### Edge Device Metrics

Edge devices push metrics periodically.

Key metrics:

- VPN tunnel status
- Upload error count
- Upload throughput
- Disk usage percentage
- CPU and GPU utilization
- Camera connectivity status

Edge metrics are critical because customer sites depend on reliable uploads.

---

## SLOs (Service Level Objectives)

### Availability

API availability target:

99.9 percent monthly uptime

Inference API and customer dashboards must remain available.

---

### Data Freshness

Video data must arrive in cloud storage within:

5 minutes of capture

This ensures analytics and investigations remain useful.

---

### Upload Reliability

Edge upload success rate:

At least 99 percent per hour

Lower success rates indicate network or VPN problems.

---

### Edge Device Uptime

Edge devices must remain operational:

At least 99.5 percent monthly uptime

Temporary VPN outages are acceptable if buffering works correctly.

---

## Alerting

Alerting is based on severity levels to avoid alert fatigue.

### Paging Alerts

Triggered when immediate action is required.

Examples:

- VPN tunnel down for more than 5 minutes
- Upload success rate below 80 percent for 10 minutes
- Edge disk usage above 90 percent
- API error rate above 5 percent
- Kafka consumer lag exceeding threshold

These alerts trigger on-call engineer paging.

---

### Ticket Alerts

Triggered for gradual issues.

Examples:

- Disk usage above 75 percent
- CPU usage above 80 percent for 30 minutes
- Increased upload latency
- Camera offline for extended periods

These alerts create tickets for investigation.

---

### Alert Fatigue Prevention

To prevent excessive alerts:

- Alerts include cooldown periods
- Repeated alerts are grouped
- Warning alerts do not page engineers
- Temporary network interruptions under 2 minutes do not trigger alerts

---

## Escalation

### L1 Automated Response

Automated remediation handles common failures.

Examples:

- Restart failed containers
- Retry failed uploads
- Reconnect VPN tunnel

---

### L2 On-call Engineer

On-call engineers investigate alerts.

Typical actions:

- Check edge device status
- Check VPN tunnel health
- Review CloudWatch metrics
- Restart services if necessary

Response target:

Within 15 minutes.

---

### L3 Specialist Escalation

Escalated when root cause requires deeper expertise.

Examples:

- Networking issues
- Kubernetes cluster problems
- Storage issues
- VPN configuration problems

---

### Customer Notification

Customers are notified when:

- Data ingestion delays exceed 30 minutes
- Edge devices go offline
- Planned maintenance occurs

---

## Dashboards

### Edge Operations Dashboard

Displays per-site metrics:

- VPN tunnel status
- Upload throughput
- Upload error rate
- Disk usage
- Camera connectivity

This dashboard helps detect site-specific failures.

---

### Platform Dashboard

Displays platform-wide metrics:

- API request rate
- API error rate
- Latency percentiles
- Kafka lag
- Processing throughput

This dashboard monitors cloud services.

---

### Infrastructure Dashboard

Displays infrastructure metrics:

- Node CPU and memory usage
- Pod resource usage
- Network throughput
- Disk utilization

This dashboard helps capacity planning.

---

### Incident Dashboard

Displays active problems:

- Sites with upload failures
- High disk usage sites
- VPN instability
- Failed deployments

This dashboard is used during incidents.