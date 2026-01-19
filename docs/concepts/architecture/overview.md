---
title: Architecture Overview
---

# Architecture Overview

This page describes the high-level architecture of Shepherd Model Gateway.

<div class="objectives" markdown>

#### What you'll learn

- How SMG adapts to different worker types
- The role of registries, control plane, and data plane
- Request flow through the gateway

</div>

---

## System Architecture

```mermaid
flowchart LR
    subgraph SMG["SMG Gateway"]
        API["API"]
        Router["Router"]
        API --> Router
    end

    Client([Clients]) --> API
    Router --> gRPC([gRPC Workers])
    Router --> HTTP([HTTP Workers])
    Router --> Ext([External APIs])
```

SMG adapts its behavior based on worker type:

| Worker Type | Gateway Behavior |
|-------------|------------------|
| **gRPC** | Full server — tokenization, chat templates, tool parsing, MCP, detokenization |
| **HTTP** | Proxy — load balancing, health checks, PD disaggregation |
| **External** | Router — model discovery, provider abstraction |

---

## Internal Components

### Registries

| Registry | Purpose |
|----------|---------|
| **Model** | Available models and backend mappings |
| **Tokenizer** | Tokenizers for gateway-side processing (gRPC mode) |
| **LB Policy** | Load balancing configurations |
| **Chat History** | Multi-turn conversation context |
| **WASM Plugins** | Custom logic extensions |

---

## Control Plane

The control plane manages the **operational state** of the system. It doesn't handle user requests directly but maintains the information needed for routing decisions.

### Components

| Component | Function |
|-----------|----------|
| **Worker Manager** | Registers workers, tracks capabilities, manages lifecycle |
| **Health Checker** | Probes workers periodically, updates health status |
| **Service Discovery** | Discovers workers in Kubernetes via pod selectors |
| **Load Monitor** | Tracks active requests and queue depths per worker |

The control plane answers questions like:

- Which workers are available?
- How healthy is each worker?
- What's the current load on each worker?

[Learn more about the Control Plane →](control-plane.md)

---

## Data Plane

The data plane handles **every user request**. It must be fast, reliable, and correct.

### Routing Paths

| Path | Protocol | Use Case |
|------|----------|----------|
| **gRPC Router** | gRPC | Token-level streaming with gateway-side tokenization |
| **HTTP Router** | HTTP | OpenAI-compatible passthrough |
| **3rd Party Router** | HTTP | External provider routing (OpenAI, Anthropic, etc.) |

### Middleware Components

| Component | Function |
|-----------|----------|
| **Rate Limiter** | Enforces request limits with token bucket algorithm |
| **Circuit Breaker** | Prevents routing to failing workers |
| **Retry Handler** | Retries failed requests with exponential backoff |
| **Metrics Collector** | Records latency, throughput, and error rates |

### Response Processing

| Component | Function |
|-----------|----------|
| **Tool Parser** | Extracts function/tool calls from model outputs |
| **Reasoning Parser** | Parses chain-of-thought and structured reasoning |
| **MCP Handler** | Model Context Protocol for tool execution loops |

The data plane answers questions like:

- Which routing path should this request use?
- Which worker should handle this request?
- Should this request be retried?
- Is the client within rate limits?

[Learn more about the Data Plane →](data-plane.md)

---

## Request Flow

Here's how a typical request flows through SMG:

```mermaid
sequenceDiagram
    participant C as Client
    participant MW as Middleware
    participant RM as Router Manager
    participant PATH as Routing Path
    participant W as Worker/Provider

    C->>MW: POST /v1/chat/completions
    MW->>MW: Rate limit, assign ID
    MW->>RM: Route request
    RM->>RM: Select routing path
    RM->>PATH: Forward to path
    PATH->>PATH: Path-specific processing
    PATH->>W: Forward to backend
    W-->>PATH: Response
    PATH->>PATH: Parse tools, handle MCP
    PATH-->>C: Stream response
```

### Step by Step

1. **Middleware Processing**: Request passes through rate limiting, gets assigned a request ID, and metrics are recorded.

2. **Path Selection**: Router manager determines which routing path to use (gRPC, HTTP, or 3rd Party).

3. **Path-Specific Processing**:
   - **gRPC**: Apply chat template, tokenize, cache tokens, load balance
   - **HTTP**: Regular or Prefill-Decode mode, load balance
   - **3rd Party**: Model discovery, provider routing

4. **Backend Communication**: Request is forwarded to the appropriate backend or external provider.

5. **Response Processing**: Tools are parsed, MCP handlers execute if needed, response is built and streamed.

---

## Deployment Topologies

SMG supports several deployment patterns:

### Single Gateway

The simplest topology with one SMG instance routing to multiple workers.

```mermaid
flowchart LR
    C[Clients] --> G[SMG]
    G --> W1[Worker 1]
    G --> W2[Worker 2]
    G --> W3[Worker 3]
```

**Best for**: Development, small deployments

### High Availability

Multiple SMG instances behind a load balancer.

```mermaid
flowchart LR
    C[Clients] --> LB[Load Balancer]
    LB --> G1[SMG 1]
    LB --> G2[SMG 2]
    G1 --> W1[Worker 1]
    G1 --> W2[Worker 2]
    G2 --> W1
    G2 --> W2
```

**Best for**: Production deployments requiring HA

### Prefill-Decode Disaggregation

Separate workers for prefill and decode phases.

```mermaid
flowchart LR
    C[Clients] --> G[SMG]
    G --> P[Prefill Workers]
    P --> D[Decode Workers]
    D --> G
```

**Best for**: High-throughput deployments optimizing for TTFT and TPOT

---

## What's Next?

- [Control Plane](control-plane.md) — Deep dive into worker management
- [Data Plane](data-plane.md) — Deep dive into request routing
- [Load Balancing](../routing/load-balancing.md) — Understand routing policies
