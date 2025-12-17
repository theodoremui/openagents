"""
Trace Capture Service for SmartRouter

Captures execution traces during SmartRouter processing for visualization.
Follows SOLID principles with clear separation of concerns.

Design Principles:
-----------------
- Single Responsibility: Only responsible for capturing and managing traces
- Dependency Injection: No hard dependencies on specific implementations
- Open/Closed: Easy to extend with new trace types
- Interface Segregation: Clean, focused interface
- Dependency Inversion: Depends on abstractions

Usage:
------
>>> capture = TraceCapture()
>>> with capture.phase("interpretation"):
...     # do interpretation work
...     capture.record_data({"complexity": "SIMPLE"})
>>> traces = capture.get_traces()
"""

import time
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class PhaseTrace:
    """
    Trace data for a single execution phase.

    Attributes:
        phase: Name of the phase (e.g., "interpretation", "routing")
        start_time: When the phase started (seconds since epoch)
        end_time: When the phase ended (seconds since epoch)
        duration: Phase duration in seconds
        data: Phase-specific data captured during execution
        success: Whether the phase completed successfully
        error: Error message if phase failed
    """
    phase: str
    start_time: float
    end_time: Optional[float] = None
    duration: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "phase": self.phase,
            "duration": round(self.duration, 3),
            "data": self.data,
            "success": self.success,
            "error": self.error,
        }


class TraceCapture:
    """
    Service for capturing execution traces during SmartRouter processing.

    This class manages trace collection throughout the SmartRouter pipeline,
    providing a clean API for recording phase execution details.

    The service follows the Context Manager pattern for automatic timing
    and the Builder pattern for constructing trace data.

    Thread-Safety: Not thread-safe by design (each request gets its own instance)
    """

    def __init__(self):
        """Initialize trace capture service."""
        self._traces: List[PhaseTrace] = []
        self._current_phase: Optional[PhaseTrace] = None
        self._start_time: float = time.time()
        self._agents_used: List[str] = []

    @contextmanager
    def phase(self, phase_name: str):
        """
        Context manager for capturing a phase execution.

        Usage:
            with trace_capture.phase("interpretation"):
                # Phase work here
                trace_capture.record_data({"complexity": "SIMPLE"})

        Args:
            phase_name: Name of the phase being executed

        Yields:
            The current PhaseTrace being recorded
        """
        phase_trace = PhaseTrace(
            phase=phase_name,
            start_time=time.time()
        )
        self._current_phase = phase_trace
        self._traces.append(phase_trace)

        try:
            yield phase_trace
        except Exception as e:
            phase_trace.success = False
            phase_trace.error = str(e)
            logger.error(f"Phase '{phase_name}' failed: {e}", exc_info=True)
            raise
        finally:
            phase_trace.end_time = time.time()
            phase_trace.duration = phase_trace.end_time - phase_trace.start_time
            self._current_phase = None
            logger.debug(
                f"Phase '{phase_name}' completed in {phase_trace.duration:.3f}s"
            )

    def record_data(self, data: Dict[str, Any]) -> None:
        """
        Record data for the current phase.

        Args:
            data: Dictionary of data to record

        Raises:
            RuntimeError: If not currently in a phase context
        """
        if not self._current_phase:
            raise RuntimeError(
                "Cannot record data outside of phase context. "
                "Use 'with trace_capture.phase(...)' first."
            )

        self._current_phase.data.update(data)

    def record_agent_used(self, agent_id: str) -> None:
        """
        Record that an agent was used in this execution.

        Args:
            agent_id: ID of the agent that was used
        """
        if agent_id not in self._agents_used:
            self._agents_used.append(agent_id)
            logger.debug(f"Recorded agent usage: {agent_id}")

    def record_agents_used(self, agent_ids: List[str]) -> None:
        """
        Record multiple agents used in this execution.

        Args:
            agent_ids: List of agent IDs that were used
        """
        for agent_id in agent_ids:
            self.record_agent_used(agent_id)

    def get_traces(self) -> List[Dict[str, Any]]:
        """
        Get all captured traces as dictionaries.

        Returns:
            List of trace dictionaries ready for JSON serialization
        """
        return [trace.to_dict() for trace in self._traces]

    def get_agents_used(self) -> List[str]:
        """
        Get list of all agents used during execution.

        Returns:
            List of agent IDs
        """
        return self._agents_used.copy()

    def get_total_time(self) -> float:
        """
        Get total execution time since capture started.

        Returns:
            Total time in seconds
        """
        return time.time() - self._start_time

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all traces and execution.

        Returns:
            Dictionary with summary information including:
            - total_time: Total execution time
            - phase_count: Number of phases executed
            - agents_used: List of agents used
            - phases: List of all phase traces
            - success: Whether all phases succeeded
        """
        return {
            "total_time": round(self.get_total_time(), 3),
            "phase_count": len(self._traces),
            "agents_used": self.get_agents_used(),
            "phases": self.get_traces(),
            "success": all(trace.success for trace in self._traces),
        }

    def has_failures(self) -> bool:
        """
        Check if any phase failed.

        Returns:
            True if any phase failed, False otherwise
        """
        return any(not trace.success for trace in self._traces)

    def clear(self) -> None:
        """Clear all captured traces and reset state."""
        self._traces.clear()
        self._agents_used.clear()
        self._current_phase = None
        self._start_time = time.time()
        logger.debug("Trace capture cleared")


@dataclass
class SmartRouterExecutionResult:
    """
    Complete result from SmartRouter execution including answer and traces.

    This is the primary return type from SmartRouter.route_query() when
    trace capture is enabled.

    Attributes:
        answer: Final answer string (may be fallback message)
        traces: List of execution phase traces
        total_time: Total execution time in seconds
        final_decision: Decision type (direct, synthesized, fallback, chitchat, error)
        agents_used: List of agent IDs used during execution
        success: Whether execution succeeded
        original_answer: Original answer before fallback (only set if final_decision == "fallback")
    """
    answer: str
    traces: List[Dict[str, Any]]
    total_time: float
    final_decision: str
    agents_used: List[str]
    success: bool = True
    original_answer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "answer": self.answer,
            "traces": self.traces,
            "total_time": round(self.total_time, 3),
            "final_decision": self.final_decision,
            "agents_used": self.agents_used,
            "success": self.success,
        }
        if self.original_answer is not None:
            result["original_answer"] = self.original_answer
        return result

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get metadata portion (everything except answer)."""
        result = self.to_dict()
        del result["answer"]
        return result
