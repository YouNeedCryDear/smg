---
title: CLI Reference
---

# CLI Reference

Complete command-line reference for the SMG gateway.

---

## Usage

```bash
smg [OPTIONS]
```

---

## Options

### Worker Configuration

#### `--worker-urls <URL>...`

URLs of inference workers to route requests to.

```bash
smg --worker-urls http://worker1:8000 http://worker2:8000
```

- **Required**: Yes (unless using service discovery)
- **Multiple**: Yes
- **Default**: None

---

### Service Discovery

#### `--service-discovery`

Enable Kubernetes service discovery for automatic worker detection.

```bash
smg --service-discovery --selector app=sglang-worker
```

- **Default**: Disabled

#### `--selector <SELECTOR>`

Kubernetes label selector for discovering worker pods.

```bash
smg --service-discovery --selector app=sglang-worker
```

- **Required**: When `--service-discovery` is enabled
- **Format**: `key=value`

#### `--service-discovery-namespace <NAMESPACE>`

Kubernetes namespace to discover workers in.

```bash
smg --service-discovery --service-discovery-namespace inference
```

- **Default**: Current namespace (from service account)

#### `--service-discovery-port <PORT>`

Port to use when connecting to discovered workers.

```bash
smg --service-discovery --service-discovery-port 8000
```

- **Default**: `8000`

---

### Routing Policy

#### `--policy <POLICY>`

Load balancing policy for routing requests to workers.

```bash
smg --worker-urls http://w1:8000 http://w2:8000 --policy cache_aware
```

| Policy | Description |
|--------|-------------|
| `random` | Random worker selection |
| `round_robin` | Sequential rotation through workers |
| `power_of_two` | Choose best of two random workers |
| `cache_aware` | Maximize KV cache hits (recommended for LLMs) |

- **Default**: `round_robin`

---

### Rate Limiting

#### `--max-concurrent-requests <N>`

Maximum number of concurrent requests.

```bash
smg --max-concurrent-requests 100
```

- **Default**: `-1` (unlimited)
- **Range**: `-1` or `1+`

#### `--rate-limit-tokens-per-second <N>`

Token bucket refill rate for rate limiting.

```bash
smg --rate-limit-tokens-per-second 50
```

- **Default**: `512`

#### `--queue-size <N>`

Maximum number of requests that can wait in the queue.

```bash
smg --queue-size 200
```

- **Default**: `128`

#### `--queue-timeout-secs <N>`

Maximum time a request can wait in the queue before timing out.

```bash
smg --queue-timeout-secs 60
```

- **Default**: `30`

---

### Circuit Breaker

#### `--circuit-breaker-threshold <N>`

Number of consecutive failures before opening the circuit.

```bash
smg --circuit-breaker-threshold 5
```

- **Default**: `5`

#### `--circuit-breaker-timeout <N>`

Seconds to wait before transitioning from open to half-open state.

```bash
smg --circuit-breaker-timeout 30
```

- **Default**: `30`

---

### Health Checks

#### `--health-check-interval <DURATION>`

Interval between health checks.

```bash
smg --health-check-interval 10s
```

- **Default**: `10s`
- **Format**: Duration string (e.g., `5s`, `1m`)

#### `--health-check-timeout <DURATION>`

Timeout for health check requests.

```bash
smg --health-check-timeout 5s
```

- **Default**: `5s`

#### `--health-check-path <PATH>`

Path to use for worker health checks.

```bash
smg --health-check-path /health
```

- **Default**: `/health`

---

### Server Configuration

#### `--host <HOST>`

Host address to bind to.

```bash
smg --host 0.0.0.0
```

- **Default**: `127.0.0.1`

#### `--port <PORT>`

Port to listen on.

```bash
smg --port 8080
```

- **Default**: `30000`

#### `--prometheus-port <PORT>`

Port for Prometheus metrics endpoint.

```bash
smg --prometheus-port 9090
```

- **Default**: `29000`

---

### TLS Configuration

#### `--tls-cert-path <PATH>`

Path to TLS certificate for HTTPS server.

```bash
smg --tls-cert-path /etc/certs/server.crt --tls-key-path /etc/certs/server.key
```

- **Default**: None (HTTP)

#### `--tls-key-path <PATH>`

Path to TLS private key.

```bash
smg --tls-key-path /etc/certs/server.key
```

- **Default**: None

#### `--client-cert-path <PATH>`

Path to client certificate for mTLS to workers.

```bash
smg --client-cert-path /etc/certs/client.crt
```

- **Default**: None

#### `--client-key-path <PATH>`

Path to client private key for mTLS.

```bash
smg --client-key-path /etc/certs/client.key
```

- **Default**: None

#### `--ca-cert-path <PATH>`

Path to CA certificate for verifying worker certificates. Can be specified multiple times.

```bash
smg --ca-cert-path /etc/certs/ca.crt
```

- **Default**: System CA bundle
- **Multiple**: Yes

---

### Authentication

#### `--api-key <KEY>`

API key for authenticating client requests.

```bash
smg --api-key "your-secret-key"
```

- **Default**: None (no authentication)

---

### Logging

#### `--log-level <LEVEL>`

Log level for output.

```bash
smg --log-level debug
```

| Level | Description |
|-------|-------------|
| `error` | Errors only |
| `warn` | Warnings and errors |
| `info` | Informational messages |
| `debug` | Debug information |
| `trace` | Detailed trace logs |

- **Default**: `info`

---

### Other Options

#### `--help`

Print help information.

```bash
smg --help
```

#### `--version`

Print version information.

```bash
smg --version
```

---

## Environment Variables

All CLI options can also be set via environment variables with the `SMG_` prefix:

| Option | Environment Variable |
|--------|---------------------|
| `--worker-urls` | `SMG_WORKER_URLS` (comma-separated) |
| `--policy` | `SMG_POLICY` |
| `--host` | `SMG_HOST` |
| `--port` | `SMG_PORT` |
| `--prometheus-port` | `SMG_PROMETHEUS_PORT` |
| `--max-concurrent-requests` | `SMG_MAX_CONCURRENT_REQUESTS` |
| `--queue-size` | `SMG_QUEUE_SIZE` |
| `--queue-timeout-secs` | `SMG_QUEUE_TIMEOUT_SECS` |
| `--api-key` | `SMG_API_KEY` |
| `--log-level` | `SMG_LOG_LEVEL` or `RUST_LOG` |

### Example

```bash
export SMG_WORKER_URLS="http://worker1:8000,http://worker2:8000"
export SMG_POLICY="cache_aware"
export SMG_PORT="8080"
export SMG_API_KEY="secret"
export RUST_LOG="info"

smg
```

---

## Examples

### Basic Usage

```bash
smg --worker-urls http://localhost:8000
```

### Multiple Workers with Cache-Aware Routing

```bash
smg \
  --worker-urls http://w1:8000 http://w2:8000 http://w3:8000 \
  --policy cache_aware
```

### Production Configuration

```bash
smg \
  --worker-urls http://w1:8000 http://w2:8000 \
  --policy cache_aware \
  --max-concurrent-requests 100 \
  --queue-size 200 \
  --queue-timeout-secs 30 \
  --tls-cert-path /etc/certs/server.crt \
  --tls-key-path /etc/certs/server.key \
  --api-key "${API_KEY}" \
  --host 0.0.0.0 \
  --port 443 \
  --prometheus-port 9090 \
  --log-level info
```

### Kubernetes with Service Discovery

```bash
smg \
  --service-discovery \
  --selector app=sglang-worker \
  --service-discovery-namespace inference \
  --service-discovery-port 8000 \
  --policy cache_aware \
  --host 0.0.0.0
```

### Development Mode

```bash
RUST_LOG=debug smg \
  --worker-urls http://localhost:8000 \
  --host 127.0.0.1 \
  --port 30000
```
