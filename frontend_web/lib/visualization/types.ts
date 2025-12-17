/**
 * TypeScript types for MoE Orchestration Trace Visualization
 *
 * These types mirror the Python dataclasses from backend:
 * - asdrp/orchestration/moe/orchestrator.py
 */

export interface ExpertExecutionDetail {
  expert_id: string;
  agent_name: string;
  confidence: number;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  start_time?: number;
  end_time?: number;
  latency_ms?: number;
  response?: string;
  tools_used?: string[];
  error?: string;
}

export interface MoETrace {
  request_id: string;
  query: string;

  // Timestamps (seconds since epoch)
  selection_start?: number;
  selection_end?: number;
  execution_start?: number;
  execution_end?: number;
  mixing_start?: number;
  mixing_end?: number;

  // Expert details
  selected_experts?: string[];
  expert_details?: ExpertExecutionDetail[];

  // Results
  expert_results?: any[];
  final_response?: string;

  // Performance
  latency_ms: number;
  cache_hit: boolean;
  fallback: boolean;
  error?: string;
}

export interface MoETraceResponse {
  session_id: string;
  trace: MoETrace;
  timestamp: number;
}
