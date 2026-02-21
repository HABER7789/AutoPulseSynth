import { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Activity } from 'lucide-react';

const PulseVisualizer = () => {
    const [isSynthesizing, setIsSynthesizing] = useState(false);
    const [showResult, setShowResult] = useState(false);

    const handleSynthesize = () => {
        setIsSynthesizing(true);
        setShowResult(false);

        // Simulate backend optimization process
        setTimeout(() => {
            setIsSynthesizing(false);
            setShowResult(true);
        }, 3000);
    };

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '2rem',
            width: '100%',
            maxWidth: '800px',
            margin: '0 auto'
        }}>

            {/* Interactive Trigger */}
            <motion.button
                onClick={handleSynthesize}
                disabled={isSynthesizing}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                style={{
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--neon-pink)',
                    padding: '1rem 2rem',
                    borderRadius: '50px',
                    fontSize: '1.125rem',
                    fontWeight: 500,
                    cursor: isSynthesizing ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    boxShadow: isSynthesizing
                        ? '0 0 50px rgba(255,20,147,0.8), 0 0 20px rgba(255,105,180,0.5)'
                        : '0 0 30px rgba(255,20,147,0.4)',
                    transition: 'all 0.3s ease',
                }}
            >
                {isSynthesizing ? (
                    <>
                        <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                        >
                            <Activity size={20} color="var(--neon-cyan)" />
                        </motion.div>
                        Optimizing Parameters...
                    </>
                ) : (
                    <>
                        <Sparkles size={20} />
                        Synthesize Robust Pulse
                    </>
                )}
            </motion.button>

            {/* Abstract Waveform Visualizer Area */}
            <motion.div
                className="glass-panel"
                style={{
                    width: '100%',
                    height: '250px',
                    position: 'relative',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden',
                    padding: '2rem'
                }}
                animate={{
                    borderColor: isSynthesizing
                        ? 'var(--neon-cyan)'
                        : showResult
                            ? 'var(--neon-pink)'
                            : 'var(--cosmic-border)',
                }}
                transition={{ duration: 0.5 }}
            >
                {/* Placeholder text when idle */}
                {!isSynthesizing && !showResult && (
                    <p style={{ color: 'var(--text-secondary)', fontWeight: 300, fontStyle: 'italic' }}>
                        Awaiting optimization parameters...
                    </p>
                )}

                {/* Processing Waves */}
                {isSynthesizing && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', height: '100px' }}>
                        {[...Array(15)].map((_, i) => (
                            <motion.div
                                key={i}
                                style={{
                                    width: '8px',
                                    background: 'linear-gradient(to top, var(--neon-pink), var(--neon-cyan))',
                                    borderRadius: '4px',
                                }}
                                animate={{
                                    height: ['20%', '100%', '20%'],
                                    opacity: [0.3, 1, 0.3]
                                }}
                                transition={{
                                    duration: 1,
                                    repeat: Infinity,
                                    delay: i * 0.1,
                                    ease: 'easeInOut'
                                }}
                            />
                        ))}
                    </div>
                )}

                {/* Result State */}
                {showResult && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            gap: '1rem',
                            textAlign: 'center'
                        }}
                    >
                        <h3 style={{ fontSize: '1.5rem', fontWeight: 600 }}>Synthesis Complete</h3>
                        <div style={{ display: 'flex', gap: '2rem', marginTop: '1rem' }}>
                            <div style={{ textAlign: 'center' }}>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Mean Fidelity</p>
                                <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--neon-cyan)' }}>98.5%</p>
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Worst Case</p>
                                <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--neon-pink)' }}>96.8%</p>
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>R² Acc.</p>
                                <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'white' }}>0.90</p>
                            </div>
                        </div>

                        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '1rem' }}>
                            Pulse optimized for $\pm 2$ MHz detuning.
                        </p>
                    </motion.div>
                )}

            </motion.div>
        </div>
    );
};

export default PulseVisualizer;
