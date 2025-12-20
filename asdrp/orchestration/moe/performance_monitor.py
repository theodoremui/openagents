"""
Performance Monitor for MoE Orchestrator.

Provides performance metrics, monitoring, and optimization features for the MoE system.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from loguru import logger


@dataclass
class PerformanceMetrics:
    """Performance metrics for MoE operations."""
    
    # Timing metrics (milliseconds)
    selection_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    mixing_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    # Expert metrics
    experts_selected: int = 0
    experts_executed: int = 0
    experts_successful: int = 0
    experts_failed: int = 0
    
    # Cache metrics
    cache_hit: bool = False
    cache_miss: bool = False
    
    # Resource metrics
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    
    # Quality metrics
    quality_score: float = 0.0
    confidence_score: float = 0.0
    
    # Error metrics
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ExpertPerformanceStats:
    """Performance statistics for individual experts."""
    
    expert_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    
    # Timing statistics
    avg_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    
    # Recent performance (sliding window)
    recent_latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_success_rate: float = 0.0
    
    # Error tracking
    common_errors: Dict[str, int] = field(default_factory=dict)
    
    def update(self, latency_ms: float, success: bool, error: Optional[str] = None):
        """Update performance statistics with new execution data."""
        self.total_executions += 1
        
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
            if error:
                self.common_errors[error] = self.common_errors.get(error, 0) + 1
        
        # Update timing statistics
        self.recent_latencies.append(latency_ms)
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        
        # Calculate average latency
        if self.recent_latencies:
            self.avg_latency_ms = sum(self.recent_latencies) / len(self.recent_latencies)
        
        # Calculate recent success rate
        recent_window = list(self.recent_latencies)[-20:]  # Last 20 executions
        if recent_window:
            recent_successes = sum(1 for i in range(len(recent_window)) 
                                 if i < self.successful_executions)
            self.recent_success_rate = recent_successes / len(recent_window)
    
    @property
    def success_rate(self) -> float:
        """Overall success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    @property
    def failure_rate(self) -> float:
        """Overall failure rate."""
        return 1.0 - self.success_rate


class PerformanceMonitor:
    """
    Performance monitoring and optimization for MoE orchestrator.
    
    Features:
    - Real-time performance metrics collection
    - Expert performance tracking
    - Circuit breaker pattern for failing experts
    - Performance-based expert selection optimization
    - Resource usage monitoring
    """
    
    def __init__(self, circuit_breaker_threshold: float = 0.8, window_size: int = 100):
        """
        Initialize performance monitor.
        
        Args:
            circuit_breaker_threshold: Failure rate threshold for circuit breaker (0.0-1.0)
            window_size: Size of sliding window for recent performance tracking
        """
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.window_size = window_size
        
        # Performance tracking
        self.expert_stats: Dict[str, ExpertPerformanceStats] = {}
        self.recent_metrics: deque = deque(maxlen=window_size)
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, bool] = {}  # expert_id -> is_open
        self.circuit_breaker_reset_time: Dict[str, float] = {}
        
        # Performance optimization
        self.expert_performance_scores: Dict[str, float] = {}
        
        logger.info(f"[Performance Monitor] Initialized with circuit breaker threshold: {circuit_breaker_threshold}")
    
    def start_request(self) -> Dict[str, Any]:
        """Start tracking a new request."""
        return {
            "start_time": time.time(),
            "selection_start": None,
            "execution_start": None,
            "mixing_start": None
        }
    
    def record_selection_start(self, context: Dict[str, Any]):
        """Record start of expert selection phase."""
        context["selection_start"] = time.time()
    
    def record_selection_end(self, context: Dict[str, Any], selected_experts: List[str]):
        """Record end of expert selection phase."""
        if context.get("selection_start"):
            selection_time = (time.time() - context["selection_start"]) * 1000
            context["selection_time_ms"] = selection_time
            logger.debug(f"[Performance] Expert selection took {selection_time:.1f}ms for {len(selected_experts)} experts")
    
    def record_execution_start(self, context: Dict[str, Any]):
        """Record start of expert execution phase."""
        context["execution_start"] = time.time()
    
    def record_execution_end(self, context: Dict[str, Any], expert_results: List[Any]):
        """Record end of expert execution phase."""
        if context.get("execution_start"):
            execution_time = (time.time() - context["execution_start"]) * 1000
            context["execution_time_ms"] = execution_time
            
            # Update expert statistics
            for result in expert_results:
                if hasattr(result, 'expert_id'):
                    expert_id = result.expert_id
                    latency_ms = getattr(result, 'latency_ms', 0.0)
                    success = getattr(result, 'success', False)
                    error = getattr(result, 'error', None)
                    
                    self.update_expert_stats(expert_id, latency_ms, success, error)
            
            successful_experts = sum(1 for r in expert_results if getattr(r, 'success', False))
            logger.debug(f"[Performance] Expert execution took {execution_time:.1f}ms, {successful_experts}/{len(expert_results)} succeeded")
    
    def record_mixing_start(self, context: Dict[str, Any]):
        """Record start of result mixing phase."""
        context["mixing_start"] = time.time()
    
    def record_mixing_end(self, context: Dict[str, Any], mixed_result: Any):
        """Record end of result mixing phase."""
        if context.get("mixing_start"):
            mixing_time = (time.time() - context["mixing_start"]) * 1000
            context["mixing_time_ms"] = mixing_time
            
            quality_score = getattr(mixed_result, 'quality_score', 0.0) if mixed_result else 0.0
            logger.debug(f"[Performance] Result mixing took {mixing_time:.1f}ms, quality: {quality_score:.2f}")
    
    def finish_request(self, context: Dict[str, Any], cache_hit: bool = False) -> PerformanceMetrics:
        """Finish tracking request and return performance metrics."""
        total_time = (time.time() - context["start_time"]) * 1000
        
        metrics = PerformanceMetrics(
            selection_time_ms=context.get("selection_time_ms", 0.0),
            execution_time_ms=context.get("execution_time_ms", 0.0),
            mixing_time_ms=context.get("mixing_time_ms", 0.0),
            total_time_ms=total_time,
            cache_hit=cache_hit,
            cache_miss=not cache_hit
        )
        
        # Add to recent metrics
        self.recent_metrics.append(metrics)
        
        # Log performance summary
        if total_time > 5000:  # Log slow requests (>5s)
            logger.warning(f"[Performance] Slow request: {total_time:.1f}ms total")
        else:
            logger.debug(f"[Performance] Request completed in {total_time:.1f}ms")
        
        return metrics
    
    def update_expert_stats(self, expert_id: str, latency_ms: float, success: bool, error: Optional[str] = None):
        """Update performance statistics for an expert."""
        if expert_id not in self.expert_stats:
            self.expert_stats[expert_id] = ExpertPerformanceStats(expert_id=expert_id)
        
        stats = self.expert_stats[expert_id]
        stats.update(latency_ms, success, error)
        
        # Update performance score (higher is better)
        # Combines success rate and speed (inverse of latency)
        if stats.total_executions >= 5:  # Need minimum data
            speed_score = max(0.1, 1000 / max(stats.avg_latency_ms, 100))  # Normalize to 0-10 range
            success_score = stats.recent_success_rate * 10  # 0-10 range
            self.expert_performance_scores[expert_id] = (speed_score + success_score) / 2
        
        # Check circuit breaker
        self.check_circuit_breaker(expert_id, stats)
    
    def check_circuit_breaker(self, expert_id: str, stats: ExpertPerformanceStats):
        """Check and update circuit breaker status for an expert."""
        # Only activate circuit breaker if we have enough data
        if stats.total_executions < 10:
            return
        
        current_time = time.time()
        
        # Check if circuit breaker should open
        if stats.recent_success_rate < (1.0 - self.circuit_breaker_threshold):
            if not self.circuit_breakers.get(expert_id, False):
                logger.warning(f"[Performance] Circuit breaker OPENED for {expert_id} (success rate: {stats.recent_success_rate:.2f})")
                self.circuit_breakers[expert_id] = True
                self.circuit_breaker_reset_time[expert_id] = current_time + 300  # 5 minute timeout
        
        # Check if circuit breaker should close (reset)
        elif self.circuit_breakers.get(expert_id, False):
            if current_time > self.circuit_breaker_reset_time.get(expert_id, 0):
                logger.info(f"[Performance] Circuit breaker CLOSED for {expert_id} (success rate recovered: {stats.recent_success_rate:.2f})")
                self.circuit_breakers[expert_id] = False
    
    def is_expert_available(self, expert_id: str) -> bool:
        """Check if expert is available (circuit breaker not open)."""
        return not self.circuit_breakers.get(expert_id, False)
    
    def get_expert_performance_score(self, expert_id: str) -> float:
        """Get performance score for expert (higher is better)."""
        return self.expert_performance_scores.get(expert_id, 5.0)  # Default neutral score
    
    def optimize_expert_selection(self, candidate_experts: List[str], k: int) -> List[str]:
        """
        Optimize expert selection based on performance metrics.
        
        Args:
            candidate_experts: List of candidate expert IDs
            k: Number of experts to select
            
        Returns:
            Optimized list of expert IDs
        """
        # Filter out experts with open circuit breakers
        available_experts = [e for e in candidate_experts if self.is_expert_available(e)]
        
        if len(available_experts) < k:
            logger.warning(f"[Performance] Only {len(available_experts)} experts available, requested {k}")
            return available_experts
        
        # Sort by performance score (descending)
        scored_experts = [(e, self.get_expert_performance_score(e)) for e in available_experts]
        scored_experts.sort(key=lambda x: x[1], reverse=True)
        
        selected = [e for e, score in scored_experts[:k]]
        
        if len(selected) < len(candidate_experts):
            logger.info(f"[Performance] Optimized expert selection: {selected} (scores: {[f'{e}:{self.get_expert_performance_score(e):.1f}' for e in selected]})")
        
        return selected
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.recent_metrics:
            return {"status": "no_data"}
        
        # Calculate aggregate metrics
        recent_total_times = [m.total_time_ms for m in self.recent_metrics]
        recent_cache_hits = sum(1 for m in self.recent_metrics if m.cache_hit)
        
        summary = {
            "requests_tracked": len(self.recent_metrics),
            "avg_response_time_ms": sum(recent_total_times) / len(recent_total_times),
            "min_response_time_ms": min(recent_total_times),
            "max_response_time_ms": max(recent_total_times),
            "cache_hit_rate": recent_cache_hits / len(self.recent_metrics),
            "expert_stats": {},
            "circuit_breakers": {}
        }
        
        # Add expert statistics
        for expert_id, stats in self.expert_stats.items():
            summary["expert_stats"][expert_id] = {
                "total_executions": stats.total_executions,
                "success_rate": stats.success_rate,
                "avg_latency_ms": stats.avg_latency_ms,
                "performance_score": self.get_expert_performance_score(expert_id)
            }
        
        # Add circuit breaker status
        for expert_id, is_open in self.circuit_breakers.items():
            if is_open:
                summary["circuit_breakers"][expert_id] = {
                    "status": "open",
                    "reset_time": self.circuit_breaker_reset_time.get(expert_id, 0)
                }
        
        return summary
    
    def log_performance_summary(self):
        """Log performance summary to console."""
        summary = self.get_performance_summary()
        
        if summary.get("status") == "no_data":
            logger.info("[Performance] No performance data available")
            return
        
        logger.info(f"[Performance Summary] {summary['requests_tracked']} requests tracked")
        logger.info(f"[Performance Summary] Avg response time: {summary['avg_response_time_ms']:.1f}ms")
        logger.info(f"[Performance Summary] Cache hit rate: {summary['cache_hit_rate']:.1%}")
        
        # Log top performing experts
        expert_scores = [(eid, data["performance_score"]) for eid, data in summary["expert_stats"].items()]
        expert_scores.sort(key=lambda x: x[1], reverse=True)
        
        if expert_scores:
            logger.info("[Performance Summary] Top experts by performance:")
            for expert_id, score in expert_scores[:5]:
                stats = summary["expert_stats"][expert_id]
                logger.info(f"  {expert_id}: {score:.1f} (success: {stats['success_rate']:.1%}, latency: {stats['avg_latency_ms']:.1f}ms)")
        
        # Log circuit breaker status
        if summary["circuit_breakers"]:
            logger.warning(f"[Performance Summary] Circuit breakers open: {list(summary['circuit_breakers'].keys())}")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def reset_performance_monitor():
    """Reset global performance monitor (for testing)."""
    global _performance_monitor
    _performance_monitor = None