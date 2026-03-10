"use client";

import React, { useEffect, useRef } from 'react';

interface SignalConvergenceProps {
  phase: 'idle' | 'converging' | 'resolved';
  duration: number; // roughly maps to wavelength/spread
  driftBounds: number; // roughly maps to messiness/offset
  isDark: boolean;
}

export default function SignalConvergence({ phase, duration, driftBounds, isDark }: SignalConvergenceProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hoverRef = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;

    // Simulation state for 7 waves
    const numWaves = 7;
    const waves = Array.from({ length: numWaves }).map((_, i) => {
      const normalizedIndex = (i - Math.floor(numWaves / 2)) / Math.floor(numWaves / 2); // -1 to 1
      return {
        id: i,
        normIdx: normalizedIndex,
        // Current values
        yOffset: 0,
        amplitude: 0,
        frequency: 0,
        opacity: 0,
        centerX: 0.2,
        spread: 0.02,
        r: 0, g: 0, b: 0,
        phaseOffset: Math.random() * Math.PI * 2,
        wobbleSpeed: 0.5 + Math.random() * 1.5,
      };
    });

    // Easing helper
    const lerp = (start: number, end: number, amt: number) => {
      return (1 - amt) * start + amt * end;
    };

    const resize = () => {
      const parent = canvas.parentElement;
      if (parent) {
        // Handle high DPI displays for crisp rendering
        const dpr = window.devicePixelRatio || 1;
        canvas.width = parent.clientWidth * dpr;
        canvas.height = parent.clientHeight * dpr;
        ctx.scale(dpr, dpr);
        canvas.style.width = `${parent.clientWidth}px`;
        canvas.style.height = `${parent.clientHeight}px`;
      }
    };
    window.addEventListener('resize', resize);
    resize();

    const draw = () => {
      // Clear canvas
      const width = canvas.width / (window.devicePixelRatio || 1);
      const height = canvas.height / (window.devicePixelRatio || 1);
      ctx.clearRect(0, 0, width, height);

      time += 0.006; // Much slower and subtler

      // Determine global targets based on phase & inputs
      const isHovered = hoverRef.current;
      const effectivePhase = (phase === 'resolved' && isHovered) ? 'decompose' : phase;
      
      const speedParam = (phase === 'converging') ? 0.02 : 0.01; // Slower transitions

      waves.forEach(wave => {
        // Target calculations based on phase
        let tYOffset = 0;
        let tAmplitude = 0;
        let tFrequency = 0;
        let tOpacity = 0;
        let tCenterX = 0.25;
        let tSpread = 0.05;
        let tColor = isDark ? { r: 255, g: 255, b: 255 } : { r: 10, g: 10, b: 10 }; 
        
        // Base wavelength based on user's duration input (0.01 to 1.0)
        // Shorter duration = tighter waves
        const baseFreq = 0.005 + (1.0 / Math.max(duration, 0.01)) * 0.0005;
        
        // Messiness based on drift bounds (0.0 to 20.0)
        const effectiveDrift = Math.max(driftBounds, 0.5); // Minimum spread

        if (effectivePhase === 'idle' || effectivePhase === 'decompose') {
          // Noisy, drifting apart
          tYOffset = wave.normIdx * effectiveDrift * 15 * (effectivePhase === 'decompose' ? 0.3 : 1.0); // Spread them out vertically
          tAmplitude = 40 + Math.abs(wave.normIdx) * 10 * effectiveDrift; 
          tFrequency = baseFreq * (1 + wave.normIdx * 0.1); // Slightly different frequencies
          tOpacity = effectivePhase === 'decompose' ? 0.4 : 0.15; // Faint in idle, stronger in decompose
          tCenterX = 0.25; // Centered behind the left input panel
          tSpread = 0.08; // Wider spread so it feels less constrained
        } else if (effectivePhase === 'converging') {
          // Bending towards center
          tYOffset = 0;
          tAmplitude = 80;
          tFrequency = baseFreq;
          tOpacity = 0.3;
          tCenterX = 0.5; // Moving to center
          tSpread = 0.15;
        } else if (effectivePhase === 'resolved') {
          // Single clean wave
          tYOffset = 0;
          tAmplitude = 60;
          tFrequency = baseFreq;
          tOpacity = wave.id === Math.floor(numWaves / 2) ? 0.6 : 0.0; // Show only the center wave
          tCenterX = 0.7; // Moves into the right panel area
          tSpread = 0.5; // Broad span over the right panel
        }

        // Interpolate current values to targets
        wave.yOffset = lerp(wave.yOffset, tYOffset, speedParam);
        wave.amplitude = lerp(wave.amplitude, tAmplitude, speedParam);
        wave.frequency = lerp(wave.frequency, tFrequency, speedParam);
        wave.opacity = lerp(wave.opacity, tOpacity, speedParam);
        wave.centerX = lerp(wave.centerX, tCenterX, speedParam);
        wave.spread = lerp(wave.spread, tSpread, speedParam);
        wave.r = lerp(wave.r, tColor.r, speedParam);
        wave.g = lerp(wave.g, tColor.g, speedParam);
        wave.b = lerp(wave.b, tColor.b, speedParam);

        // Don't draw if nearly invisible
        if (wave.opacity < 0.01) return;

        // Draw the wave
        ctx.beginPath();
        
        // To make it look like a flow diagram, we draw from left to right
        for (let x = 0; x <= width; x += 5) {
          // Add a Gaussian envelope so waves are strongest in the middle
          const envCenterX = width * wave.centerX;
          const distFromCenter = x - envCenterX;
          const envelope = Math.exp(-(distFromCenter * distFromCenter) / (width * width * wave.spread));
          
          // Wobble effect for idle state
          const wobble = (effectivePhase === 'idle') ? Math.sin(time * wave.wobbleSpeed + x * 0.01) * 10 : 0;
          
          // Flowing time offset
          const timeOffset = time * 2;
          
          const yPos = Math.sin(x * wave.frequency - timeOffset + wave.phaseOffset) * wave.amplitude * envelope + wave.yOffset + wobble;
          
          if (x === 0) {
            ctx.moveTo(x, height / 2 + yPos);
          } else {
            ctx.lineTo(x, height / 2 + yPos);
          }
        }

        ctx.strokeStyle = `rgba(${Math.round(wave.r)}, ${Math.round(wave.g)}, ${Math.round(wave.b)}, ${wave.opacity})`;
        ctx.lineWidth = effectivePhase === 'resolved' ? 3 : 2;
        ctx.stroke();
      });

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [phase, duration, driftBounds, isDark]);

  return (
    <div 
      className="fixed inset-0 z-0 pointer-events-none transition-opacity duration-1000 overflow-hidden"
    >
      <div className={`absolute inset-0 bg-gradient-to-r from-transparent via-${isDark ? 'white' : 'black'}/5 to-transparent opacity-30`}></div>
      <canvas 
        ref={canvasRef} 
        className="absolute inset-0 w-full h-full pointer-events-auto"
        onMouseEnter={() => { hoverRef.current = true; }}
        onMouseLeave={() => { hoverRef.current = false; }}
        style={{ cursor: phase === 'resolved' ? 'crosshair' : 'default' }}
      />
    </div>
  );
}
