"""
Tests for SmartRouter Trace Capture System

This module tests the TraceCapture service and SmartRouterExecutionResult
following SOLID principles and best practices.

Test Coverage:
- TraceCapture context manager
- Phase timing and data recording
- Agent tracking
- Error handling
- Summary generation
- SmartRouterExecutionResult dataclass
"""

import pytest
import time
from typing import Dict, Any
from asdrp.orchestration.smartrouter.trace_capture import (
    TraceCapture,
    PhaseTrace,
    SmartRouterExecutionResult,
)


class TestPhaseTrace:
    """Test PhaseTrace dataclass."""

    def test_phase_trace_creation(self):
        """Test creating a PhaseTrace with all fields."""
        trace = PhaseTrace(
            phase="interpretation",
            start_time=1000.0,
            end_time=1001.5,
            duration=1.5,
            data={"complexity": "SIMPLE"},
            success=True,
            error=None,
        )

        assert trace.phase == "interpretation"
        assert trace.start_time == 1000.0
        assert trace.end_time == 1001.5
        assert trace.duration == 1.5
        assert trace.data == {"complexity": "SIMPLE"}
        assert trace.success is True
        assert trace.error is None

    def test_phase_trace_to_dict(self):
        """Test PhaseTrace.to_dict() conversion."""
        trace = PhaseTrace(
            phase="routing",
            start_time=1000.0,
            end_time=1001.234,
            duration=1.234,
            data={"agent": "one"},
            success=True,
        )

        result = trace.to_dict()

        assert result == {
            "phase": "routing",
            "duration": 1.234,  # Rounded to 3 decimals
            "data": {"agent": "one"},
            "success": True,
            "error": None,
        }

    def test_phase_trace_with_error(self):
        """Test PhaseTrace with error state."""
        trace = PhaseTrace(
            phase="execution",
            start_time=1000.0,
            end_time=1001.0,
            duration=1.0,
            success=False,
            error="Agent not found",
        )

        result = trace.to_dict()

        assert result["success"] is False
        assert result["error"] == "Agent not found"


class TestTraceCaptureBasics:
    """Test basic TraceCapture functionality."""

    def test_trace_capture_initialization(self):
        """Test TraceCapture initializes with empty state."""
        capture = TraceCapture()

        assert len(capture._traces) == 0
        assert capture._current_phase is None
        assert len(capture._agents_used) == 0
        assert capture._start_time > 0

    def test_phase_context_manager(self):
        """Test phase() context manager records timing."""
        capture = TraceCapture()

        with capture.phase("test_phase"):
            time.sleep(0.01)  # Small delay for timing

        assert len(capture._traces) == 1
        trace = capture._traces[0]
        assert trace.phase == "test_phase"
        assert trace.duration >= 0.01  # At least 10ms
        assert trace.success is True
        assert trace.error is None

    def test_record_data_in_phase(self):
        """Test recording data during phase execution."""
        capture = TraceCapture()

        with capture.phase("interpretation"):
            capture.record_data({"complexity": "SIMPLE"})
            capture.record_data({"domains": ["search"]})

        trace = capture._traces[0]
        assert trace.data == {
            "complexity": "SIMPLE",
            "domains": ["search"],
        }

    def test_record_data_outside_phase_raises_error(self):
        """Test recording data outside phase raises RuntimeError."""
        capture = TraceCapture()

        with pytest.raises(RuntimeError, match="outside of phase context"):
            capture.record_data({"test": "data"})

    def test_multiple_phases(self):
        """Test multiple sequential phases."""
        capture = TraceCapture()

        with capture.phase("interpretation"):
            capture.record_data({"complexity": "SIMPLE"})

        with capture.phase("routing"):
            capture.record_data({"agent": "one"})

        with capture.phase("execution"):
            capture.record_data({"success": True})

        assert len(capture._traces) == 3
        assert capture._traces[0].phase == "interpretation"
        assert capture._traces[1].phase == "routing"
        assert capture._traces[2].phase == "execution"


class TestTraceCaptureErrorHandling:
    """Test error handling in TraceCapture."""

    def test_phase_with_exception(self):
        """Test phase() context manager captures exceptions."""
        capture = TraceCapture()

        with pytest.raises(ValueError, match="Test error"):
            with capture.phase("failing_phase"):
                capture.record_data({"start": "ok"})
                raise ValueError("Test error")

        assert len(capture._traces) == 1
        trace = capture._traces[0]
        assert trace.phase == "failing_phase"
        assert trace.success is False
        assert trace.error == "Test error"
        assert trace.data == {"start": "ok"}  # Data before error preserved

    def test_multiple_phases_with_error(self):
        """Test that error in one phase doesn't affect others."""
        capture = TraceCapture()

        # Successful phase
        with capture.phase("phase1"):
            capture.record_data({"result": "success"})

        # Failing phase
        try:
            with capture.phase("phase2"):
                raise RuntimeError("Phase 2 failed")
        except RuntimeError:
            pass

        # Another successful phase
        with capture.phase("phase3"):
            capture.record_data({"result": "success"})

        assert len(capture._traces) == 3
        assert capture._traces[0].success is True
        assert capture._traces[1].success is False
        assert capture._traces[2].success is True


class TestTraceCaptureAgentTracking:
    """Test agent tracking functionality."""

    def test_record_agent_used(self):
        """Test recording a single agent."""
        capture = TraceCapture()

        capture.record_agent_used("one")

        assert capture._agents_used == ["one"]

    def test_record_multiple_agents(self):
        """Test recording multiple agents."""
        capture = TraceCapture()

        capture.record_agent_used("one")
        capture.record_agent_used("geo")
        capture.record_agent_used("finance")

        assert capture._agents_used == ["one", "geo", "finance"]

    def test_record_duplicate_agent(self):
        """Test that duplicate agents are not added."""
        capture = TraceCapture()

        capture.record_agent_used("one")
        capture.record_agent_used("one")
        capture.record_agent_used("geo")
        capture.record_agent_used("one")

        assert capture._agents_used == ["one", "geo"]

    def test_record_agents_used(self):
        """Test recording multiple agents at once."""
        capture = TraceCapture()

        capture.record_agents_used(["one", "geo", "finance"])

        assert capture._agents_used == ["one", "geo", "finance"]

    def test_record_agents_used_with_duplicates(self):
        """Test recording agents with duplicates."""
        capture = TraceCapture()

        capture.record_agent_used("one")
        capture.record_agents_used(["one", "geo", "one", "finance"])

        assert capture._agents_used == ["one", "geo", "finance"]


class TestTraceCaptureQueries:
    """Test querying trace data."""

    def test_get_traces(self):
        """Test get_traces() returns list of dicts."""
        capture = TraceCapture()

        with capture.phase("phase1"):
            capture.record_data({"key": "value1"})

        with capture.phase("phase2"):
            capture.record_data({"key": "value2"})

        traces = capture.get_traces()

        assert len(traces) == 2
        assert all(isinstance(t, dict) for t in traces)
        assert traces[0]["phase"] == "phase1"
        assert traces[1]["phase"] == "phase2"

    def test_get_agents_used(self):
        """Test get_agents_used() returns copy of list."""
        capture = TraceCapture()

        capture.record_agent_used("one")
        capture.record_agent_used("geo")

        agents = capture.get_agents_used()

        # Modify returned list
        agents.append("finance")

        # Original should be unchanged
        assert capture._agents_used == ["one", "geo"]

    def test_get_total_time(self):
        """Test get_total_time() returns time since start."""
        capture = TraceCapture()

        time.sleep(0.01)  # Small delay

        total_time = capture.get_total_time()

        assert total_time >= 0.01  # At least 10ms
        assert total_time < 1.0  # Less than 1 second

    def test_get_summary(self):
        """Test get_summary() returns complete summary."""
        capture = TraceCapture()

        with capture.phase("interpretation"):
            capture.record_data({"complexity": "SIMPLE"})

        with capture.phase("routing"):
            capture.record_data({"agent": "one"})

        capture.record_agent_used("one")

        summary = capture.get_summary()

        assert "total_time" in summary
        assert summary["phase_count"] == 2
        assert summary["agents_used"] == ["one"]
        assert len(summary["phases"]) == 2
        assert summary["success"] is True

    def test_has_failures_false(self):
        """Test has_failures() returns False when all phases succeed."""
        capture = TraceCapture()

        with capture.phase("phase1"):
            pass

        with capture.phase("phase2"):
            pass

        assert capture.has_failures() is False

    def test_has_failures_true(self):
        """Test has_failures() returns True when any phase fails."""
        capture = TraceCapture()

        with capture.phase("phase1"):
            pass

        try:
            with capture.phase("phase2"):
                raise ValueError("Error")
        except ValueError:
            pass

        assert capture.has_failures() is True


class TestTraceCaptureClearing:
    """Test clearing trace data."""

    def test_clear(self):
        """Test clear() resets all state."""
        capture = TraceCapture()

        # Add some data
        with capture.phase("test"):
            capture.record_data({"key": "value"})

        capture.record_agent_used("one")

        # Clear
        capture.clear()

        # Verify cleared
        assert len(capture._traces) == 0
        assert len(capture._agents_used) == 0
        assert capture._current_phase is None

    def test_clear_and_reuse(self):
        """Test that TraceCapture can be reused after clear()."""
        capture = TraceCapture()

        # First use
        with capture.phase("phase1"):
            capture.record_data({"run": 1})

        capture.record_agent_used("one")

        # Clear
        capture.clear()

        # Second use
        with capture.phase("phase2"):
            capture.record_data({"run": 2})

        capture.record_agent_used("geo")

        # Verify only second use data
        assert len(capture._traces) == 1
        assert capture._traces[0].phase == "phase2"
        assert capture._agents_used == ["geo"]


class TestSmartRouterExecutionResult:
    """Test SmartRouterExecutionResult dataclass."""

    def test_execution_result_creation(self):
        """Test creating SmartRouterExecutionResult."""
        result = SmartRouterExecutionResult(
            answer="Test answer",
            traces=[
                {"phase": "interpretation", "duration": 0.5, "data": {}}
            ],
            total_time=1.5,
            final_decision="direct",
            agents_used=["one"],
            success=True,
        )

        assert result.answer == "Test answer"
        assert len(result.traces) == 1
        assert result.total_time == 1.5
        assert result.final_decision == "direct"
        assert result.agents_used == ["one"]
        assert result.success is True

    def test_execution_result_to_dict(self):
        """Test to_dict() conversion."""
        result = SmartRouterExecutionResult(
            answer="Test answer",
            traces=[{"phase": "test", "duration": 0.5, "data": {}}],
            total_time=1.234,
            final_decision="synthesized",
            agents_used=["one", "geo"],
            success=True,
        )

        data = result.to_dict()

        assert data["answer"] == "Test answer"
        assert data["total_time"] == 1.234  # Rounded to 3 decimals
        assert data["final_decision"] == "synthesized"
        assert data["agents_used"] == ["one", "geo"]
        assert data["success"] is True

    def test_execution_result_metadata_property(self):
        """Test metadata property excludes answer."""
        result = SmartRouterExecutionResult(
            answer="Test answer",
            traces=[],
            total_time=1.0,
            final_decision="direct",
            agents_used=["one"],
        )

        metadata = result.metadata

        assert "answer" not in metadata
        assert "traces" in metadata
        assert "total_time" in metadata
        assert "final_decision" in metadata
        assert "agents_used" in metadata

    def test_execution_result_with_error(self):
        """Test SmartRouterExecutionResult with error state."""
        result = SmartRouterExecutionResult(
            answer="Fallback message",
            traces=[
                {"phase": "interpretation", "duration": 0.5, "data": {}, "success": False, "error": "Test error"}
            ],
            total_time=0.5,
            final_decision="error",
            agents_used=[],
            success=False,
        )

        assert result.success is False
        assert result.final_decision == "error"
        assert len(result.agents_used) == 0


class TestTraceCaptureIntegration:
    """Integration tests for TraceCapture with realistic scenarios."""

    def test_simple_query_flow(self):
        """Test trace capture for simple query flow."""
        capture = TraceCapture()

        # Interpretation
        with capture.phase("interpretation"):
            capture.record_data({
                "intent": {
                    "complexity": "SIMPLE",
                    "domains": ["search"],
                }
            })

        # Routing
        with capture.phase("routing"):
            capture.record_data({
                "pattern": "SIMPLE",
                "agent": "one",
                "domains": ["search"],
            })

        # Execution
        with capture.phase("execution"):
            capture.record_agent_used("one")
            capture.record_data({
                "agents": ["one"],
                "success": True,
            })

        # Evaluation (skipped for simple)
        # Final result
        result = SmartRouterExecutionResult(
            answer="Test answer",
            traces=capture.get_traces(),
            total_time=capture.get_total_time(),
            final_decision="direct",
            agents_used=capture.get_agents_used(),
            success=not capture.has_failures(),
        )

        assert len(result.traces) == 3
        assert result.final_decision == "direct"
        assert result.agents_used == ["one"]
        assert result.success is True

    def test_complex_query_flow(self):
        """Test trace capture for complex query flow."""
        capture = TraceCapture()

        # Interpretation
        with capture.phase("interpretation"):
            capture.record_data({
                "intent": {
                    "complexity": "COMPLEX",
                    "domains": ["search", "finance"],
                }
            })

        # Decomposition
        with capture.phase("decomposition"):
            capture.record_data({
                "subquery_count": 2,
                "subqueries": [
                    {"id": "sq1", "text": "weather", "capability": "search"},
                    {"id": "sq2", "text": "stock", "capability": "finance"},
                ],
            })

        # Routing
        with capture.phase("routing"):
            capture.record_data({
                "routing": {"sq1": "one", "sq2": "finance"},
                "agents_selected": ["one", "finance"],
            })
            capture.record_agents_used(["one", "finance"])

        # Execution
        with capture.phase("execution"):
            capture.record_data({
                "response_count": 2,
                "agents": ["one", "finance"],
                "success": True,
            })

        # Synthesis
        with capture.phase("synthesis"):
            capture.record_data({
                "synthesized_from": 2,
                "confidence": 0.95,
                "sources": ["one", "finance"],
            })

        # Evaluation
        with capture.phase("evaluation"):
            capture.record_data({
                "passed": True,
                "issues": [],
            })

        # Final result
        result = SmartRouterExecutionResult(
            answer="Synthesized answer",
            traces=capture.get_traces(),
            total_time=capture.get_total_time(),
            final_decision="synthesized",
            agents_used=capture.get_agents_used(),
            success=not capture.has_failures(),
        )

        assert len(result.traces) == 6
        assert result.final_decision == "synthesized"
        assert set(result.agents_used) == {"one", "finance"}
        assert result.success is True
