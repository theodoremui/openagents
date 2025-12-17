/**
 * Voice State Animation Component
 *
 * Visual feedback component showing the agent's current state with animations.
 * Implements specification Section 6.2: Voice State Animation
 *
 * Features:
 * - Distinct animations for each state (listening, thinking, speaking)
 * - Smooth transitions between states
 * - Respects prefers-reduced-motion
 * - Accessible with ARIA labels
 * - Responsive sizing
 */

"use client";

import React, { useMemo, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useVoiceMode } from "./VoiceModeProvider";
import type { VoiceState } from "@/lib/types/voice";

interface VoiceStateAnimationProps {
  className?: string;
}

/**
 * State configuration for styling and accessibility
 */
interface StateConfig {
  containerClass: string;
  ariaLabel: string;
  color: string;
}

function getStateConfig(state: VoiceState): StateConfig {
  const configs: Record<VoiceState, StateConfig> = {
    disconnected: {
      containerClass: "w-24 h-24 bg-muted",
      ariaLabel: "Voice mode inactive",
      color: "bg-muted-foreground/30",
    },
    connecting: {
      containerClass: "w-24 h-24 bg-primary/10",
      ariaLabel: "Connecting to voice session",
      color: "bg-primary",
    },
    initializing: {
      containerClass: "w-24 h-24 bg-primary/10",
      ariaLabel: "Initializing voice agent",
      color: "bg-primary",
    },
    listening: {
      containerClass: "w-32 h-32 bg-green-500/10",
      ariaLabel: "Agent is listening. Speak now.",
      color: "bg-green-500",
    },
    processing: {
      containerClass: "w-28 h-28 bg-blue-500/10",
      ariaLabel: "Processing your speech",
      color: "bg-blue-500",
    },
    thinking: {
      containerClass: "w-28 h-28 bg-amber-500/10",
      ariaLabel: "Agent is thinking",
      color: "bg-amber-500",
    },
    speaking: {
      containerClass: "w-36 h-36 bg-blue-500/10",
      ariaLabel: "Agent is speaking",
      color: "bg-blue-500",
    },
  };
  return configs[state] || configs.disconnected;
}

/**
 * Check for reduced motion preference
 */
function usePrefersReducedMotion(): boolean {
  const [prefersReduced, setPrefersReduced] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReduced(query.matches);

    const handler = (e: MediaQueryListEvent) => setPrefersReduced(e.matches);
    query.addEventListener("change", handler);
    return () => query.removeEventListener("change", handler);
  }, []);

  return prefersReduced;
}

/**
 * Main Voice State Animation Component
 */
export const VoiceStateAnimation: React.FC<VoiceStateAnimationProps> = ({
  className = "",
}) => {
  const { agentState } = useVoiceMode();
  const prefersReducedMotion = usePrefersReducedMotion();
  const stateConfig = useMemo(
    () => getStateConfig(agentState),
    [agentState]
  );

  return (
    <div
      className={`relative flex items-center justify-center rounded-full transition-all duration-300 ${stateConfig.containerClass} ${className}`}
      role="status"
      aria-label={stateConfig.ariaLabel}
      aria-live="polite"
    >
      <AnimatePresence mode="wait">
        {agentState === "listening" && (
          <ListeningAnimation
            key="listening"
            reduced={prefersReducedMotion}
            color={stateConfig.color}
          />
        )}
        {agentState === "thinking" && (
          <ThinkingAnimation
            key="thinking"
            reduced={prefersReducedMotion}
            color={stateConfig.color}
          />
        )}
        {(agentState === "speaking" || agentState === "processing") && (
          <SpeakingAnimation
            key="speaking"
            reduced={prefersReducedMotion}
            color={stateConfig.color}
          />
        )}
        {(agentState === "connecting" || agentState === "initializing") && (
          <ConnectingAnimation
            key="connecting"
            reduced={prefersReducedMotion}
            color={stateConfig.color}
          />
        )}
        {agentState === "disconnected" && (
          <IdleIndicator key="idle" color={stateConfig.color} />
        )}
      </AnimatePresence>

      {/* State label for screen readers */}
      <span className="sr-only">{stateConfig.ariaLabel}</span>
    </div>
  );
};

/**
 * Listening Animation - Pulsing rings
 */
const ListeningAnimation: React.FC<{
  reduced: boolean;
  color: string;
}> = ({ reduced, color }) => {
  if (reduced) {
    return (
      <div
        className={`w-16 h-16 rounded-full ${color.replace("bg-", "border-")} border-2`}
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      className="relative w-16 h-16"
    >
      {/* Pulsing rings */}
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className={`absolute inset-0 rounded-full ${color.replace("bg-", "border-")} border-2`}
          animate={{
            scale: [1, 1.5, 1.8],
            opacity: [0.6, 0.3, 0],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            delay: i * 0.5,
            ease: "easeOut",
          }}
        />
      ))}
      {/* Center dot */}
      <motion.div
        className={`absolute inset-0 m-auto w-4 h-4 rounded-full ${color}`}
        animate={{
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 1,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
    </motion.div>
  );
};

/**
 * Thinking Animation - Bouncing dots
 */
const ThinkingAnimation: React.FC<{
  reduced: boolean;
  color: string;
}> = ({ reduced, color }) => {
  if (reduced) {
    return (
      <div className="flex gap-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className={`w-3 h-3 rounded-full ${color}`} />
        ))}
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex gap-2"
    >
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className={`w-3 h-3 rounded-full ${color}`}
          animate={{
            y: [0, -12, 0],
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            delay: i * 0.15,
            ease: "easeInOut",
          }}
        />
      ))}
    </motion.div>
  );
};

/**
 * Speaking Animation - Bar visualizer
 */
const SpeakingAnimation: React.FC<{
  reduced: boolean;
  color: string;
}> = ({ reduced, color }) => {
  if (reduced) {
    return (
      <div className="flex gap-1 items-center">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className={`w-2 h-8 rounded ${color}`} />
        ))}
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="flex gap-1 items-center"
    >
      {[0, 1, 2, 3, 4].map((i) => (
        <motion.div
          key={i}
          className={`w-2 rounded ${color}`}
          animate={{
            height: [8, 32, 8],
          }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: i * 0.1,
            ease: "easeInOut",
          }}
        />
      ))}
    </motion.div>
  );
};

/**
 * Connecting Animation - Spinner
 */
const ConnectingAnimation: React.FC<{
  reduced: boolean;
  color: string;
}> = ({ reduced, color }) => {
  if (reduced) {
    return (
      <div
        className={`w-8 h-8 rounded-full ${color.replace("bg-", "border-")} border-2 border-t-transparent`}
      />
    );
  }

  return (
    <motion.div
      className={`w-8 h-8 rounded-full ${color.replace("bg-", "border-")} border-2 border-t-transparent`}
      animate={{ rotate: 360 }}
      transition={{
        duration: 1,
        repeat: Infinity,
        ease: "linear",
      }}
    />
  );
};

/**
 * Idle Indicator - Static dot
 */
const IdleIndicator: React.FC<{ color: string }> = ({ color }) => (
  <div className={`w-4 h-4 rounded-full ${color}`} />
);
