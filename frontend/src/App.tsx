import CosmicBackground from './components/CosmicBackground';
import PulseVisualizer from './components/PulseVisualizer';
import './index.css';

function App() {
  return (
    <>
      <CosmicBackground />
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '2rem',
        position: 'relative',
        zIndex: 1
      }}>

        {/* Header Section */}
        <header style={{ width: '100%', maxWidth: '1200px', padding: '2rem 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.03em' }}>
            AutoPulse<span className="text-gradient">Synth</span>
          </h1>
          <nav style={{ display: 'flex', gap: '2rem' }}>
            <a href="#" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.9rem', transition: 'color 0.2s' }} onMouseOver={(e) => e.currentTarget.style.color = 'var(--text-primary)'} onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}>Documentation</a>
            <a href="https://github.com/HABER7789/AutoPulseSynth" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.9rem', transition: 'color 0.2s' }} onMouseOver={(e) => e.currentTarget.style.color = 'var(--text-primary)'} onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}>GitHub</a>
          </nav>
        </header>

        {/* Hero Section */}
        <main style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center',
          maxWidth: '800px',
          gap: '2rem',
          marginTop: '-10vh'
        }}>

          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            borderRadius: '100px',
            background: 'var(--cosmic-surface)',
            border: '1px solid var(--cosmic-border)',
            fontSize: '0.875rem',
            color: 'var(--neon-pink)',
            marginBottom: '1rem'
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--neon-cyan)', boxShadow: '0 0 10px var(--neon-cyan)' }}></span>
            Phase 5 Interactive Frontend
          </div>

          <h2 style={{
            fontSize: 'clamp(3rem, 8vw, 5rem)',
            fontWeight: 700,
            lineHeight: 1.1,
            letterSpacing: '-0.04em'
          }}>
            Robust Quantum <br />
            <span className="text-gradient">Control Synthesis</span>
          </h2>

          <p style={{
            fontSize: '1.25rem',
            color: 'var(--text-secondary)',
            maxWidth: '600px',
            lineHeight: 1.6,
            fontWeight: 300
          }}>
            Generate &gt;96% fidelity control pulses resilient to calibration drift.
            Powered by surrogate-assisted optimization architecture.
          </p>

          <div style={{ marginTop: '3rem', width: '100%' }}>
            <PulseVisualizer />
          </div>

        </main>
      </div>
    </>
  );
}

export default App;
