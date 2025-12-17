# SmartRouter: Parallel Execution and Fast-Path Design

## Document Purpose

This document analyzes design options for Phase 2 (Parallel Execution) and Phase 3 (Fast-Path Classification), evaluates tradeoffs, and selects optimal architectures for implementation.

---

## Table of Contents

1. [Current Pipeline Analysis](#current-pipeline-analysis)
2. [Phase 2: Parallel Execution](#phase-2-parallel-execution)
3. [Phase 3: Fast-Path Classification](#phase-3-fast-path-classification)
4. [Integration Strategy](#integration-strategy)
5. [Risk Analysis](#risk-analysis)
6. [Implementation Plan](#implementation-plan)

---

## Current Pipeline Analysis

### Sequential Flow (Current)

```
User Query
    ↓
┌─────────────────────────────────────────┐
│  1. Interpretation (LLM)    500-800ms   │ ← Can run in parallel with warm-up
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│  2. Decomposition (LLM)     800-1200ms  │ ← Can run in parallel with interpretation
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│  3. Routing (cached)        <50ms       │ ← Already optimized (Phase 1)
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│  4. Execution (parallel)    2000-5000ms │ ← Already parallel
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│  5. Synthesis (LLM)         800-1200ms  │ ← Can run in parallel with evaluation
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│  6. Evaluation (LLM)        500-800ms   │ ← Can run speculatively
└─────────────────────────────────────────┘

TOTAL: 4.6-8.1 seconds
```

### Bottleneck Analysis

| Phase | Current | Parallelizable? | Dependency |
|-------|---------|-----------------|------------|
| Interpretation | 500-800ms | ✅ Yes (with decomposition) | None |
| Decomposition | 800-1200ms | ✅ Yes (with interpretation) | Needs QueryIntent |
| Routing | <50ms | ❌ No (already fast) | Needs Subqueries |
| Execution | 2000-5000ms | ✅ Already parallel | Needs Routes |
| Synthesis | 800-1200ms | ✅ Yes (with evaluation) | Needs Responses |
| Evaluation | 500-800ms | ✅ Yes (speculative) | Needs Answer |

**Key Insight**: Interpretation and Decomposition have circular dependency (Decomposition needs Intent), but we can use speculative execution or parallel LLM calls with shared context.

---

## Phase 2: Parallel Execution

### Design Options

#### Option A: Speculative Decomposition

**Concept**: Run interpretation and decomposition simultaneously, decomposition speculates on complexity.

```
Query → ┬→ Interpretation (LLM) ────→ Intent
        │                              ↓
        └→ Decomposition (LLM) ─→ Subqueries (speculative)
                                       ↓
                                  Validation: If intent=SIMPLE, discard subqueries
                                              If intent=COMPLEX, use subqueries
```

**Pros**:
- ✅ Maximum parallelism (both run simultaneously)
- ✅ 50% latency reduction if both succeed
- ✅ Simple implementation (fire-and-forget decomposition)

**Cons**:
- ❌ Wasted LLM call if query is SIMPLE (30-40% of queries)
- ❌ Decomposition may be incorrect without intent context
- ❌ Increased token usage (~30% more)
- ❌ Rate limit risk

**Estimated Impact**: 600-900ms reduction (complex queries only)

---

#### Option B: Intelligent Speculation with Early Abort

**Concept**: Run interpretation first, quickly assess if complex, then run decomposition in parallel with remaining interpretation processing.

```
Query → Interpretation (LLM) ──→ Quick complexity check (first 100 tokens)
                                           ↓
                          Is likely complex? ──Yes→ Start Decomposition (parallel)
                                           ↓
                                          No → Continue interpretation only
```

**Pros**:
- ✅ No wasted calls for SIMPLE queries
- ✅ Decomposition has intent context (more accurate)
- ✅ 40% latency reduction with minimal waste
- ✅ Can abort decomposition if intent determined as SIMPLE

**Cons**:
- ❌ More complex implementation (streaming detection)
- ❌ Requires streaming LLM support
- ❌ Only ~300-400ms gain (not full parallelism)

**Estimated Impact**: 300-400ms reduction (complex queries only)

---

#### Option C: Synthesis + Evaluation Parallelism

**Concept**: Run synthesis first, then immediately start speculative evaluation while synthesis completes.

```
Responses → Synthesis (LLM) ────→ Answer
                 ↓ (start after 100 tokens)
            Evaluation (LLM, speculative) → Quality scores
```

**Pros**:
- ✅ Always beneficial (works for all query types)
- ✅ No wasted calls (evaluation always needed)
- ✅ 200-400ms reduction
- ✅ Simpler than interpretation/decomposition parallelism

**Cons**:
- ❌ Evaluation may start on incomplete answer
- ❌ Requires answer buffering

**Estimated Impact**: 200-400ms reduction (all queries)

---

#### Option D: Hybrid Approach (Recommended)

**Concept**: Combine C (always beneficial) + B (when safe)

```
Phase 1: Query Analysis (parallel when safe)
    Query → Interpretation ──→ Intent
                ↓ (if early signal = COMPLEX)
            Decomposition (parallel)

Phase 2: Synthesis + Evaluation (always parallel)
    Responses → Synthesis ────→ Answer
                    ↓ (immediate start)
                Evaluation → Quality scores
```

**Pros**:
- ✅ Maximum benefit with minimal risk
- ✅ ~500-700ms reduction across all query types
- ✅ No wasted calls for SIMPLE queries
- ✅ Evaluation parallelism always beneficial

**Cons**:
- ❌ Moderate implementation complexity
- ❌ Requires careful coordination

**Estimated Impact**: 500-700ms reduction (30-40% overall latency)

---

### Selected Design: Option D (Hybrid Approach)

**Rationale**:
1. **Synthesis + Evaluation** parallelism is always beneficial (no downside)
2. **Interpretation + Decomposition** parallelism only when early signal indicates complexity
3. Balances performance gain with token usage and complexity

**Implementation Strategy**:

1. **Synthesis + Evaluation Parallelism** (Low Risk)
   - Use `asyncio.gather()` to run both concurrently
   - Evaluation starts immediately after synthesis begins
   - Wait for both to complete

2. **Interpretation + Decomposition Parallelism** (Controlled Risk)
   - Analyze query keywords for complexity hints
   - If query has "and", "also", multiple "?", or 3+ domains → likely complex
   - Launch decomposition speculatively
   - Cancel decomposition if interpretation determines SIMPLE

---

## Phase 3: Fast-Path Classification

### Design Options

#### Option A: Keyword-Based Pre-Classifier

**Concept**: Use regex and keyword matching before LLM interpretation.

```
Query → Keyword Matcher ──→ Match? ──Yes→ Direct routing (skip LLM)
                             ↓
                            No → LLM Interpretation (normal flow)
```

**Patterns**:
```python
SIMPLE_PATTERNS = {
    "greeting": r"\b(hi|hello|hey|greetings)\b",
    "farewell": r"\b(bye|goodbye|see you|farewell)\b",
    "gratitude": r"\b(thanks|thank you|thx|appreciate)\b",
    "how_are_you": r"\bhow (are|r) (you|u)\b",
}
```

**Pros**:
- ✅ 95%+ latency reduction for matched queries
- ✅ Zero LLM token usage
- ✅ Simple implementation
- ✅ Deterministic (no variability)

**Cons**:
- ❌ Limited coverage (~20-30% of queries)
- ❌ Maintenance overhead (pattern updates)
- ❌ May miss nuanced queries
- ❌ False positives risk

**Estimated Impact**: 1.5-2.5 seconds reduction (simple queries only, 20-30% of total)

---

#### Option B: Lightweight ML Classifier

**Concept**: Use a small ML model (e.g., DistilBERT) for classification.

```
Query → ML Classifier (50-100ms) ──→ Confidence > 0.9? ──Yes→ Direct routing
                                           ↓
                                          No → LLM Interpretation
```

**Pros**:
- ✅ Higher coverage (~50-60% of queries)
- ✅ More nuanced understanding than keywords
- ✅ Fast inference (50-100ms)
- ✅ Learns patterns over time

**Cons**:
- ❌ Requires training data
- ❌ Model deployment complexity
- ❌ 50-100ms overhead for non-matched queries
- ❌ Additional dependency

**Estimated Impact**: 1.2-2.0 seconds reduction (50-60% of queries)

---

#### Option C: LLM Streaming with Early Exit

**Concept**: Use streaming LLM, exit early when classification is clear.

```
Query → LLM (streaming) ──→ First 50 tokens ──→ Complexity clear? ──Yes→ Early exit
                                                        ↓
                                                       No → Continue
```

**Pros**:
- ✅ Uses existing LLM (no new components)
- ✅ 40-50% faster than full LLM call
- ✅ No false positives (same model)
- ✅ Works for all queries

**Cons**:
- ❌ Still uses LLM tokens
- ❌ Only ~200-300ms reduction
- ❌ Requires streaming support

**Estimated Impact**: 200-300ms reduction (all queries)

---

#### Option D: Hybrid Fast-Path (Recommended)

**Concept**: Combine keyword pre-filter + LLM streaming.

```
Query → Keyword Matcher ──→ Matched? ──Yes→ Direct routing (no LLM)
             ↓                          (20-30% of queries)
            No
             ↓
        LLM Streaming ──→ Early exit when possible
                          (remaining 70-80%)
```

**Pros**:
- ✅ Best of both worlds
- ✅ Zero LLM calls for simple patterns
- ✅ Faster LLM processing for others
- ✅ Minimal maintenance (small keyword set)

**Cons**:
- ❌ Moderate implementation complexity
- ❌ Requires careful pattern selection

**Estimated Impact**:
- Simple pattern matches: 1.5-2.5s reduction (20-30% of queries)
- Other queries: 200-300ms reduction (70-80% of queries)
- **Overall: 600-900ms average reduction**

---

### Selected Design: Option D (Hybrid Fast-Path)

**Rationale**:
1. **High-confidence patterns** get immediate routing (chitchat, greetings)
2. **Remaining queries** use existing LLM with streaming optimization
3. No ML deployment complexity
4. Easy to extend pattern set over time

**Implementation Strategy**:

1. **Pre-Classifier Patterns** (Conservative set):
   ```python
   FAST_PATH_PATTERNS = {
       "chitchat_greeting": (
           r"^(hi|hello|hey|greetings|howdy)(\s|!|\.|\?)*$",
           "chitchat",
           QueryComplexity.SIMPLE
       ),
       "chitchat_farewell": (
           r"^(bye|goodbye|see you|farewell|goodnight)(\s|!|\.)*$",
           "chitchat",
           QueryComplexity.SIMPLE
       ),
       "chitchat_gratitude": (
           r"^(thanks|thank you|thx|ty|appreciate it)(\s|!|\.)*$",
           "chitchat",
           QueryComplexity.SIMPLE
       ),
       "chitchat_status": (
           r"^how (are|r) (you|u)(\s|\?|!)*$",
           "chitchat",
           QueryComplexity.SIMPLE
       ),
   }
   ```

2. **LLM Streaming** (For non-matched queries):
   - Use streaming API
   - Parse JSON incrementally
   - Exit as soon as `complexity` field is complete

---

## Integration Strategy

### Component Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     SmartRouter                          │
└────────────┬─────────────────────────────────────────────┘
             │
    ┌────────▼────────┐
    │ FastPathRouter  │ ← NEW: Pre-classification
    └────────┬────────┘
             │
         No match
             ↓
    ┌────────▼───────────┐
    │ ParallelOrchestrator│ ← NEW: Coordinates parallel execution
    └────────┬────────────┘
             │
      ┌──────┴───────┐
      │              │
┌─────▼──────┐  ┌───▼──────────┐
│Interpretation│ │ Decomposition│ (Parallel when safe)
└─────┬────────┘ └───┬──────────┘
      │              │
      └──────┬───────┘
             ↓
      Existing Pipeline
             ↓
      ┌─────▼────┐  ┌──▼──────────┐
      │ Synthesis │  │ Evaluation  │ (Always parallel)
      └───────────┘  └─────────────┘
```

### New Components

1. **`FastPathRouter`** (Phase 3)
   - Keyword pattern matching
   - Direct routing for matched queries
   - Falls through to LLM for non-matches

2. **`ParallelOrchestrator`** (Phase 2)
   - Coordinates parallel LLM calls
   - Manages cancellation for speculation
   - Handles Synthesis + Evaluation parallelism

3. **`StreamingInterpreter`** (Phase 3)
   - Wraps QueryInterpreter with streaming
   - Early exit when classification is clear
   - Backward compatible with existing interface

---

## Risk Analysis

### Phase 2 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Wasted LLM calls** | Medium | High | Only speculate when early signal indicates complexity |
| **Race conditions** | Low | High | Use asyncio.gather() and proper locking |
| **Increased complexity** | High | Medium | Comprehensive testing, clear documentation |
| **Token limit exceeded** | Low | Medium | Monitor token usage, implement circuit breaker |

### Phase 3 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **False positives** | Medium | High | Conservative pattern set, logging/monitoring |
| **Pattern maintenance** | Medium | Low | Small pattern set, document update process |
| **Missed optimization** | High | Low | Acceptable - keyword matching is bonus |
| **Regex complexity** | Low | Low | Use simple patterns, avoid complex lookaheads |

---

## Implementation Plan

### Phase 2: Parallel Execution

#### Step 1: Synthesis + Evaluation Parallelism (Low Risk)

**Files to modify**:
- `smartrouter.py`: Update `_handle_complex_query_with_trace()`

**Implementation**:
```python
# Before (sequential)
with trace_capture.phase("synthesis"):
    answer = await self.synthesizer.synthesize(...)

with trace_capture.phase("evaluation"):
    evaluation = await self.judge.evaluate(answer, query)

# After (parallel)
async with trace_capture.parallel_phase("synthesis", "evaluation"):
    synthesis_task = self.synthesizer.synthesize(...)
    evaluation_task = self.judge.evaluate_streaming(...)  # Starts immediately

    answer, evaluation = await asyncio.gather(synthesis_task, evaluation_task)
```

**Testing**:
- Verify both phases run concurrently
- Measure latency reduction
- Test error handling (one fails, other succeeds)

---

#### Step 2: Interpretation + Decomposition Speculation (Medium Risk)

**Files to create**:
- `asdrp/agents/router/parallel_orchestrator.py`

**Files to modify**:
- `smartrouter.py`: Use ParallelOrchestrator

**Implementation**:
```python
class ParallelOrchestrator:
    async def interpret_and_decompose(
        self,
        query: str,
        interpreter: IQueryInterpreter,
        decomposer: IQueryDecomposer
    ) -> Tuple[QueryIntent, Optional[List[Subquery]]]:
        """
        Intelligently parallelize interpretation and decomposition.

        Strategy:
        1. Check query for complexity hints
        2. If hints indicate COMPLEX, run both in parallel
        3. If SIMPLE, run interpretation only
        4. Return intent and subqueries (or None)
        """
        # Quick complexity heuristic
        if self._is_likely_complex(query):
            # Run both in parallel
            intent_task = interpreter.interpret(query)
            decompose_task = decomposer.decompose_from_query(query)

            intent, subqueries = await asyncio.gather(
                intent_task,
                decompose_task
            )

            # Validate: If intent is SIMPLE, discard subqueries
            if intent.complexity == QueryComplexity.SIMPLE:
                return intent, None

            return intent, subqueries
        else:
            # Run interpretation only
            intent = await interpreter.interpret(query)
            return intent, None

    def _is_likely_complex(self, query: str) -> bool:
        """
        Quick heuristic to detect likely complex queries.

        Indicators:
        - Multiple "and" conjunctions
        - Multiple question marks
        - Query length > 100 chars
        - Multiple domain keywords
        """
        conjunctions = query.lower().count(" and ") + query.lower().count(" also ")
        questions = query.count("?")

        return (
            conjunctions >= 2 or
            questions >= 2 or
            len(query) > 100
        )
```

**Testing**:
- Test with SIMPLE queries (should not speculate)
- Test with COMPLEX queries (should speculate successfully)
- Test speculation cancellation
- Measure token usage increase

---

### Phase 3: Fast-Path Classification

#### Step 1: FastPathRouter Implementation

**Files to create**:
- `asdrp/agents/router/fast_path_router.py`
- `tests/asdrp/agents/router/test_fast_path_router.py`

**Implementation**:
```python
class FastPathRouter:
    """
    Pre-classifier for simple queries using keyword patterns.

    Provides immediate routing for high-confidence simple queries
    (chitchat, greetings, etc.) without LLM interpretation.
    """

    PATTERNS = {
        "chitchat_greeting": (
            r"^(hi|hello|hey|greetings|howdy)(\s|!|\.|\?)*$",
            ["conversation", "social"],
            QueryComplexity.SIMPLE,
        ),
        # ... more patterns
    }

    def try_fast_path(self, query: str) -> Optional[QueryIntent]:
        """
        Attempt to classify query using keyword patterns.

        Returns:
            QueryIntent if matched, None otherwise
        """
        query_normalized = query.strip().lower()

        for pattern_name, (regex, domains, complexity) in self.PATTERNS.items():
            if re.match(regex, query_normalized, re.IGNORECASE):
                logger.info(f"Fast-path match: {pattern_name}")
                return QueryIntent(
                    query_text=query,
                    complexity=complexity,
                    domains=domains,
                    requires_synthesis=False,
                    metadata={"fast_path": pattern_name}
                )

        return None  # No match, fall through to LLM
```

**Testing**:
- Test pattern matching accuracy
- Test case insensitivity
- Test false positive rate
- Test fallthrough for non-matches

---

#### Step 2: Integration with SmartRouter

**Files to modify**:
- `smartrouter.py`: Add FastPathRouter before interpretation

**Implementation**:
```python
async def route_query(self, query: str, ...) -> SmartRouterExecutionResult:
    trace_capture = TraceCapture()

    # NEW: Try fast-path first
    fast_path_intent = self.fast_path_router.try_fast_path(query)

    if fast_path_intent:
        logger.info("Using fast-path routing (skipped LLM interpretation)")
        intent = fast_path_intent
        trace_capture.record_data({"fast_path": True})
    else:
        # Normal LLM interpretation
        with trace_capture.phase("interpretation"):
            intent = await self.interpreter.interpret(query)
        trace_capture.record_data({"fast_path": False})

    # Continue with normal pipeline...
```

---

## Expected Performance Impact

### Phase 2 Impact

| Query Type | Before | After | Improvement |
|------------|--------|-------|-------------|
| Chitchat | 1.5s | 1.1s | 27% (400ms) |
| Simple | 2.5s | 1.9s | 24% (600ms) |
| Complex (3 agents) | 5.5s | 4.4s | 20% (1100ms) |

**Average Reduction**: ~700ms (25-30% overall)

### Phase 3 Impact

| Query Type | Before | After | Improvement |
|------------|--------|-------|-------------|
| Chitchat (fast-path) | 1.5s | 0.2s | 87% (1300ms) |
| Simple (LLM streaming) | 2.5s | 2.2s | 12% (300ms) |
| Complex | 5.5s | 5.2s | 5% (300ms) |

**Average Reduction**: ~400-600ms (15-25% overall)

### Combined (Phase 2 + 3)

| Query Type | Before | After Phase 2 | After Phase 3 | Total Improvement |
|------------|--------|---------------|---------------|-------------------|
| Chitchat | 1.5s | 1.1s | 0.2s | 87% (1300ms) |
| Simple | 2.5s | 1.9s | 1.6s | 36% (900ms) |
| Complex | 5.5s | 4.4s | 4.1s | 25% (1400ms) |

**Overall Average Reduction**: ~1.0-1.2 seconds (30-40%)

---

## Success Metrics

### Performance Metrics

- [ ] P50 latency reduced by 30%
- [ ] P95 latency reduced by 25%
- [ ] Fast-path hit rate > 20%
- [ ] Token usage increase < 10%

### Quality Metrics

- [ ] Answer accuracy unchanged (within 2%)
- [ ] Fast-path false positive rate < 1%
- [ ] No increase in error rate

### Operational Metrics

- [ ] All tests passing (> 95%)
- [ ] Documentation complete
- [ ] Monitoring dashboards updated

---

## Rollout Strategy

### Phase 2A: Synthesis + Evaluation Parallelism
**Risk**: Low
**Rollout**: Immediate (production-ready)

### Phase 2B: Interpretation + Decomposition Speculation
**Risk**: Medium
**Rollout**: Feature flag, gradual rollout (10% → 50% → 100%)

### Phase 3A: Fast-Path Router
**Risk**: Low
**Rollout**: Immediate (conservative patterns only)

### Phase 3B: Streaming Optimization
**Risk**: Medium
**Rollout**: Feature flag, monitor token usage

---

## Conclusion

**Recommended Implementation Order**:

1. ✅ **Phase 1**: Static Caching (COMPLETE)
2. 🔄 **Phase 2A**: Synthesis + Evaluation Parallelism (Low risk, high value)
3. 🔄 **Phase 3A**: Fast-Path Router (Low risk, high value for chitchat)
4. 🔄 **Phase 2B**: Interpretation + Decomposition Speculation (Medium risk, feature flag)
5. 📋 **Phase 3B**: Streaming Optimization (Optional, if needed)

**Expected Total Impact**: 1.0-1.5 seconds reduction (30-40% overall latency improvement)

This design provides a clear path to significant performance improvements while managing risk through incremental rollout and comprehensive testing.
