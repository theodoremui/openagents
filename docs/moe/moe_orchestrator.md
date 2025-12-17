# MoE Orchestrator (Mixture of Experts)

**Purpose**: Route a user query to the smallest set of relevant specialist agents, execute them in parallel when needed, and synthesize a final response (optionally including interactive map payloads).

This document is the **canonical** MoE reference. All MoE documentation has been consolidated here to reduce duplication.

---

## Table of Contents

- [MoE Orchestrator (Mixture of Experts)](#moe-orchestrator-mixture-of-experts)
  - [Table of Contents](#table-of-contents)
  - [High-level Pipeline](#high-level-pipeline)
  - [Fast-Path Bypass (Chitchat)](#fast-path-bypass-chitchat)
    - [Goal](#goal)
    - [Behavior](#behavior)
    - [Configuration](#configuration)
  - [Dynamic Expert Selection (Relevance Gap)](#dynamic-expert-selection-relevance-gap)
    - [Problem](#problem)
    - [Solution: Relevance Gap Filter](#solution-relevance-gap-filter)
    - [Configuration](#configuration-1)
  - [Selection Strategies: Semantic vs Capability-Based](#selection-strategies-semantic-vs-capability-based)
    - [1) Semantic Selection (Embeddings)](#1-semantic-selection-embeddings)
    - [2) Capability-Based Selection (Keyword/Capability Matching)](#2-capability-based-selection-keywordcapability-matching)
  - [Map / Directions Routing Fixes](#map--directions-routing-fixes)
    - [Core Issue](#core-issue)
    - [Fixes Applied](#fixes-applied)
    - [Interactive Map Preservation](#interactive-map-preservation)
  - [Fallback Behavior](#fallback-behavior)
  - [Testing](#testing)
    - [Unit tests (fast)](#unit-tests-fast)
    - [Integration tests (slow)](#integration-tests-slow)
  - [Troubleshooting](#troubleshooting)
    - [Fast-path not triggering](#fast-path-not-triggering)
    - [Semantic selection failing](#semantic-selection-failing)

---

## High-level Pipeline

At a high level, MoE runs:

1. **Fast-path detection** (optional): shunt chitchat/small-talk to a single lightweight agent.
2. **Cache lookup** (optional): return a cached response for identical queries.
3. **Expert selection**: choose relevant experts (semantic embeddings or capability-based).
4. **Parallel execution**: run selected agents concurrently with per-expert timeouts.
5. **Result mixing**: synthesize a coherent answer and preserve/emit interactive payloads.
6. **Fallback**: on total failure, run the configured fallback agent (usually `one`).

Key code:
- `asdrp/orchestration/moe/orchestrator.py`
- `asdrp/orchestration/moe/fast_path.py`
- `asdrp/orchestration/moe/semantic_selector.py`
- `asdrp/orchestration/moe/expert_selector.py`
- `asdrp/orchestration/moe/expert_executor.py`
- `asdrp/orchestration/moe/result_mixer.py`

---

## Fast-Path Bypass (Chitchat)

### Goal

Avoid running full MoE for small talk (e.g. "hello", "what's up", "not much") to minimize latency and cost.

### Behavior

- If a query matches a chitchat pattern, MoE **bypasses selection + multi-agent execution + synthesis** and directly executes the `chitchat` agent.
- Detection supports:
  - Embedding-based similarity (when embeddings are available)
  - Lexical fallback (works without `OPENAI_API_KEY`)

### Configuration

In `config/moe.yaml`:

```yaml
moe:
  fast_path_enabled: true
  fast_path_threshold: 0.75
```

Tuning guidance:
- `0.85`: strict (fewer bypasses)
- `0.75`: balanced (recommended)
- `0.65`: loose (more bypasses)

---

## Dynamic Expert Selection (Relevance Gap)

### Problem

Selecting a fixed number of experts (e.g. always 3) wastes compute, increases latency, and dilutes quality on simple/single-domain queries.

### Solution: Relevance Gap Filter

After scoring experts, MoE applies a relevance gap strategy:

- Always select the top expert.
- Add the next expert only if the relevance **gap** from the previous is small.
- Stop when the gap exceeds a threshold or `top_k_experts` is reached.

This yields **1–N** experts depending on query complexity:
- "hello" → 1 expert (`chitchat`)
- "TSLA stock" → 1 expert (`finance`)
- "San Carlos" → 2 experts (`geo`, `map`)

### Configuration

```yaml
moe:
  top_k_experts: 3
  confidence_threshold: 0.5
  relevance_gap_threshold: 0.15  # semantic default
  # relevance_gap_threshold: 0.20  # capability/lexical default
```

---

## Selection Strategies: Semantic vs Capability-Based

MoE supports two selection strategies:

### 1) Semantic Selection (Embeddings)

**Best accuracy**, small cost/latency (~50ms per query embedding).

How it works:
- Pre-compute embeddings for each expert group (from expert capabilities).
- Embed the incoming query.
- Choose top experts by cosine similarity, filtered by threshold + relevance gap.

Requirements:
- `OPENAI_API_KEY` present (and embeddings calls working)

Defensive behavior:
- If embedding responses are malformed or missing data, selection raises a controlled `ExpertSelectionException`.
- The orchestrator can fail open to a deterministic selector for that request.

### 2) Capability-Based Selection (Keyword/Capability Matching)

**Fast and deterministic**, no API key required.

Key improvements:
- Bidirectional substring matching (`map` ↔ `maps`, `driving` ↔ `drive`)
- Punctuation-stripping keyword extraction to avoid losing location tokens

---

## Map / Directions Routing Fixes

### Core Issue

Map/directions queries can be misrouted if:
- Capability matching is too rigid (e.g., `map` not matching `maps`)
- Stop word filtering removes intent words and/or location tokens
- Expert selection truncation drops `map`/`yelp_mcp` due to `top_k_experts`

### Fixes Applied

- **Better keyword/capability matching** (bidirectional + exact matches).
- **Stop word tuning** (avoid removing intent/location signals incorrectly).
- **Map intent prioritization**: for map/restaurant queries, ensure `map` and `yelp_mcp` aren’t dropped when truncating.

### Interactive Map Preservation

The mixer is instructed (and defensively implemented) to preserve interactive payload blocks (e.g. `{"type":"interactive_map", ...}`) so the frontend can render maps reliably.

---

## Fallback Behavior

MoE uses two “fallback” concepts:

1. **Selector fallback**: if semantic selection fails with `ExpertSelectionException`, MoE can fall back to capability selection for that request.
2. **Pipeline fallback agent**: if MoE cannot execute any experts successfully (or hits an unexpected failure), it runs a configured fallback agent (commonly `one`).

Config (example):

```yaml
error_handling:
  fallback_agent: one
  fallback_message: "I apologize, but I encountered an issue processing your request."
```

---

## Testing

### Unit tests (fast)

- Fast-path lexical routing:
  - `tests/asdrp/orchestration/moe/test_fast_path_chitchat.py`
- Defensive embedding shape tests:
  - `tests/asdrp/orchestration/moe/test_embedding_shape_defensive.py`
- Per-expert timing trace correctness:
  - `tests/asdrp/orchestration/moe/test_trace_per_expert_timings.py`

### Integration tests (slow)

MoE integration tests are marked `slow` and are skipped by default:
- `tests/asdrp/orchestration/moe/test_integration.py`

Run slow tests explicitly:

```bash
pytest -m slow
```

---

## Troubleshooting

### Fast-path not triggering

- Ensure `fast_path_enabled: true`
- Ensure `OPENAI_API_KEY` is set if you rely on embedding-based detection
- Check logs for fast-path initialization and similarity output

### Semantic selection failing

- Confirm `OPENAI_API_KEY` is present
- If embedding responses are malformed, MoE should degrade gracefully to capability selection (or configured fallback agent on unexpected failures)


