---
title: Configuration
---

# Configuration Reference

Complete configuration reference for tuning SMG behavior.

---

## Configuration Methods

SMG can be configured through:

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **Default values** (lowest priority)

---

## Routing Configuration

### Load Balancing Policy

Controls how requests are distributed across workers.

| Option | `--policy` |
|--------|------------|
| Environment | `SMG_POLICY` |
| Default | `round_robin` |
| Values | `random`, `round_robin`, `power_of_two`, `cache_aware` |

**Policy Comparison**:

| Policy | Use Case | KV Cache | Load Balance |
|--------|----------|----------|--------------|
| `random` | Simple deployments | Poor | Fair |
| `round_robin` | Uniform workloads | Poor | Good |
| `power_of_two` | Variable workloads | Poor | Excellent |
| `cache_aware` | LLM inference | Excellent | Good |

**Recommendation**: Use `cache_aware` for LLM workloads to maximize KV cache hit rates.

---

## Rate Limiting Configuration

### Concurrent Request Limit

Maximum number of requests processing simultaneously.

| Option | `--max-concurrent-requests` |
|--------|----------------------------|
| Environment | `SMG_MAX_CONCURRENT_REQUESTS` |
| Default | `-1` (unlimited) |
| Range | `-1` or `1+` |

**Sizing Guide**:

```
max_concurrent_requests = num_workers × requests_per_worker_capacity
```

| Worker GPU Memory | Suggested per Worker |
|-------------------|---------------------|
| 16GB | 4-8 |
| 40GB | 8-16 |
| 80GB | 16-32 |

### Token Refill Rate

Rate at which tokens are added to the rate limit bucket.

| Option | `--rate-limit-tokens-per-second` |
|--------|----------------------------------|
| Environment | `SMG_RATE_LIMIT_TOKENS_PER_SECOND` |
| Default | `512` |

### Queue Size

Maximum requests waiting when rate limit is reached.

| Option | `--queue-size` |
|--------|----------------|
| Environment | `SMG_QUEUE_SIZE` |
| Default | `128` |

**Sizing Guide**:

| Workload Type | Queue Size Factor |
|---------------|-------------------|
| Interactive (low latency) | 0.5-1× concurrent limit |
| Batch processing | 2-4× concurrent limit |
| Async jobs | 4-8× concurrent limit |

### Queue Timeout

Maximum time a request waits in queue before timeout.

| Option | `--queue-timeout-secs` |
|--------|------------------------|
| Environment | `SMG_QUEUE_TIMEOUT_SECS` |
| Default | `30` |
| Unit | Seconds |

---

## Circuit Breaker Configuration

### Failure Threshold

Consecutive failures before circuit opens.

| Option | `--circuit-breaker-threshold` |
|--------|-------------------------------|
| Environment | `SMG_CIRCUIT_BREAKER_THRESHOLD` |
| Default | `5` |

### Recovery Timeout

Time before attempting recovery (half-open state).

| Option | `--circuit-breaker-timeout` |
|--------|----------------------------|
| Environment | `SMG_CIRCUIT_BREAKER_TIMEOUT` |
| Default | `30` |
| Unit | Seconds |

---

## Health Check Configuration

### Check Interval

Time between health checks.

| Option | `--health-check-interval` |
|--------|---------------------------|
| Environment | `SMG_HEALTH_CHECK_INTERVAL` |
| Default | `10s` |
| Format | Duration (e.g., `5s`, `1m`) |

### Check Timeout

Timeout for individual health check requests.

| Option | `--health-check-timeout` |
|--------|--------------------------|
| Environment | `SMG_HEALTH_CHECK_TIMEOUT` |
| Default | `5s` |
| Format | Duration |

### Health Check Path

HTTP path for health checks.

| Option | `--health-check-path` |
|--------|----------------------|
| Environment | `SMG_HEALTH_CHECK_PATH` |
| Default | `/health` |

---

## Server Configuration

### Host

Network interface to bind to.

| Option | `--host` |
|--------|----------|
| Environment | `SMG_HOST` |
| Default | `127.0.0.1` |

| Value | Description |
|-------|-------------|
| `127.0.0.1` | Localhost only |
| `0.0.0.0` | All interfaces |

### Port

Port for the main API server.

| Option | `--port` |
|--------|----------|
| Environment | `SMG_PORT` |
| Default | `30000` |

### Metrics Port

Port for Prometheus metrics endpoint.

| Option | `--prometheus-port` |
|--------|---------------------|
| Environment | `SMG_PROMETHEUS_PORT` |
| Default | `29000` |

---

## TLS Configuration

### Server TLS

For HTTPS on the gateway:

| Option | Description |
|--------|-------------|
| `--tls-cert-path` | Path to server certificate |
| `--tls-key-path` | Path to server private key |

### Client mTLS

For secure communication to workers:

| Option | Description |
|--------|-------------|
| `--client-cert-path` | Path to client certificate |
| `--client-key-path` | Path to client private key |
| `--ca-cert-path` | Path to CA certificate(s) |

---

## Authentication Configuration

### API Key

Require API key for client requests.

| Option | `--api-key` |
|--------|-------------|
| Environment | `SMG_API_KEY` |
| Default | None (disabled) |

When set, clients must include:

```
Authorization: Bearer <api-key>
```

---

## Service Discovery Configuration

### Enable Service Discovery

| Option | `--service-discovery` |
|--------|----------------------|
| Default | Disabled |

### Label Selector

| Option | `--selector` |
|--------|--------------|
| Environment | `SMG_SELECTOR` |
| Format | `key=value` |

### Namespace

| Option | `--service-discovery-namespace` |
|--------|--------------------------------|
| Environment | `SMG_SERVICE_DISCOVERY_NAMESPACE` |
| Default | Current namespace |

### Worker Port

| Option | `--service-discovery-port` |
|--------|---------------------------|
| Environment | `SMG_SERVICE_DISCOVERY_PORT` |
| Default | `8000` |

---

## Logging Configuration

### Log Level

| Option | `--log-level` |
|--------|---------------|
| Environment | `SMG_LOG_LEVEL` or `RUST_LOG` |
| Default | `info` |
| Values | `error`, `warn`, `info`, `debug`, `trace` |

**Per-Module Logging**:

```bash
RUST_LOG=smg=debug,hyper=warn smg ...
```

---

## Configuration Examples

### Minimal Configuration

```bash
smg --worker-urls http://localhost:8000
```

### High-Throughput Configuration

```bash
smg \
  --worker-urls http://w1:8000 http://w2:8000 http://w3:8000 http://w4:8000 \
  --policy cache_aware \
  --max-concurrent-requests 200 \
  --rate-limit-tokens-per-second 100 \
  --queue-size 400 \
  --queue-timeout-secs 60
```

### Low-Latency Configuration

```bash
smg \
  --worker-urls http://w1:8000 http://w2:8000 \
  --policy power_of_two \
  --max-concurrent-requests 50 \
  --queue-size 25 \
  --queue-timeout-secs 5 \
  --health-check-interval 5s
```

### Secure Production Configuration

```bash
smg \
  --service-discovery \
  --selector app=sglang-worker \
  --service-discovery-namespace inference \
  --policy cache_aware \
  --max-concurrent-requests 100 \
  --tls-cert-path /etc/certs/server.crt \
  --tls-key-path /etc/certs/server.key \
  --client-cert-path /etc/certs/client.crt \
  --client-key-path /etc/certs/client.key \
  --ca-cert-path /etc/certs/ca.crt \
  --api-key "${SMG_API_KEY}" \
  --host 0.0.0.0 \
  --port 443
```

---

## Environment Variable Reference

| Environment Variable | CLI Option |
|---------------------|------------|
| `SMG_WORKER_URLS` | `--worker-urls` |
| `SMG_POLICY` | `--policy` |
| `SMG_HOST` | `--host` |
| `SMG_PORT` | `--port` |
| `SMG_PROMETHEUS_PORT` | `--prometheus-port` |
| `SMG_MAX_CONCURRENT_REQUESTS` | `--max-concurrent-requests` |
| `SMG_RATE_LIMIT_TOKENS_PER_SECOND` | `--rate-limit-tokens-per-second` |
| `SMG_QUEUE_SIZE` | `--queue-size` |
| `SMG_QUEUE_TIMEOUT_SECS` | `--queue-timeout-secs` |
| `SMG_CIRCUIT_BREAKER_THRESHOLD` | `--circuit-breaker-threshold` |
| `SMG_CIRCUIT_BREAKER_TIMEOUT` | `--circuit-breaker-timeout` |
| `SMG_HEALTH_CHECK_INTERVAL` | `--health-check-interval` |
| `SMG_HEALTH_CHECK_TIMEOUT` | `--health-check-timeout` |
| `SMG_HEALTH_CHECK_PATH` | `--health-check-path` |
| `SMG_API_KEY` | `--api-key` |
| `SMG_LOG_LEVEL` / `RUST_LOG` | `--log-level` |
| `SMG_SELECTOR` | `--selector` |
| `SMG_SERVICE_DISCOVERY_NAMESPACE` | `--service-discovery-namespace` |
| `SMG_SERVICE_DISCOVERY_PORT` | `--service-discovery-port` |
