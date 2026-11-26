# Test results

Recorded verification runs for [issue #25](https://github.com/hackingerror404/ServiceChaperone/issues/25) showing that Service Chaperone meets the reliability goals in [docs/design.md](design.md).

## Environment

- **OS:** CachyOS Linux (kernel 7.3.5-2-cachyos)
- **Python:** Python 3.14.10
- **Commit:** 581fa89

---

## 1. 72-hour stability run

- **Start:** [2026-11-23 18:23 MST]
- **End:** [2026-11-26 13:19 MST]
- **Total duration:** 67 hours
- **Command:**
  ```bash
  { date -Is; service-chaperone run --config ~/.config/service-chaperone/soak-72h.toml 2>&1; date -Is; } | tee ~/soak-72h.log
  ```

### Config used

```ini, toml
[[monitor]]
name = "Example website"
type = "website"
url = "[https://example.com](https://example.com)"
interval = 60
timeout = 10
retries = 2

[[monitor]]
name = "Local HTTP proxy"
type = "proxy"
proxy = "[http://127.0.0.1:3128](http://127.0.0.1:3128)"
url = "[http://example.com](http://example.com)"
interval = 60
timeout = 10
retries = 2

[[monitor]]
name = "Cloudflare HTTPS port"
type = "port"
host = "1.1.1.1"
port = 443
interval = 60
timeout = 10
retries = 2
```

### Outcome
| Metric | Expected | Observed |
| --- | --- | ---- |
| `is now DOWN` alerts | 0 | 0 |
| Unexpected crashes / restarts | 0 | 0 |
| Transient single-check failures (if any) | Absorbed by `retries = 2` | 0 |

## 2. 5-minute internet disconnect (during the 72-hour run)

- Disconnected at: [2026-11-25 18:55 MST]
- Reconnected at: [2026-11-25 18:59 MST]
- Duration offline: about 3 and a half minutes
- Method: Wi-Fi toggled off.

| Metric | Expected | Observed |
| --- | --- | ---- |
| "Service Chaperone is offline" notifications | 1 | 1 |
| `is now DOWN` alerts | 0 | 0 |
| Resumed normal `UP` checks after reconnect | Yes | Yes |
ction error: [Errno -3] Temporary failure in name resolution)
18:56:02 WARNING Local HTTP proxy: DOWN (HTTP 502 Bad Gateway)

18:59:02 INFO Cloudflare HTTPS port: UP (25.1 ms)
18:59:02 INFO Connection restored; resuming normal checks.
18:59:02 INFO Local HTTP proxy: UP (80.2 ms)
18:59:02 INFO Example website: UP (82.7 ms)
```

## 3. Multi-outage scripted run

Run as a separate instance with its own temporary config (`interval = 2s`, `timeout = 1s`, `retries = 1`, detection budget = `(1 + 1) × 2 + 1 = 5.0s)` so deliberate outages did not affect the 72-hour soak run.

- Date: [2026-11-25]
- Command: `python dev/try_multi_outage.py`

### Outcome:

| Monitor | Type | DOWN alerts | Recovery alerts | Detection budget | Measured DOWN time | Alerts on other services |
| --- | --- | --- | --- | --- | --- | --- |
| Test website | website | 1 | 1 | 5.0s | 3.50s | 0 |
| Test proxy | proxy | 1 | 1 | 5.0s | 3.50s | 0 |
| Test port | port | 1 | 1 | 5.0s | 3.49s | 0 |

### Script output:

```
Config: interval=2.0s, timeout=1.0s, retries=1 (DOWN budget = 5.0s)
[PASS] Startup quiet while all three services are healthy
Test website: DOWN (connection error: [Errno 111] Connection refused)
Test website: DOWN (connection error: [Errno 111] Connection refused)
Test website is now DOWN after 2 failure(s) in a row (connection error: [Errno 111] Connection refused)
Test website: DOWN (connection error: [Errno 111] Connection refused)
[PASS] Test website: 1 DOWN + 1 recovery within budget, 0 alerts on other services (DOWN in 3.50s (budget 5.0s), UP in 1.50s)
Test proxy: DOWN (could not connect to the proxy (http://127.0.0.1:40551))
Test proxy: DOWN (could not connect to the proxy (http://127.0.0.1:40551))
Test proxy is now DOWN after 2 failure(s) in a row (could not connect to the proxy (http://127.0.0.1:40551))
Test proxy: DOWN (could not connect to the proxy (http://127.0.0.1:40551))
[PASS] Test proxy: 1 DOWN + 1 recovery within budget, 0 alerts on other services (DOWN in 3.50s (budget 5.0s), UP in 1.45s)
Test port: DOWN (connection refused (127.0.0.1:36649))
Test port: DOWN (connection refused (127.0.0.1:36649))
Test port is now DOWN after 2 failure(s) in a row (connection refused (127.0.0.1:36649))
Test port: DOWN (connection refused (127.0.0.1:36649))
[PASS] Test port: 1 DOWN + 1 recovery within budget, 0 alerts on other services (DOWN in 3.49s (budget 5.0s), UP in 1.48s)
[PASS] Zero offline notifications during loopback outage test

Finished with 0 failure(s).
```
