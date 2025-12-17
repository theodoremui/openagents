/**
 * Session Management Service
 *
 * Handles conversation session IDs for maintaining context across requests.
 * Follows SOLID principles with single responsibility for session management.
 */

import type { ISessionService } from "./interfaces";

export class SessionService implements ISessionService {
  private sessions: Map<string, string> = new Map();

  /**
   * Get or create session ID for an agent
   *
   * Generates a unique session ID per agent to maintain conversation history.
   */
  public getSessionId(agentId: string): string {
    let sessionId = this.sessions.get(agentId);

    if (!sessionId) {
      sessionId = this.generateSessionId(agentId);
      this.sessions.set(agentId, sessionId);
    }

    return sessionId;
  }

  /**
   * Clear session for specific agent
   */
  public clearSession(agentId: string): void {
    this.sessions.delete(agentId);
  }

  /**
   * Clear all sessions
   */
  public clearAllSessions(): void {
    this.sessions.clear();
  }

  /**
   * Generate unique session ID
   */
  private generateSessionId(agentId: string): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 15);
    return `${agentId}-${timestamp}-${random}`;
  }

  /**
   * Get all active sessions
   */
  public getActiveSessions(): Map<string, string> {
    return new Map(this.sessions);
  }

  /**
   * Check if agent has active session
   */
  public hasSession(agentId: string): boolean {
    return this.sessions.has(agentId);
  }
}
