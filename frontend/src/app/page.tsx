"use client";

import React, { useState, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import { Play, Info, CheckCircle2, Cpu, Sun, Moon, ChevronRight, X, AlertTriangle } from 'lucide-react';
import SignalConvergence from '@/components/SignalConvergence';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false, loading: () => <div className="h-64 flex items-center justify-center text-zinc-500 font-mono text-xs">Initializing engine...</div> });

function MatrixDisplay({ label, matrix, isDark }: { label: string; matrix: any[][]; isDark: boolean }) {
  const fmt = (v: any) => {
    if (typeof v === 'string') return v;
    if (typeof v === 'object' && v !== null) {
      const r = v[0] || 0, i = v[1] || 0;
      if (Math.abs(i) < 1e-10) return r.toFixed(1);
      if (Math.abs(r) < 1e-10) return `${i.toFixed(1)}i`;
      return `${r.toFixed(1)}${i >= 0 ? '+' : ''}${i.toFixed(1)}i`;
    }
    return Number(v).toFixed(1);
  };
  return (
    <div className="inline-block">
      <span className={`text-[10px] ${isDark ? 'text-zinc-500' : 'text-slate-400'}`}>{label} = </span>
      <span className="font-mono text-[11px]">
        [{matrix.map((row, i) => (
          <span key={i}>{i > 0 && ' '}{row.map((v, j) => <span key={j}>{j > 0 && ', '}{fmt(v)}</span>)}{i < matrix.length - 1 && ';'}</span>
        ))}]
      </span>
    </div>
  );
}

function StreamLogEntry({ evt, isDark, theme }: { evt: any; isDark: boolean; theme: any }) {
  const { type, data } = evt;
  const labelClass = `text-[10px] font-bold uppercase tracking-widest ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`;
  const monoClass = `font-mono text-[11px] ${theme.textMuted}`;
  const valClass = `font-mono text-[11px] font-semibold ${theme.textMain}`;

  if (type === 'setup') {
    return (
      <div className="space-y-1.5">
        <div className={labelClass}>▸ Hamiltonian</div>
        <div className={monoClass}>{data.hamiltonian}</div>
        <div className={monoClass}>
          Δ ∈ [{data.delta_range_mhz[0]}, {data.delta_range_mhz[1]}] MHz &nbsp;|&nbsp; n_steps: <span className={valClass}>{data.n_steps}</span> &nbsp;|&nbsp; t: <span className={valClass}>{data.duration_ns}ns</span>
        </div>
        {data.target_unitary && (
          <MatrixDisplay label="U_target" matrix={data.target_unitary} isDark={isDark} />
        )}
      </div>
    );
  }

  if (type === 'training_start') {
    return (
      <div className="space-y-1.5">
        <div className={labelClass}>▸ Training</div>
        <div className={monoClass}>
          Generating <span className={valClass}>{data.total_sims}</span> simulations ({data.n_pulses} pulses × {data.n_theta} θ)...
        </div>
        <div className="w-full h-1.5 rounded-full overflow-hidden bg-black/10 dark:bg-white/10">
          <div className={`h-full rounded-full animate-pulse ${isDark ? 'bg-violet-400' : 'bg-violet-500'}`} style={{ width: '100%' }} />
        </div>
      </div>
    );
  }

  if (type === 'training_done') {
    return (
      <div className={monoClass}>
        Training data complete — <span className={valClass}>{data.total_sims} sims</span> in <span className={valClass}>{data.elapsed}s</span>
      </div>
    );
  }

  if (type === 'surrogate') {
    return (
      <div className="space-y-1">
        <div className={labelClass}>▸ Surrogate Model</div>
        <div className={monoClass}>
          Random Forest ({data.n_estimators} trees, {data.n_features} features)
        </div>
        <div className={monoClass}>
          R² = <span className={`font-semibold ${isDark ? 'text-sky-400' : 'text-sky-600'}`}>{data.r2}</span> &nbsp;|&nbsp; MAE = <span className={valClass}>{data.mae}</span>
        </div>
      </div>
    );
  }

  if (type === 'optimization') {
    const pct = Math.min(100, Math.round((data.generations / data.maxiter) * 100));
    return (
      <div className="space-y-1.5">
        <div className={labelClass}>▸ Differential Evolution</div>
        <div className={monoClass}>
          {data.generations} generations (pop={data.popsize}) — converged
        </div>
        <div className="w-full h-1.5 rounded-full overflow-hidden bg-black/10 dark:bg-white/10">
          <div className={`h-full rounded-full transition-all ${isDark ? 'bg-emerald-400' : 'bg-emerald-500'}`} style={{ width: `${pct}%` }} />
        </div>
        <div className={monoClass}>
          f_mean = <span className={`font-semibold ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>{(data.pred_f_mean * 100).toFixed(1)}%</span> &nbsp;|&nbsp; f_worst = <span className={valClass}>{(data.pred_f_worst * 100).toFixed(1)}%</span>
        </div>
      </div>
    );
  }

  if (type === 'verification') {
    return (
      <div className="space-y-1.5">
        <div className={labelClass}>▸ Verification ({data.n_theta} θ samples)</div>
        <div className={monoClass}>
          f_mean = <span className={`font-semibold text-[13px] ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>{(data.f_mean * 100).toFixed(2)}%</span> &nbsp;|&nbsp;
          f_worst = <span className={`font-semibold text-[13px] ${theme.textMain}`}>{(data.f_worst * 100).toFixed(2)}%</span> &nbsp;|&nbsp;
          σ = <span className={valClass}>{(data.f_std * 100).toFixed(2)}%</span>
        </div>
        {data.achieved_U && (
          <div className={`${monoClass} space-y-0.5`}>
            <div>U_achieved = [{data.achieved_U[0].join(', ')}; {data.achieved_U[1].join(', ')}]</div>
          </div>
        )}
        {data.used_baseline_fallback && (
          <div className={`mt-2 px-2.5 py-1.5 rounded-lg text-[10px] font-mono ${isDark ? 'bg-amber-500/10 border border-amber-500/20 text-amber-400' : 'bg-amber-50 border border-amber-200 text-amber-700'}`}>
            ⚠ Surrogate accuracy insufficient for this gate. Using calibrated baseline pulse (f_worst = {(data.baseline_f_worst * 100).toFixed(1)}%). Increase training samples for better results.
          </div>
        )}
      </div>
    );
  }

  if (type === 'robustness_scan') {
    return (
      <div className="space-y-1">
        <div className={labelClass}>▸ Robustness Scan</div>
        <div className={monoClass}>
          Sweeping <span className={valClass}>{data.n_points}</span> detuning points across ±3 MHz...
        </div>
      </div>
    );
  }

  if (type === 'boulder_opal') {
    return (
      <div className="space-y-1.5">
        <div className={`text-[10px] font-bold uppercase tracking-widest ${isDark ? 'text-sky-400' : 'text-sky-600'}`}>▸ Boulder Opal (Q-CTRL)</div>
        <div className={monoClass}>
          Sending optimized pulse to Q-CTRL cloud for independent verification...
        </div>
        <div className="w-full h-1.5 rounded-full overflow-hidden bg-black/10 dark:bg-white/10">
          <div className={`h-full rounded-full animate-pulse ${isDark ? 'bg-sky-400' : 'bg-sky-500'}`} style={{ width: '100%' }} />
        </div>
      </div>
    );
  }

  return null;
}

export default function AutoPulseDashboard() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDark, setIsDark] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [showHelp, setShowHelp] = useState(false);
  const [dismissWarning, setDismissWarning] = useState(false);
  const [isLocal, setIsLocal] = useState(false);

  useEffect(() => {
    setIsLocal(window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  }, []);
  
  // Form State
  const [gate, setGate] = useState("X");
  const [duration, setDuration] = useState("0.04");
  const [detMax, setDetMax] = useState("2.0");
  const [boKey, setBoKey] = useState("");
  
  // Results State
  const [results, setResults] = useState<any>(null);
  const [streamEvents, setStreamEvents] = useState<any[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  // Determine Signal Phase
  const syncPhase = loading ? 'converging' : (results ? 'resolved' : 'idle');

  // Physical Constraints Check
  const numDur = parseFloat(duration) || 0;
  const numDrift = parseFloat(detMax) || 0;
  const isExtreme = numDur < 0.02 || numDrift > 10.0;

  // Timer Effect
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (loading) {
      setElapsedTime(0);
      interval = setInterval(() => {
        setElapsedTime((prev) => prev + 0.1);
      }, 100);
    } else {
      setElapsedTime(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  // Auto-scroll computation log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [streamEvents]);

  const handleSynthesize = async (e: React.FormEvent, quick: boolean = false) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);
    setStreamEvents([]);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const params = new URLSearchParams({
      gate,
      duration: String(parseFloat(duration) * 1e-6),
      det_max_hz: String(parseFloat(detMax) * 1e6),
      det_min_hz: String(-parseFloat(detMax) * 1e6),
      n_train: quick ? '30' : '150',
      n_theta_train: quick ? '2' : '3',
      seed: '43',
      quick: String(quick),
    });
    if (boKey.trim()) params.set('boulder_opal_key', boKey);

    const es = new EventSource(`${API_URL}/api/synthesize-stream?${params}`);

    const eventTypes = ['setup', 'training_start', 'training_done', 'surrogate', 'optimization', 'verification', 'robustness_scan', 'boulder_opal', 'complete', 'error'];
    eventTypes.forEach(type => {
      es.addEventListener(type, (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        setStreamEvents(prev => [...prev, { type, data }]);

        if (type === 'complete') {
          setResults(data);
          setLoading(false);
          es.close();
        }
        if (type === 'error') {
          setError(data.message || 'Synthesis failed');
          setLoading(false);
          es.close();
        }
      });
    });

    es.onerror = () => {
      setError('Connection to synthesis engine lost.');
      setLoading(false);
      es.close();
    };
  };

  const theme = {
    bg: isDark ? 'bg-[#000000]' : 'bg-[#fafafa]',
    nav: 'bg-transparent border-transparent', // Blended perfectly
    textMain: isDark ? 'text-zinc-100' : 'text-slate-900',
    textMuted: isDark ? 'text-[#CDBAD9]' : 'text-slate-600',
    textSubtle: isDark ? 'text-[#A390B0]' : 'text-slate-500',
    border: isDark ? 'border-white/10' : 'border-black/10',
    borderMuted: isDark ? 'border-white/5' : 'border-black/5',
    card: isDark ? 'bg-[#30233A]/40 backdrop-blur-md' : 'bg-white/50 backdrop-blur-md shadow-xl shadow-purple-900/5',
    cardAlt: isDark ? 'bg-[#251A2C]/40 backdrop-blur-md' : 'bg-white/30 backdrop-blur-md',
    input: isDark ? 'bg-black/20 border-white/10 focus:border-white/30 text-white placeholder-white/30' : 'bg-white/50 border-black/10 focus:border-black/30 text-slate-900 placeholder-slate-400',
    btnPrimary: isDark ? 'bg-white text-[#2B2132] hover:bg-[#F2E8F7] shadow-lg shadow-white/5' : 'bg-[#463550] text-white hover:bg-[#2B2132] shadow-lg shadow-black/10',
    btnDisabled: isDark ? 'bg-black/20 text-white/30' : 'bg-black/5 text-black/30',
    highlight: isDark ? 'bg-purple-500/10 border-purple-500/20 text-purple-300' : 'bg-purple-50 border-purple-200 text-purple-700',
    plotText: isDark ? '#CDBAD9' : '#475569',
    plotGrid: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
    plotZero: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)',
    plotLineMain: isDark ? '#ffffff' : '#463550',
    plotLineSub: isDark ? '#A390B0' : '#E2D4E8',
    plotLineBase: isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
  };

  return (
    <div className={`min-h-screen ${theme.bg} ${theme.textMain} selection:bg-blue-500/30 transition-colors duration-500 relative`}>
      
      <SignalConvergence 
        phase={syncPhase} 
        duration={parseFloat(duration) || 0.04} 
        driftBounds={parseFloat(detMax) || 2.0} 
        isDark={isDark} 
      />

      <div className="relative z-10 flex flex-col h-full min-h-screen">
        {/* Top Navbar */}
        <nav className={`sticky top-0 z-50 transition-colors duration-300 ${theme.nav}`}>
        <div className="w-full max-w-[1536px] mx-auto px-8 h-14 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`w-3.5 h-3.5 rounded-full ${isDark ? 'bg-zinc-100 shadow-[0_0_15px_rgba(255,255,255,0.8)]' : 'bg-slate-900 shadow-[0_0_15px_rgba(0,0,0,0.4)]'}`} />
            <span className={`text-lg font-bold tracking-tight ${theme.textMain}`}>AutoPulseSynth</span>
          </div>
          <div className="flex items-center space-x-6">
            <a href="https://github.com/HABER7789/AutoPulseSynth" target="_blank" rel="noreferrer" className={`text-sm font-semibold ${theme.textMuted} hover:${theme.textMain} transition-colors`}>Documentation</a>
            <span className={`px-2.5 py-1 ${theme.cardAlt} border ${theme.border} rounded-md text-xs font-bold ${theme.textMuted}`}>v2.0.0</span>
            <button 
              onClick={() => setIsDark(!isDark)} 
              className={`p-2 rounded-full transition-colors ${isDark ? 'hover:bg-zinc-900 text-zinc-400 hover:text-white' : 'hover:bg-slate-200 text-slate-500 hover:text-black'}`}
              title="Toggle Theme"
            >
              {isDark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Help Modal */}
      {showHelp && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm transition-opacity">
          <div className={`${theme.card} border ${theme.border} rounded-2xl p-8 max-w-lg w-full relative shadow-2xl`}>
            <button 
              onClick={() => setShowHelp(false)} 
              className="absolute top-5 right-5 p-2 rounded-full hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
            >
              <X size={20} className={theme.textMain} />
            </button>
            <div className="flex items-center mb-6">
              <Info className={`mr-3 ${theme.textMain}`} size={24} />
              <h3 className={`text-xl font-bold ${theme.textMain}`}>How it works</h3>
            </div>
            <ul className={`text-[13px] font-medium space-y-4 leading-relaxed ${theme.textMuted}`}>
              <li><strong className={theme.textMain}>1. Target Gate</strong>: Select the quantum operation (e.g. $\pi$-pulse) to execute on the target physical qubit.</li>
              <li><strong className={theme.textMain}>2. Duration</strong>: The operational time window (e.g. 40ns) for the gate. Pushing this below hardware limits (&lt;20ns) risks significant leakage to non-computational states due to the massive required driving amplitude $\Omega(t)$.</li>
              <li><strong className={theme.textMain}>3. Drift Bounds (± MHz)</strong>: The estimated symmetric frequency drift from charge noise / TLS defects. The optimizer finds a DRAG envelope that maximizes worst-case fidelity across this entire detuning window.</li>
              <li><strong className={theme.textMain}>4. Hardware Output</strong>: The output plot represents the exact digital array needed by the lab's Arbitrary Waveform Generator (AWG) to synthesize and IQ-mix the microwave burst sent down the dilution refrigerator.</li>
            </ul>
            <div className={`mt-6 pt-4 border-t ${theme.border}`}>
              <h4 className={`text-[12px] font-bold uppercase tracking-wider mb-3 ${theme.textMain}`}>Typical Lab Parameters</h4>
              <div className={`text-[12px] font-mono space-y-1.5 ${theme.textMuted}`}>
                <div className="flex justify-between"><span>Standard (IBM/Google)</span><span>0.04 µs, ±2 MHz</span></div>
                <div className="flex justify-between"><span>Aggressive</span><span>0.02 µs, ±1 MHz</span></div>
                <div className="flex justify-between"><span>Conservative</span><span>0.10 µs, ±3 MHz</span></div>
                <div className="flex justify-between"><span>Stress test</span><span>0.01 µs, ±5 MHz</span></div>
              </div>
            </div>
          </div>
        </div>
      )}

      <main className="w-full max-w-[1536px] mx-auto px-6 lg:px-8 py-2 min-h-[calc(100vh-56px)] lg:h-[calc(100vh-56px)] flex flex-col pt-3 lg:pt-4">
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-16 flex-1 min-h-0">
          
          {/* Left Column: Header, Input & Context */}
          <div className="lg:col-span-4 flex flex-col space-y-4 overflow-y-auto pr-4 pb-4 hide-scrollbar min-h-0">
            
            {/* Header Section */}
            <div className="shrink-0 mb-1">
              <h1 className="text-4xl lg:text-[42px] font-extrabold tracking-tighter mb-3 leading-[1.05]">Quantum Control <br className="hidden xl:block" /> Optimization.</h1>
              <p className={`text-[13px] font-medium leading-relaxed ${theme.textMuted}`}>
                A production-grade ML pipeline that synthesizes hardware-resilient microwave pulses. 
                Replace static hit-and-trial calibration with dynamic, surrogate-assisted optimization.
              </p>
            </div>

            {/* Instruction Tab / Toggle */}
            <button 
              type="button"
              onClick={() => setShowHelp(true)}
              className={`flex items-center justify-between w-full p-3.5 rounded-xl border ${theme.cardAlt} ${theme.border} transition-colors duration-300 hover:opacity-80 shrink-0`}
            >
              <div className="flex items-center">
                <Info size={18} className={`mr-3 ${theme.textMain}`} />
                <span className={`text-[13px] font-bold ${theme.textMain}`}>How it works</span>
              </div>
              <ChevronRight size={18} className={theme.textSubtle} />
            </button>

            {/* Form */}
            <form onSubmit={handleSynthesize} className="space-y-4">
              <div className={`space-y-4 ${theme.card} border ${theme.border} p-5 rounded-xl transition-colors duration-300`}>
                <div>
                  <label className={`block text-[11px] font-bold mb-2 uppercase tracking-widest ${theme.textMuted}`}>Target Gate</label>
                  <select 
                    value={gate}
                    onChange={(e) => setGate(e.target.value)}
                    className={`w-full font-medium rounded-md px-3 py-2 text-sm transition-colors appearance-none border focus:outline-none ${theme.input}`}
                  >
                    <option value="X">X Gate (Pi Pulse)</option>
                    <option value="SX">SX Gate (Pi/2 Pulse)</option>
                  </select>
                </div>

                <div>
                  <label className={`block text-[11px] font-bold mb-2 uppercase tracking-widest ${theme.textMuted}`}>Duration (µs)</label>
                  <div className={`flex items-center w-full rounded-md border transition-colors ${theme.input}`}>
                    <button type="button" onClick={() => { setDuration(Math.max(0.01, parseFloat(duration) - 0.01).toFixed(2)); setDismissWarning(false); }} className={`px-4 py-2 font-bold ${theme.textMuted} hover:${theme.textMain}`}>-</button>
                    <input 
                      type="number" 
                      step="0.01" min="0.01" max="1.0"
                      value={duration}
                      onChange={(e) => { setDuration(e.target.value); setDismissWarning(false); }}
                      className="w-full text-center bg-transparent border-none focus:outline-none text-sm font-semibold [&::-webkit-inner-spin-button]:appearance-none"
                      style={{ MozAppearance: 'textfield' }}
                    />
                    <button type="button" onClick={() => { setDuration(Math.min(1.0, parseFloat(duration) + 0.01).toFixed(2)); setDismissWarning(false); }} className={`px-4 py-2 font-bold ${theme.textMuted} hover:${theme.textMain}`}>+</button>
                  </div>
                </div>

                <div>
                  <label className={`block text-[11px] font-bold mb-2 uppercase tracking-widest ${theme.textMuted}`}>Drift Bounds (± MHz)</label>
                  <div className={`flex items-center w-full rounded-md border transition-colors ${theme.input}`}>
                    <button type="button" onClick={() => { setDetMax(Math.max(0.0, parseFloat(detMax) - 0.5).toFixed(1)); setDismissWarning(false); }} className={`px-4 py-2 font-bold ${theme.textMuted} hover:${theme.textMain}`}>-</button>
                    <input 
                      type="number" 
                      step="0.5" min="0.0" max="20.0"
                      value={detMax}
                      onChange={(e) => { setDetMax(e.target.value); setDismissWarning(false); }}
                      className="w-full text-center bg-transparent border-none focus:outline-none text-sm font-semibold [&::-webkit-inner-spin-button]:appearance-none"
                      style={{ MozAppearance: 'textfield' }}
                    />
                    <button type="button" onClick={() => { setDetMax(Math.min(20.0, parseFloat(detMax) + 0.5).toFixed(1)); setDismissWarning(false); }} className={`px-4 py-2 font-bold ${theme.textMuted} hover:${theme.textMain}`}>+</button>
                  </div>
                </div>
                
                <div className={`pt-2 border-t ${theme.border}`}>
                  <label className={`block text-[11px] font-bold mb-2 uppercase tracking-widest flex items-center justify-between ${theme.textMuted}`}>
                    <span>Q-CTRL API Key</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${isDark ? 'bg-zinc-900 border-zinc-800 text-zinc-500' : 'bg-slate-100 border-slate-200 text-slate-500'}`}>Optional</span>
                  </label>
                  {isLocal ? (
                    <input 
                      type="password" 
                      placeholder="Enter key for BO validation..."
                      value={boKey}
                      onChange={(e) => setBoKey(e.target.value)}
                      className={`w-full rounded-md px-3 py-2 text-sm font-medium transition-colors border focus:outline-none ${theme.input}`}
                    />
                  ) : (
                    <div className={`w-full rounded-md px-3 py-2 text-[11px] font-medium border ${isDark ? 'bg-zinc-900/50 border-zinc-800 text-zinc-500' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                      Boulder Opal cross-validation requires OAuth and is available in local mode only. Clone the repo and run <code className="font-mono">./run.sh</code> to enable.
                    </div>
                  )}
                </div>
              </div>

              {isExtreme && !dismissWarning && (
                <div className={`relative flex flex-col p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-500 transition-all duration-300 animate-in fade-in slide-in-from-top-2`}>
                  <button 
                    type="button" 
                    onClick={() => setDismissWarning(true)}
                    className="absolute top-3 right-3 opacity-60 hover:opacity-100 transition-opacity"
                  >
                    <X size={14} />
                  </button>
                  <div className="flex items-center mb-2">
                    <Info size={16} className="mr-2 shrink-0" />
                    <h4 className="text-[12px] font-bold uppercase tracking-wider">Physical Hardware Limit</h4>
                  </div>
                  <p className="text-[11px] font-medium leading-relaxed opacity-90 pl-6">
                    You have crossed typical superconducting limits (duration &lt; 20ns or drift &gt; 10 MHz). 
                    AWG electronics lack the sampling rate to shape pulses this fast, and such massive drift boundaries require unfeasible control amplitudes (driving leakage to higher energy states). You are now in theoretical stress-testing territory.
                  </p>
                </div>
              )}

              <div className="flex gap-2">
                <button 
                  type="submit" 
                  disabled={loading}
                  className={`flex-1 flex items-center justify-center py-2.5 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all ${
                    loading ? theme.btnDisabled + ' cursor-not-allowed' : theme.btnPrimary + ' active:scale-[0.98]'
                  }`}
                >
                  {loading ? (
                    <span className="flex items-center">
                      <svg className={`animate-spin -ml-1 mr-2 h-4 w-4 ${theme.textSubtle}`} fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Synthesizing...
                    </span>
                  ) : (
                    <span className="flex items-center">
                      <Play size={12} className="mr-1.5 fill-current" /> Full Run
                    </span>
                  )}
                </button>

                <button 
                  type="button"
                  disabled={loading}
                  onClick={(e) => handleSynthesize(e, true)}
                  className={`flex-1 flex items-center justify-center py-2.5 rounded-md text-[11px] font-semibold uppercase tracking-wider transition-all ${
                    loading ? theme.btnDisabled + ' cursor-not-allowed' : (isDark ? 'bg-white/5 text-white/60 hover:bg-white/10 border border-white/10' : 'bg-black/5 text-black/50 hover:bg-black/10 border border-black/10') + ' active:scale-[0.98]'
                  }`}
                >
                  <Play size={12} className="mr-1.5 fill-current" /> Quick Demo
                </button>
              </div>
            </form>

          </div>

          {/* Right Column: Visualization Display */}
          <div className="lg:col-span-8 flex flex-col space-y-4 min-h-[500px] lg:min-h-0">
            
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 flex items-start text-red-600 dark:text-red-400 shrink-0">
                <p className="text-xs font-mono">{error}</p>
              </div>
            )}
            
            {results && results.plot_data.bo_error && (
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 flex items-start text-amber-600 dark:text-amber-500 shrink-0">
                <p className="text-xs font-mono"><strong>Q-CTRL API Error:</strong> {results.plot_data.bo_error}</p>
              </div>
            )}

            {!results && !error && (
               <div className={`flex-grow flex flex-col border border-dashed rounded-xl h-full transition-colors duration-300 ${theme.border} ${theme.cardAlt}`}>
                  {loading && streamEvents.length > 0 ? (
                    <div className="flex flex-col h-full">
                      <div className={`flex items-center justify-between px-4 py-2.5 border-b ${theme.border}`}>
                        <div className="flex items-center space-x-2">
                          <span className={`w-2 h-2 rounded-full animate-pulse ${isDark ? 'bg-emerald-400' : 'bg-emerald-500'}`}></span>
                          <span className={`text-[11px] font-bold uppercase tracking-wider ${theme.textMain}`}>Computation Log</span>
                        </div>
                        <span className={`text-[11px] font-mono ${theme.textMuted}`}>{elapsedTime.toFixed(1)}s</span>
                      </div>
                      <div ref={logRef} className="flex-1 overflow-y-auto p-4 space-y-3 hide-scrollbar">
                        {streamEvents.map((evt, i) => (
                          <StreamLogEntry key={i} evt={evt} isDark={isDark} theme={theme} />
                        ))}
                      </div>
                    </div>
                  ) : loading ? (
                    <div className="flex-grow flex flex-col items-center justify-center p-8">
                      <div className="flex items-center justify-center space-x-1.5 mb-6 h-12">
                        {[0, 1, 2, 3, 4, 5, 6].map(i => (
                          <div 
                             key={i}
                             className={`w-1.5 ${isDark ? 'bg-zinc-100' : 'bg-slate-900'} rounded-full animate-wave`}
                             style={{ animationDelay: `${i * 0.15}s` }}
                          ></div>
                        ))}
                      </div>
                      <h3 className={`text-sm font-medium ${theme.textMain} mb-2 animate-pulse`}>Connecting to engine...</h3>
                    </div>
                  ) : (
                    <div className="flex-grow flex flex-col items-center justify-center p-8">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-4 border ${isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-slate-200 shadow-sm'}`}>
                        <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${isDark ? 'bg-zinc-500' : 'bg-slate-400'}`}></span>
                      </div>
                      <h3 className={`text-sm font-medium mb-1 ${theme.textMuted}`}>Engine Standby</h3>
                      <p className={`text-xs max-w-xs text-center ${theme.textSubtle}`}>
                        Awaiting hardware parameters to generate the waveform and robustness matrices.
                      </p>
                    </div>
                  )}
               </div>
            )}

            {results && !error && (
              <div className={`flex flex-col space-y-4 h-full transition-opacity duration-500 ${loading ? 'opacity-30 pointer-events-none' : 'opacity-100'}`}>
                
                {results.baseline_comparison?.used_baseline_fallback && (
                  <div className={`shrink-0 flex items-start px-4 py-3 rounded-xl border ${isDark ? 'bg-amber-500/10 border-amber-500/20 text-amber-500' : 'bg-amber-50 border-amber-200 text-amber-700'}`}>
                    <div className="mr-3 mt-0.5">
                      <AlertTriangle size={16} />
                    </div>
                    <div>
                      <h4 className="text-[12px] font-bold uppercase tracking-wider mb-0.5">Safeguard Triggered: Baseline Fallback</h4>
                      <p className="text-[11px] font-medium opacity-90 leading-relaxed">
                        The surrogate model (R²={results.metrics.r2.toFixed(3)}) was insufficiently accurate for this parameter space to beat a calibrated analytical pulse. As a safeguard, the pipeline automatically fell back to the gate-aware analytical baseline to ensure optimal fidelity.
                      </p>
                    </div>
                  </div>
                )}

                {/* Minimal Metrics Row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 shrink-0">
                  <div className={`${theme.card} border ${theme.border} rounded-xl p-5 flex flex-col justify-between transition-colors duration-300`}>
                    <div className="flex justify-between items-center mb-3">
                      <p className={`text-[11px] font-bold uppercase tracking-widest ${theme.textMuted}`}>Mean Fidelity</p>
                      <CheckCircle2 size={16} className="text-emerald-500" />
                    </div>
                    <p className="text-[38px] font-bold tracking-tight">
                      {(results.verification.f_mean * 100).toFixed(2)}<span className={`text-xl font-bold ml-1 ${theme.textMuted}`}>%</span>
                    </p>
                  </div>
                  <div className={`${theme.card} border ${theme.border} rounded-xl p-5 flex flex-col justify-between transition-colors duration-300`}>
                    <div className="flex justify-between items-center mb-3">
                      <p className={`text-[11px] font-bold uppercase tracking-widest ${theme.textMuted}`}>Worst Case Bounds</p>
                    </div>
                    <p className="text-[38px] font-bold tracking-tight">
                      {(results.verification.f_worst * 100).toFixed(2)}<span className={`text-xl font-bold ml-1 ${theme.textMuted}`}>%</span>
                    </p>
                  </div>
                  <div className={`${theme.card} border ${theme.border} rounded-xl p-5 flex flex-col justify-between transition-colors duration-300`}>
                    <div className="flex justify-between items-center mb-3">
                      <p className={`text-[11px] font-bold uppercase tracking-widest ${theme.textMuted}`}>Surrogate R² Score</p>
                    </div>
                    <p className="text-[38px] font-bold tracking-tight">
                      {results.metrics.r2.toFixed(3)}
                    </p>
                  </div>
                </div>

                {/* Abstract Charts Area */}
                <div className={`flex-1 min-h-0 flex flex-col ${theme.card} border ${theme.border} rounded-xl overflow-hidden p-2 transition-colors duration-300`}>
                  
                  {/* Robustness Plot */}
                  <div className={`flex-1 min-h-[160px] w-full relative border-b ${theme.border}`}>
                    {Plot && (
                      <Plot
                        data={[
                          {
                            x: results.plot_data.detunings_mhz,
                            y: results.plot_data.fidelities_baseline,
                            type: 'scatter',
                            mode: 'lines',
                            line: {color: theme.plotLineBase, width: 2, dash: 'dot', shape: 'spline'},
                            name: 'Unoptimized Baseline',
                            hovertemplate: '%{x:.2f} MHz<br>%{y:.4f}<extra></extra>'
                          },
                          {
                            x: results.plot_data.detunings_mhz,
                            y: results.plot_data.fidelities,
                            type: 'scatter',
                            mode: 'lines+markers',
                            marker: {color: theme.plotLineMain, size: 4},
                            line: {color: theme.plotLineSub, width: 2, shape: 'spline'},
                            name: 'ML Synthesized',
                            hovertemplate: '%{x:.2f} MHz<br>%{y:.4f}<extra></extra>'
                          },
                          ...(results.plot_data.bo_fidelities ? [{
                            x: results.plot_data.detunings_mhz,
                            y: results.plot_data.bo_fidelities,
                            type: 'scatter',
                            mode: 'lines',
                            line: {color: '#3b82f6', width: 2, shape: 'spline'},
                            name: 'Boulder Opal Validation',
                            hovertemplate: '%{x:.2f} MHz<br>%{y:.4f}<extra></extra>'
                          }] : [])
                        ] as any[]}
                        layout={{
                          autosize: true,
                          margin: { l: 40, r: 40, t: 40, b: 40 },
                          paper_bgcolor: 'transparent',
                          plot_bgcolor: 'transparent',
                          title: {
                              text: 'Stability Across Calibration Drift',
                              font: { color: theme.plotText, size: 11, family: 'sans-serif', weight: 'normal' },
                              x: 0.05
                          },
                          xaxis: {
                            title: { text: '', font: { color: theme.plotText, size: 10 } },
                            gridcolor: theme.plotGrid,
                            zerolinecolor: theme.plotZero,
                            tickfont: { color: theme.plotText, size: 10 },
                            range: [Math.min(...results.plot_data.detunings_mhz) * 1.05, Math.max(...results.plot_data.detunings_mhz) * 1.05]
                          },
                          yaxis: {
                            title: { text: '', font: { color: theme.plotText, size: 10 } },
                            gridcolor: theme.plotGrid,
                            range: [0, 1.05],
                            tickfont: { color: theme.plotText, size: 10 }
                          },
                          hovermode: 'x unified',
                          showlegend: true,
                          legend: {
                           orientation: 'h',
                           yanchor: 'bottom',
                           y: 1.02,
                           xanchor: 'right',
                           x: 1,
                           font: { color: theme.plotText, size: 10 }
                         }
                        }}
                        style={{width: '100%', height: '100%'}}
                        useResizeHandler={true}
                        config={{displayModeBar: false}}
                      />
                    )}
                  </div>

                  {/* AWG Waveform Plot */}
                  <div className="h-[180px] w-full relative pt-2 shrink-0">
                    {Plot && (
                       <Plot
                       data={[
                         {
                           x: results.plot_data.time_ns,
                           y: results.plot_data.i_wave,
                           type: 'scatter',
                           mode: 'lines',
                           line: {color: theme.plotLineMain, width: 1.5, shape: 'spline'},
                           name: 'I (In-phase)',
                           fill: 'tozeroy',
                           fillcolor: isDark ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.03)'
                         },
                         {
                           x: results.plot_data.time_ns,
                           y: results.plot_data.q_wave,
                           type: 'scatter',
                           mode: 'lines',
                           line: {color: theme.plotLineSub, width: 1.5, shape: 'spline'},
                           name: 'Q (Quadrature)'
                         }
                       ] as any[]}
                       layout={{
                         autosize: true,
                         margin: { l: 40, r: 40, t: 40, b: 40 },
                         paper_bgcolor: 'transparent',
                         plot_bgcolor: 'transparent',
                         title: {
                             text: 'AWG Microwave Control (DRAG Envelopes)',
                             font: { color: theme.plotText, size: 11, family: 'sans-serif', weight: 'normal' },
                             x: 0.05
                         },
                         xaxis: {
                           title: { text: '', font: { color: theme.plotText, size: 10 } },
                           gridcolor: theme.plotGrid,
                           zerolinecolor: theme.plotZero,
                           tickfont: { color: theme.plotText, size: 10 },
                           range: [0, results.plot_data.time_ns[results.plot_data.time_ns.length - 1] * 1.05]
                         },
                         yaxis: {
                           title: { text: '', font: { color: theme.plotText, size: 10 } },
                           gridcolor: theme.plotGrid,
                           zerolinecolor: theme.plotZero,
                           tickfont: { color: theme.plotText, size: 10 }
                         },
                         legend: {
                           orientation: 'h',
                           yanchor: 'bottom',
                           y: 1.02,
                           xanchor: 'right',
                           x: 1,
                           font: { color: theme.plotText, size: 10 }
                         },
                         hovermode: 'x unified'
                       }}
                       style={{width: '100%', height: '100%'}}
                       useResizeHandler={true}
                       config={{displayModeBar: false}}
                     />
                    )}
                  </div>
                </div>

              </div>
            )}
            
          </div>
        </div>
      </main>
      </div>
    </div>
  );
}
