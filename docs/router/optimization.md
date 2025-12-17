# SmartRouter Performance Optimization - Implementation Plan

**Date**: December 8, 2025
**Status**: Planning Phase
**Goal**: Reduce SmartRouter latency by 30-40% through strategic optimizations

---

## Current Status

### ✅ Completed

#### Phase 1: Caching Optimization
- Agent instance caching implemented
- Configuration caching implemented
- Session caching implemented
- All tests passing

#### Session Memory Fix (CRITICAL - December 8, 2025)
**Problem**: Session context lost after 2-3 conversation turns
**Root Cause**: Creating new SQLiteSession objects on every LLM call instead of reusing persistent sessions
**Solution**: Following OpenAI best practices:
- Create session ONCE in `__init__` with file-based storage (`db_path=".smartrouter_sessions.db"`)
- Store as instance variable `self._session`
- Reuse same session object across all calls
- Applied to all 4 LLM components (QueryInterpreter, QueryDecomposer, ResultSynthesizer, LLMJudge)

**Results**:
- ✅ Deep conversation memory now working indefinitely
- ✅ All 59 SmartRouter tests passing
- ✅ File-based persistent storage created
- ✅ Full documentation: `SMARTROUTER_SESSION_FIX_FINAL.md`

#### Phase 3A: Fast-Path Router Implementation
**Implementation**: Keyword-based pre-classification for chitchat queries
- 8 pattern categories (greetings, farewells, gratitude, status, affirmations, negations, help, clarification)
- Zero LLM calls for matched patterns
- Regex-based matching with metrics tracking
- 33 unit tests passing

**Expected Impact**: 1.3-2.5s reduction (83% faster) for 20-30% of queries

#### Phase 3B: Fast-Path Integration
**Implementation**: Integrated fast-path into SmartRouter pipeline
- Fast-path check FIRST, before LLM interpretation
- Skip interpretation + evaluation for chitchat queries
- Graceful fallthrough for non-matched queries
- 13 integration tests passing

**Results**:
- ✅ End-to-end fast-path flow working
- ✅ All 285 SmartRouter tests passing
- ✅ Metrics tracking fast-path hit rate

### 📋 Pending (Not Yet Requested)
- Phase 2B: Parallel interpretation/decomposition speculation
- Phase 4: Performance instrumentation
- Phase 5: Comprehensive benchmarking and validation
- Results documentation

---

## Pipeline Analysis

### Current SmartRouter Flow (Sequential)

```
User Query
    ↓
1. QueryInterpreter (300-600ms)  ← LLM call
    ↓
2. QueryDecomposer (400-800ms)   ← LLM call (if COMPLEX)
    ↓
3. Routing (1-5ms)               ← Fast
    ↓
4. Execution (500-1500ms)        ← Parallel already
    ↓
5. Synthesis (400-700ms)         ← LLM call
    ↓
6. Evaluation (300-500ms)        ← LLM call
    ↓
Total: 1.9-4.1s (average: 3.0s)
```

### Bottlenecks Identified

1. **Sequential LLM calls** (Steps 1-2, 5-6): 1.4-2.6s
2. **Decomposition overhead**: 400-800ms (only for COMPLEX queries)
3. **Quality evaluation**: 300-500ms (every query)
4. **No fast-path for simple queries**: Full pipeline even for "hi"

---

## Optimization Strategies

### Phase 3B: Fast-Path Integration (PRIORITY 1)

**Goal**: Bypass LLM interpretation for chitchat queries
**Expected Impact**: 1.3-2.5s reduction for 20-30% of queries

#### Implementation Plan

```python
# smartrouter.py: route_query()

async def route_query(self, query: str, context: Optional[Dict] = None):
    trace_capture = TraceCapture()

    # STEP 0: Try fast-path FIRST (NEW)
    fast_path_intent = self.fast_path_router.try_fast_path(query)

    if fast_path_intent:
        # Fast-path hit: skip interpretation, go directly to routing
        with trace_capture.phase("fast_path"):
            trace_capture.record_data({
                "matched": True,
                "pattern": fast_path_intent.metadata["fast_path_pattern"],
                "confidence": 1.0
            })

        # Route directly with fast-path intent
        answer, agent_id = await self._handle_simple_query_with_trace(
            fast_path_intent, trace_capture
        )

        # Skip quality evaluation for chitchat (always acceptable)
        return SmartRouterExecutionResult(
            answer=answer,
            traces=trace_capture.get_traces(),
            total_time=trace_capture.get_total_time(),
            final_decision="fast_path",
            agents_used=[agent_id],
            success=True
        )

    # STEP 1: Standard interpretation (LLM)
    with trace_capture.phase("interpretation"):
        intent = await self.interpreter.interpret(query)
        ...
```

#### Changes Required

1. **Add FastPathRouter to SmartRouter.__init__**:
   ```python
   self.fast_path_router = FastPathRouter(enable_logging=True)
   ```

2. **Update route_query() flow**:
   - Try fast-path FIRST (before LLM)
   - If match: skip interpretation + skip evaluation
   - If no match: fall through to standard pipeline

3. **Add fast-path metrics**:
   - Track hit rate
   - Track latency savings
   - Log matched patterns

#### Testing Strategy

1. **Unit tests**: Fast-path integration
2. **Integration tests**: End-to-end fast-path flow
3. **Performance tests**: Verify latency reduction
4. **Fallback tests**: Ensure graceful fallthrough

**Estimated Implementation**: 2-3 hours
**Expected Benefit**: 1.3-2.5s for 20-30% of queries

---

### Phase 2B: Parallel Interpretation/Decomposition (PRIORITY 2)

**Goal**: Speculate decomposition in parallel with interpretation
**Expected Impact**: 300-600ms reduction for COMPLEX queries (30% of queries)

#### Design Options

##### Option A: Unconditional Speculation (Aggressive)
```python
# Always run interpretation + decomposition in parallel
interpretation_task = asyncio.create_task(interpreter.interpret(query))
decomposition_task = asyncio.create_task(decomposer.decompose_speculative(query))

intent = await interpretation_task

if intent.complexity == QueryComplexity.COMPLEX:
    subqueries = await decomposition_task  # Use result
else:
    decomposition_task.cancel()  # Discard
```

**Pros**:
- Maximum latency reduction (300-600ms)
- Simple implementation
- No complex decision logic

**Cons**:
- Wasted LLM calls 70% of time (SIMPLE queries)
- Increased API costs ($)
- Increased token usage

##### Option B: Early Signal Speculation (Conservative)
```python
# Start interpretation
intent_partial = await interpreter.interpret_with_streaming(query)

# If early signal suggests COMPLEX, start decomposition
if intent_partial.likely_complex():
    decomposition_task = asyncio.create_task(decomposer.decompose(...))
    intent = await interpreter.finalize()

    if intent.complexity == QueryComplexity.COMPLEX:
        subqueries = await decomposition_task
    else:
        decomposition_task.cancel()
else:
    intent = await interpreter.finalize()
```

**Pros**:
- Reduced waste (only speculate when likely COMPLEX)
- Lower API costs
- Still saves 300-600ms for COMPLEX queries

**Cons**:
- Requires streaming interpretation (more complex)
- May miss some COMPLEX queries (conservative)
- Adds complexity to interpreter

##### Option C: Synthesis/Evaluation Parallelism (Low-Hanging Fruit)
```python
# After execution, run synthesis + evaluation in parallel
synthesis_task = asyncio.create_task(synthesizer.synthesize(...))
answer = await synthesis_task

# Start evaluation IMMEDIATELY (don't wait for synthesis)
evaluation_task = asyncio.create_task(judge.evaluate(answer, query))
evaluation = await evaluation_task
```

**Pros**:
- Simple implementation (no speculation)
- No wasted calls (both always needed)
- 200-400ms reduction for ALL queries
- Zero downside

**Cons**:
- Smaller impact than Option A/B

#### Recommendation: **Start with Option C, then evaluate Option B**

**Rationale**:
1. **Option C is risk-free**: No wasted calls, simple, benefits all queries
2. **Option B requires more design**: Streaming interpretation needs careful implementation
3. **Option A is too wasteful**: 70% wasted calls not acceptable

#### Implementation Plan (Option C - Synthesis/Evaluation Parallel)

```python
# smartrouter.py: _handle_complex_query_with_trace()

# Step 6: Synthesize responses (TRACE)
with trace_capture.phase("synthesis"):
    synthesized = await self.synthesizer.synthesize(
        successful,
        intent.original_query
    )

    trace_capture.record_data({...})

# Step 7: Evaluate answer quality IN PARALLEL with synthesis completion
# (evaluation can start as soon as synthesis is done, no need to wait)
with trace_capture.phase("evaluation"):
    evaluation = await self.judge.evaluate(synthesized.answer, intent.original_query)
    trace_capture.record_data({...})
```

**Wait, this is already sequential in current code!**

Let me check if we can truly parallelize:

```python
# Current (Sequential):
synthesis_result = await synthesizer.synthesize(...)  # 400-700ms
evaluation_result = await judge.evaluate(synthesis_result.answer, ...)  # 300-500ms
# Total: 700-1200ms

# Potential Parallel (if evaluation doesn't need synthesis details):
# Can't truly parallelize because evaluation NEEDS the synthesized answer!
# Must be sequential.
```

**Conclusion**: Synthesis/Evaluation CANNOT be parallelized (evaluation depends on synthesis output).

#### Revised Recommendation: **Option B - Early Signal Speculation**

Since Option C doesn't work, we need Option B. But let's simplify:

##### Option D: Hybrid - Query Length Heuristic (SELECTED)

```python
# Use simple heuristic to predict complexity
async def route_query(self, query: str, ...):
    word_count = len(query.split())
    question_marks = query.count('?')

    # Heuristic: Likely COMPLEX if:
    # - More than 20 words, OR
    # - Multiple questions (>1 '?')
    likely_complex = word_count > 20 or question_marks > 1

    if likely_complex:
        # Speculative decomposition in parallel
        interpretation_task = asyncio.create_task(interpreter.interpret(query))
        decomposition_task = asyncio.create_task(decomposer.decompose_speculative(query))

        intent = await interpretation_task

        if intent.complexity == QueryComplexity.COMPLEX:
            subqueries = await decomposition_task  # Use result (saved 300-600ms!)
        else:
            decomposition_task.cancel()  # Wasted call (rare)
    else:
        # Standard path (no speculation)
        intent = await interpreter.interpret(query)
```

**Pros**:
- Simple heuristic (no streaming needed)
- High accuracy (long queries usually COMPLEX)
- Minimal waste (short queries are rarely COMPLEX)
- 300-600ms savings for true COMPLEX queries

**Cons**:
- Some false positives (wasted calls)
- Heuristic may miss edge cases

**Expected Waste Rate**: 10-15% (acceptable tradeoff)

#### Changes Required

1. **Add heuristic function**:
   ```python
   def _predict_complexity(self, query: str) -> bool:
       """Heuristic to predict if query is likely COMPLEX."""
       word_count = len(query.split())
       question_marks = query.count('?')
       sentence_count = len([s for s in query.split('.') if s.strip()])

       return (
           word_count > 20 or
           question_marks > 1 or
           sentence_count > 2
       )
   ```

2. **Update route_query() with speculation**:
   ```python
   if self._predict_complexity(query):
       # Parallel speculation
       ...
   ```

3. **Add decomposer method**:
   ```python
   async def decompose_speculative(self, query: str) -> List[Subquery]:
       """Speculative decomposition (may be cancelled)."""
       # Create temporary intent with COMPLEX assumption
       temp_intent = QueryIntent(
           original_query=query,
           complexity=QueryComplexity.COMPLEX,
           domains=["search"],
           requires_synthesis=True,
           metadata={"speculative": True}
       )
       return await self.decompose(temp_intent)
   ```

**Estimated Implementation**: 4-5 hours
**Expected Benefit**: 300-600ms for 30% of queries (COMPLEX)

---

### Phase 4: Performance Instrumentation (PRIORITY 3)

**Goal**: Add detailed timing metrics to track optimization impact

#### Metrics to Track

1. **Per-phase latency**:
   - Fast-path check: <1ms
   - Interpretation: 300-600ms
   - Decomposition: 400-800ms
   - Routing: 1-5ms
   - Execution: 500-1500ms
   - Synthesis: 400-700ms
   - Evaluation: 300-500ms

2. **Cache metrics** (already implemented):
   - Hit rate
   - Miss rate
   - Average lookup time

3. **Fast-path metrics**:
   - Match rate
   - Pattern distribution
   - Latency savings

4. **Speculation metrics**:
   - Speculation hit rate (used)
   - Speculation waste rate (cancelled)
   - Latency savings

#### Implementation

```python
# asdrp/agents/router/performance.py

class PerformanceTracker:
    """Track SmartRouter performance metrics."""

    def __init__(self):
        self.metrics = defaultdict(list)

    def record_phase(self, phase: str, duration_ms: float):
        """Record phase execution time."""
        self.metrics[f"{phase}_duration"].append(duration_ms)

    def record_fast_path(self, matched: bool, pattern: Optional[str] = None):
        """Record fast-path attempt."""
        self.metrics["fast_path_attempts"].append(1)
        if matched:
            self.metrics["fast_path_hits"].append(1)
            self.metrics[f"fast_path_pattern_{pattern}"].append(1)

    def record_speculation(self, started: bool, used: bool):
        """Record speculation attempt."""
        if started:
            self.metrics["speculation_attempts"].append(1)
            if used:
                self.metrics["speculation_hits"].append(1)
            else:
                self.metrics["speculation_waste"].append(1)

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            "total_queries": len(self.metrics.get("interpretation_duration", [])),
            "fast_path_rate": self._calculate_rate("fast_path_hits", "fast_path_attempts"),
            "speculation_accuracy": self._calculate_rate("speculation_hits", "speculation_attempts"),
            "avg_latency": self._calculate_avg_latency(),
            "p50_latency": self._calculate_percentile(50),
            "p95_latency": self._calculate_percentile(95),
            "p99_latency": self._calculate_percentile(99),
        }
```

**Estimated Implementation**: 3-4 hours

---

## Implementation Roadmap

### Phase 3B: Fast-Path Integration (2-3 hours)

**Priority**: HIGHEST
**Benefit**: 1.3-2.5s for 20-30% of queries
**Risk**: LOW

**Steps**:
1. Add `FastPathRouter` to `SmartRouter.__init__` (15 min)
2. Update `route_query()` with fast-path check (30 min)
3. Add fast-path metrics tracking (30 min)
4. Write integration tests (45 min)
5. Test end-to-end with frontend (30 min)
6. Fix any issues (30 min)

**Deliverables**:
- Fast-path integrated into SmartRouter
- 5-10 integration tests
- Updated metrics tracking
- Documentation

---

### Phase 2B: Parallel Speculation (4-5 hours)

**Priority**: HIGH
**Benefit**: 300-600ms for 30% of queries
**Risk**: MEDIUM (potential wasted calls)

**Steps**:
1. Implement `_predict_complexity()` heuristic (30 min)
2. Add `decompose_speculative()` method (30 min)
3. Update `route_query()` with speculation logic (1 hour)
4. Add speculation metrics (30 min)
5. Write tests for speculation (1 hour)
6. Tune heuristic thresholds (1 hour)
7. Test and fix issues (1 hour)

**Deliverables**:
- Speculation implemented with heuristic
- 10-15 tests
- Metrics dashboard
- Tuned thresholds
- Documentation

---

### Phase 4: Performance Instrumentation (3-4 hours)

**Priority**: MEDIUM
**Benefit**: Visibility into optimizations
**Risk**: LOW

**Steps**:
1. Implement `PerformanceTracker` class (1 hour)
2. Integrate with SmartRouter pipeline (1 hour)
3. Add metrics endpoint (30 min)
4. Create performance dashboard (1 hour)
5. Write tests (30 min)

**Deliverables**:
- Complete performance tracking
- Metrics API endpoint
- Dashboard for visualization
- Tests

---

### Phase 5: Benchmarking & Validation (4-5 hours)

**Priority**: HIGH (after implementation)
**Benefit**: Validate optimization impact
**Risk**: LOW

**Steps**:
1. Create benchmark suite (1 hour)
2. Baseline performance tests (1 hour)
3. Run optimized tests (1 hour)
4. Compare results (1 hour)
5. Document findings (1 hour)

**Deliverables**:
- Comprehensive benchmark suite
- Performance comparison report
- Validation of optimization goals

---

## Expected Outcomes

### Latency Reduction by Query Type

| Query Type | Baseline | After Fast-Path | After Speculation | Total Reduction |
|-----------|----------|-----------------|-------------------|-----------------|
| Chitchat (20%) | 3.0s | **0.5s** | 0.5s | **-2.5s (83%)** |
| Simple (50%) | 2.0s | 2.0s | 2.0s | **0s (0%)** |
| Complex (30%) | 4.0s | 4.0s | **3.5s** | **-0.5s (12%)** |
| **Weighted Avg** | **2.7s** | **2.2s** | **2.1s** | **-0.6s (22%)** |

### API Cost Impact

| Optimization | LLM Calls Added | Cost Impact |
|--------------|----------------|-------------|
| Fast-Path | 0 (saves calls) | **-20% for chitchat** |
| Speculation | +10-15% waste | **+5% overall** |
| **Net Impact** | - | **-15% overall** |

### Summary

- **Latency**: 22% reduction (2.7s → 2.1s)
- **Fast-path queries**: 83% faster (3.0s → 0.5s)
- **Complex queries**: 12% faster (4.0s → 3.5s)
- **API costs**: 15% reduction overall

---

## Testing Strategy

### Unit Tests
- Fast-path integration (10 tests)
- Speculation logic (15 tests)
- Performance tracking (10 tests)
- **Total**: 35 new tests

### Integration Tests
- End-to-end fast-path flow (5 tests)
- End-to-end speculation flow (5 tests)
- Metrics collection (5 tests)
- **Total**: 15 new tests

### Performance Tests
- Baseline benchmarks (10 scenarios)
- Optimized benchmarks (10 scenarios)
- Comparison analysis (5 tests)
- **Total**: 25 benchmark tests

### Total Test Coverage
- **75 new tests**
- **Expected pass rate**: 100%

---

## Documentation Updates

### New Documentation
1. `SMARTROUTER_FAST_PATH_INTEGRATION.md` - Fast-path integration guide
2. `SMARTROUTER_SPECULATION_DESIGN.md` - Speculation architecture
3. `SMARTROUTER_PERFORMANCE_METRICS.md` - Metrics and benchmarks
4. `SMARTROUTER_OPTIMIZATION_RESULTS.md` - Final results and analysis

### Updated Documentation
1. `SMARTROUTER.md` - Add optimization sections
2. `SMARTROUTER_FRONTEND_INTEGRATION.md` - Update with metrics
3. `COMPLETE_TUTORIAL.md` - Add performance tips

---

## Risk Assessment

### Technical Risks

1. **Speculation Waste** (MEDIUM)
   - Risk: Too many wasted LLM calls
   - Mitigation: Conservative heuristic (10-15% waste acceptable)
   - Fallback: Disable speculation if waste >20%

2. **Fast-Path False Negatives** (LOW)
   - Risk: Missing complex queries that look like chitchat
   - Mitigation: Conservative patterns, fallthrough to LLM
   - Fallback: Disable specific patterns if issues arise

3. **Performance Regression** (LOW)
   - Risk: Optimizations actually slow down pipeline
   - Mitigation: Comprehensive benchmarks before/after
   - Fallback: Feature flags to disable optimizations

### Operational Risks

1. **Increased API Costs** (LOW-MEDIUM)
   - Risk: Speculation increases token usage
   - Mitigation: Monitor costs, tune thresholds
   - Fallback: Disable speculation for high-cost users

2. **Debugging Complexity** (LOW)
   - Risk: Parallel execution harder to debug
   - Mitigation: Comprehensive tracing and logging
   - Fallback: Metrics dashboard shows exactly what's happening

---

## Implementation Timeline

**Total Estimated Time**: 13-17 hours

| Phase | Duration | Priority |
|-------|----------|----------|
| Phase 3B: Fast-Path Integration | 2-3 hours | HIGHEST |
| Phase 2B: Speculation | 4-5 hours | HIGH |
| Phase 4: Instrumentation | 3-4 hours | MEDIUM |
| Phase 5: Benchmarking | 4-5 hours | HIGH |

**Recommended Sequence**:
1. Fast-Path Integration (immediate value, low risk)
2. Performance Instrumentation (measure baseline)
3. Speculation (complex, needs careful tuning)
4. Benchmarking & Validation (prove results)

---

## Success Criteria

✅ **Phase 3B Complete When**:
- Fast-path integrated into SmartRouter
- Chitchat queries bypass LLM
- 10+ integration tests passing
- Latency reduced by 2+ seconds for chitchat

✅ **Phase 2B Complete When**:
- Speculation implemented with heuristic
- Complex queries save 300-500ms
- Waste rate <15%
- 15+ tests passing

✅ **Phase 4 Complete When**:
- All metrics tracked and logged
- Dashboard shows real-time performance
- Metrics API endpoint available

✅ **Phase 5 Complete When**:
- Benchmarks show 20%+ latency reduction
- API costs reduced by 10%+
- All optimizations validated
- Documentation complete

---

## Next Steps

**Immediate Action**: Start with Phase 3B (Fast-Path Integration)

**Command to run**:
```bash
# 1. Implement fast-path integration
# 2. Write tests
# 3. Test end-to-end
# 4. Update documentation
```

**Expected Timeline**: 2-3 hours
**Expected Benefit**: 2.5s reduction for 20% of queries
