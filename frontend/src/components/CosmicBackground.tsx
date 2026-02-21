import React from 'react';
import { motion } from 'framer-motion';

const CosmicBackground: React.FC = () => {
  return (
    <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', zIndex: -1 }}>
      {/* Deep Space Base Layer */}
      <div 
        style={{ 
          position: 'absolute', 
          inset: 0, 
          background: 'linear-gradient(to bottom right, #05020a, #0a0515, #080312)' 
        }} 
      />

      {/* Shimmer Wave 1: Cyan/Blue */}
      <motion.div
        style={{
          position: 'absolute',
          top: '-20%',
          left: '-10%',
          width: '60vw',
          height: '60vw',
          borderRadius: '50%',
          filter: 'blur(150px)',
          background: 'radial-gradient(circle, rgba(0,255,255,0.15) 0%, rgba(0,100,255,0.05) 50%, transparent 70%)',
          willChange: 'transform, opacity',
        }}
        animate={{
          scale: [1, 1.1, 0.9, 1],
          opacity: [0.5, 0.8, 0.4, 0.5],
          x: [0, 50, -30, 0],
          y: [0, 30, -50, 0]
        }}
        transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
      />

      {/* Shimmer Wave 2: Deep Pink */}
      <motion.div
        style={{
          position: 'absolute',
          bottom: '-10%',
          right: '-20%',
          width: '70vw',
          height: '70vw',
          borderRadius: '50%',
          filter: 'blur(180px)',
          background: 'radial-gradient(circle, rgba(255,20,147,0.2) 0%, rgba(255,105,180,0.1) 40%, transparent 70%)',
          willChange: 'transform, opacity',
        }}
        animate={{
          scale: [0.9, 1.2, 1],
          opacity: [0.4, 0.7, 0.4],
          x: [0, -60, 20, 0],
          y: [0, -40, 40, 0]
        }}
        transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
      />
      
      {/* Shimmer Wave 3: Purple Accent */}
      <motion.div
        style={{
          position: 'absolute',
          top: '30%',
          left: '20%',
          width: '40vw',
          height: '40vw',
          borderRadius: '50%',
          filter: 'blur(120px)',
          background: 'radial-gradient(circle, rgba(138,43,226,0.15) 0%, rgba(75,0,130,0.05) 50%, transparent 70%)',
          willChange: 'transform, opacity',
        }}
        animate={{
          scale: [1, 1.3, 0.8, 1],
          opacity: [0.3, 0.6, 0.2, 0.3],
        }}
        transition={{ duration: 12, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  );
};

export default CosmicBackground;
