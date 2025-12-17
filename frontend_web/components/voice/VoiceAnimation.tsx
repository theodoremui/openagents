/**
 * VoiceAnimation Component
 *
 * Audio waveform visualization for recording and playback.
 * Features:
 * - Real-time audio level bars
 * - Playback frequency visualization
 * - Smooth animations
 * - Customizable styling
 */

'use client';

import React, { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

/**
 * VoiceAnimation props
 */
export interface VoiceAnimationProps {
  /** Audio level (0.0 - 1.0) for recording visualization */
  audioLevel?: number;
  /** Frequency data for playback visualization */
  frequencyData?: Uint8Array | null;
  /** Whether audio is active (recording or playing) */
  isActive?: boolean;
  /** Number of bars to display */
  barCount?: number;
  /** Bar width in pixels */
  barWidth?: number;
  /** Bar gap in pixels */
  barGap?: number;
  /** Maximum bar height in pixels */
  maxHeight?: number;
  /** Bar color */
  barColor?: string;
  /** Active bar color (when audio is active) */
  activeBarColor?: string;
  /** Animation style */
  animationStyle?: 'bars' | 'wave' | 'pulse';
  /** Custom className */
  className?: string;
}

/**
 * Default props
 */
const DEFAULT_PROPS = {
  audioLevel: 0,
  frequencyData: null,
  isActive: false,
  barCount: 5,
  barWidth: 4,
  barGap: 4,
  maxHeight: 40,
  barColor: 'rgba(148, 163, 184, 0.5)', // slate-400 with opacity
  activeBarColor: 'rgba(59, 130, 246, 0.8)', // blue-500 with opacity
  animationStyle: 'bars' as const,
};

/**
 * Generate bar heights from audio level (for recording)
 */
function generateBarHeightsFromLevel(
  audioLevel: number,
  barCount: number,
  maxHeight: number
): number[] {
  const heights: number[] = [];
  const center = Math.floor(barCount / 2);

  for (let i = 0; i < barCount; i++) {
    // Create symmetric pattern from center
    const distanceFromCenter = Math.abs(i - center);
    const heightFactor = 1 - (distanceFromCenter / center) * 0.5;

    // Add some randomness
    const randomFactor = 0.8 + Math.random() * 0.4;

    // Calculate height based on audio level
    const height = audioLevel * maxHeight * heightFactor * randomFactor;

    heights.push(Math.max(2, height)); // Minimum height of 2px
  }

  return heights;
}

/**
 * Generate bar heights from frequency data (for playback)
 */
function generateBarHeightsFromFrequency(
  frequencyData: Uint8Array,
  barCount: number,
  maxHeight: number
): number[] {
  const heights: number[] = [];
  const dataStep = Math.floor(frequencyData.length / barCount);

  for (let i = 0; i < barCount; i++) {
    const dataIndex = i * dataStep;
    const value = frequencyData[dataIndex] || 0;

    // Normalize to 0-1 and apply to maxHeight
    const normalized = value / 255;
    const height = normalized * maxHeight;

    heights.push(Math.max(2, height));
  }

  return heights;
}

/**
 * VoiceAnimation component
 */
export const VoiceAnimation: React.FC<VoiceAnimationProps> = (props) => {
  const {
    audioLevel = DEFAULT_PROPS.audioLevel,
    frequencyData = DEFAULT_PROPS.frequencyData,
    isActive = DEFAULT_PROPS.isActive,
    barCount = DEFAULT_PROPS.barCount,
    barWidth = DEFAULT_PROPS.barWidth,
    barGap = DEFAULT_PROPS.barGap,
    maxHeight = DEFAULT_PROPS.maxHeight,
    barColor = DEFAULT_PROPS.barColor,
    activeBarColor = DEFAULT_PROPS.activeBarColor,
    animationStyle = DEFAULT_PROPS.animationStyle,
    className,
  } = props;

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);

  /**
   * Draw bars visualization
   */
  const drawBars = (heights: number[]) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Calculate total width
    const totalWidth = barCount * barWidth + (barCount - 1) * barGap;
    const startX = (canvas.width - totalWidth) / 2;

    // Draw bars
    heights.forEach((height, index) => {
      const x = startX + index * (barWidth + barGap);
      const y = (canvas.height - height) / 2;

      // Set color based on active state
      ctx.fillStyle = isActive ? activeBarColor : barColor;

      // Draw rounded rectangle
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, height, barWidth / 2);
      ctx.fill();
    });
  };

  /**
   * Draw wave visualization
   */
  const drawWave = (heights: number[]) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const centerY = canvas.height / 2;
    const spacing = canvas.width / (barCount - 1);

    // Set color and line width
    ctx.strokeStyle = isActive ? activeBarColor : barColor;
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // Draw wave path
    ctx.beginPath();
    heights.forEach((height, index) => {
      const x = index * spacing;
      const y = centerY - height / 2;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    // Draw mirrored wave
    ctx.beginPath();
    heights.forEach((height, index) => {
      const x = index * spacing;
      const y = centerY + height / 2;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
  };

  /**
   * Draw pulse visualization
   */
  const drawPulse = (heights: number[]) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    // Calculate average height
    const avgHeight = heights.reduce((a, b) => a + b, 0) / heights.length;
    const radius = avgHeight / 2;

    // Draw pulsing circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.fillStyle = isActive ? activeBarColor : barColor;
    ctx.fill();

    // Draw outer ring for active state
    if (isActive) {
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius + 4, 0, Math.PI * 2);
      ctx.strokeStyle = activeBarColor;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  };

  /**
   * Animation loop
   */
  useEffect(() => {
    const animate = () => {
      let heights: number[];

      // Determine height source
      if (frequencyData && frequencyData.length > 0) {
        heights = generateBarHeightsFromFrequency(frequencyData, barCount, maxHeight);
      } else {
        heights = generateBarHeightsFromLevel(audioLevel, barCount, maxHeight);
      }

      // Draw based on style
      switch (animationStyle) {
        case 'wave':
          drawWave(heights);
          break;
        case 'pulse':
          drawPulse(heights);
          break;
        case 'bars':
        default:
          drawBars(heights);
          break;
      }

      // Continue animation if active
      if (isActive) {
        animationFrameRef.current = requestAnimationFrame(animate);
      }
    };

    // Start animation
    if (isActive) {
      animate();
    } else {
      // Draw idle state
      const idleHeights = new Array(barCount).fill(maxHeight * 0.1);
      drawBars(idleHeights);
    }

    // Cleanup
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    };
  }, [
    audioLevel,
    frequencyData,
    isActive,
    barCount,
    maxHeight,
    animationStyle,
    barColor,
    activeBarColor,
  ]);

  /**
   * Calculate canvas dimensions
   */
  const canvasWidth = barCount * barWidth + (barCount - 1) * barGap + 40; // +40 for padding
  const canvasHeight = maxHeight + 20; // +20 for padding

  return (
    <div className={cn('flex items-center justify-center', className)}>
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={canvasHeight}
        className="rounded-lg"
        aria-label="Audio visualization"
      />
    </div>
  );
};

export default VoiceAnimation;
