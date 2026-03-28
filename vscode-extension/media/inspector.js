(function () {
    // ── VS Code API ──────────────────────────────────────────────
    const vscode = acquireVsCodeApi();
    const debugOutput = document.getElementById('debug-output');

    function log(msg) {
        debugOutput.textContent += msg + '\n';
    }

    // Tell the extension we're ready to receive data
    vscode.postMessage({ type: 'ready' });

    // ── Listen for messages from the extension ───────────────────
    window.addEventListener('message', event => {
        const msg = event.data;
        if (msg.type === 'update') {
            try {
                const data = JSON.parse(msg.text);
                renderAll(data);
            } catch (e) {
                log('Parse error: ' + e.message);
            }
        } else if (msg.type === 'status') {
            document.getElementById('status-bar').textContent = msg.text;
            log(msg.text);
        }
    });

    // ── Re-optimize button ───────────────────────────────────────
    document.getElementById('btn-reoptimize').addEventListener('click', () => {
        const gate = document.getElementById('val-gate').textContent || 'X';
        log('Requesting re-optimization for gate: ' + gate);
        vscode.postMessage({ type: 'reoptimize', gate: gate });
    });

    // ── Quil-T toggle (collapsible) ────────────────────────────
    document.getElementById('circuit-toggle').addEventListener('click', function () {
        const code = document.getElementById('quilt-code');
        const isCollapsed = code.classList.toggle('collapsed');
        this.textContent = isCollapsed
            ? '▸ Quil-T Hardware Program (click to expand)'
            : '▾ Quil-T Hardware Program (click to collapse)';
    });

    // ── Main render function ─────────────────────────────────────
    function renderAll(data) {
        debugOutput.textContent = '';
        log('Loaded pulse data successfully');

        // Extract fields (handles both direct API response and saved format)
        const gate = data.args?.gate || data.gate || 'X';
        const verification = data.verification || {};
        const metrics = data.metrics || {};
        const plotData = data.plot_data || {};
        const baseline = data.baseline_comparison || {};
        const params = data.optimized_params || [];

        // ── Metrics cards ─────────────────────────────────────────
        setText('val-gate', gate);
        setText('val-fmean', fmtPct(verification.f_mean));
        setText('val-fworst', fmtPct(verification.f_worst));
        setText('val-r2', metrics.r2 != null ? metrics.r2.toFixed(4) : '—');
        setText('val-fallback', baseline.used_baseline_fallback ? 'YES' : 'No');

        // Color the worst fidelity card
        const fWorst = verification.f_worst;
        const cardWorst = document.getElementById('card-fworst');
        if (fWorst != null) {
            cardWorst.className = 'metric-card ' + (fWorst >= 0.99 ? 'good' : fWorst >= 0.90 ? 'ok' : 'bad');
        }

        // ── Parameters panel ──────────────────────────────────────
        const paramNames = ['Amplitude (rad/s)', 'Center t₀ (s)', 'Sigma σ (s)', 'Phase φ (rad)', 'DRAG β'];
        let paramText = '';
        params.forEach((p, i) => {
            paramText += (paramNames[i] || `param[${i}]`) + ': ' + formatParam(p, i) + '\n';
        });
        if (verification.f_mean != null) {
            paramText += '\n── Verification ──\n';
            paramText += 'Mean fidelity:  ' + fmtPct(verification.f_mean) + '\n';
            paramText += 'Worst fidelity: ' + fmtPct(verification.f_worst) + '\n';
            paramText += 'Std deviation:  ' + (verification.f_std != null ? verification.f_std.toFixed(6) : '—') + '\n';
        }
        document.getElementById('params-text').textContent = paramText;

        // ── Quil-T circuit inspection ────────────────────────────
        const quiltEl = document.getElementById('quilt-code');
        const summaryEl = document.getElementById('circuit-summary');
        if (data.quilt_program) {
            quiltEl.innerHTML = highlightQuilt(cleanUpQuilt(data.quilt_program));

            // Count IQ samples from raw program
            var sampleCount = 0;
            data.quilt_program.split('\n').forEach(function (l) {
                var t = l.trim();
                if (t.match(/^[\d.-]+[+-][\d.]+i,/)) {
                    sampleCount = t.split(',').filter(Boolean).length;
                }
            });

            summaryEl.innerHTML =
                '<b>What this program does:</b> ' +
                'Defines a custom <b>' + gate + '</b> gate calibration for qubit 0. ' +
                'The <code>DEFWAVEFORM</code> contains ' + sampleCount + ' IQ samples — ' +
                'the ML-optimized microwave envelope loaded into the AWG. ' +
                '<code>DEFCAL</code> overrides the default ' + gate + ' gate with this custom pulse. ' +
                'When <code>' + gate + ' 0</code> runs, the hardware plays our waveform instead of the factory default.';
            log('Quil-T program loaded (' + data.quilt_program.split('\n').length + ' lines, ' + sampleCount + ' IQ samples)');
        } else {
            quiltEl.textContent = 'No Quil-T program in this file.\nRe-optimize to generate one.';
            summaryEl.textContent = '';
        }

        // ── Debug diagnostics ───────────────────────────────────
        if (baseline.used_baseline_fallback) {
            log('⚠ Baseline safeguard triggered — ML did not beat calibrated pulse');
            log('  Baseline worst: ' + fmtPct(baseline.baseline_f_worst) + '  (used as final)');
        } else {
            log('✓ ML-optimized pulse outperforms baseline');
            log('  ML worst:       ' + fmtPct(verification.f_worst));
            log('  Baseline worst: ' + fmtPct(baseline.baseline_f_worst));
            var improvement = verification.f_worst - baseline.baseline_f_worst;
            log('  Improvement:    +' + (improvement * 100).toFixed(2) + ' pp');
        }
        if (metrics.r2 != null) {
            log('Surrogate R²: ' + metrics.r2.toFixed(4) + (metrics.r2 < 0.5 ? ' (low — surrogate struggled)' : metrics.r2 < 0.8 ? ' (moderate)' : ' (good fit)'));
        }

        // ── Waveform chart (Canvas) ───────────────────────────────
        if (plotData.time_ns && plotData.i_wave) {
            drawWaveform(plotData.time_ns, plotData.i_wave, plotData.q_wave);
            log('Waveform: ' + plotData.time_ns.length + ' samples, ' +
                plotData.time_ns[plotData.time_ns.length - 1].toFixed(1) + ' ns');
        }

        // ── Fidelity chart (Canvas) ──────────────────────────────
        if (plotData.detunings_mhz && plotData.fidelities) {
            drawFidelity(plotData.detunings_mhz, plotData.fidelities, plotData.fidelities_baseline);
            log('Robustness scan: ' + plotData.detunings_mhz.length + ' detuning points');
        }
    }

    // ── Canvas drawing: Waveform ─────────────────────────────────
    function drawWaveform(time, iWave, qWave) {
        const canvas = document.getElementById('canvas-waveform');
        const ctx = canvas.getContext('2d');
        const W = canvas.width, H = canvas.height;
        const pad = { top: 20, right: 20, bottom: 40, left: 60 };

        ctx.clearRect(0, 0, W, H);
        ctx.fillStyle = 'rgba(0,0,0,0.15)';
        ctx.fillRect(0, 0, W, H);

        const plotW = W - pad.left - pad.right;
        const plotH = H - pad.top - pad.bottom;

        // Find Y range across both traces
        const allY = iWave.concat(qWave || []);
        let yMin = Math.min(...allY), yMax = Math.max(...allY);
        const yPad = (yMax - yMin) * 0.1 || 1;
        yMin -= yPad; yMax += yPad;

        const xMin = time[0], xMax = time[time.length - 1];

        function toX(v) { return pad.left + ((v - xMin) / (xMax - xMin)) * plotW; }
        function toY(v) { return pad.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH; }

        // Grid
        drawGrid(ctx, pad, plotW, plotH, xMin, xMax, yMin, yMax, toX, toY, 'Time (ns)', 'Rabi freq (rad/s)');

        // I-wave trace
        drawLine(ctx, time, iWave, toX, toY, '#007acc', 2);

        // Q-wave trace
        if (qWave) {
            drawLine(ctx, time, qWave, toX, toY, '#00bfff', 1.5, [5, 3]);
        }

        // Legend
        drawLegend(ctx, pad.left + 10, pad.top + 10, [
            { color: '#007acc', label: 'I (Ωx)', dash: false },
            { color: '#00bfff', label: 'Q (Ωy)', dash: true },
        ]);
    }

    // ── Canvas drawing: Fidelity ─────────────────────────────────
    function drawFidelity(detunings, fidsOpt, fidsBase) {
        const canvas = document.getElementById('canvas-fidelity');
        const ctx = canvas.getContext('2d');
        const W = canvas.width, H = canvas.height;
        const pad = { top: 20, right: 20, bottom: 40, left: 60 };

        ctx.clearRect(0, 0, W, H);
        ctx.fillStyle = 'rgba(0,0,0,0.15)';
        ctx.fillRect(0, 0, W, H);

        const plotW = W - pad.left - pad.right;
        const plotH = H - pad.top - pad.bottom;

        const allY = fidsOpt.concat(fidsBase || []);
        let yMin = Math.min(...allY), yMax = Math.max(...allY);
        const yPad = (yMax - yMin) * 0.1 || 0.01;
        yMin = Math.max(0, yMin - yPad); yMax = Math.min(1.0, yMax + yPad);

        const xMin = detunings[0], xMax = detunings[detunings.length - 1];

        function toX(v) { return pad.left + ((v - xMin) / (xMax - xMin)) * plotW; }
        function toY(v) { return pad.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH; }

        drawGrid(ctx, pad, plotW, plotH, xMin, xMax, yMin, yMax, toX, toY, 'Detuning (MHz)', 'Fidelity');

        // Optimized trace
        drawLine(ctx, detunings, fidsOpt, toX, toY, '#4caf50', 2.5);

        // Baseline trace
        if (fidsBase) {
            drawLine(ctx, detunings, fidsBase, toX, toY, '#ff5722', 1.5, [5, 3]);
        }

        drawLegend(ctx, pad.left + 10, pad.top + 10, [
            { color: '#4caf50', label: 'Optimized', dash: false },
            { color: '#ff5722', label: 'Baseline', dash: true },
        ]);
    }

    // ── Shared drawing helpers ────────────────────────────────────
    function drawLine(ctx, xs, ys, toX, toY, color, width, dash) {
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.setLineDash(dash || []);
        ctx.beginPath();
        for (let i = 0; i < xs.length; i++) {
            const px = toX(xs[i]), py = toY(ys[i]);
            i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
        }
        ctx.stroke();
        ctx.setLineDash([]);
    }

    function drawGrid(ctx, pad, plotW, plotH, xMin, xMax, yMin, yMax, toX, toY, xLabel, yLabel) {
        ctx.strokeStyle = 'rgba(255,255,255,0.08)';
        ctx.lineWidth = 1;
        // Horizontal grid lines
        for (let i = 0; i <= 4; i++) {
            const y = pad.top + (plotH * i / 4);
            ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + plotW, y); ctx.stroke();
            // Y label
            const val = yMax - (yMax - yMin) * (i / 4);
            ctx.fillStyle = '#888'; ctx.font = '10px monospace'; ctx.textAlign = 'right';
            ctx.fillText(formatAxis(val), pad.left - 6, y + 3);
        }
        // Vertical grid lines
        for (let i = 0; i <= 4; i++) {
            const x = pad.left + (plotW * i / 4);
            ctx.beginPath(); ctx.moveTo(x, pad.top); ctx.lineTo(x, pad.top + plotH); ctx.stroke();
            const val = xMin + (xMax - xMin) * (i / 4);
            ctx.fillStyle = '#888'; ctx.font = '10px monospace'; ctx.textAlign = 'center';
            ctx.fillText(formatAxis(val), x, pad.top + plotH + 16);
        }
        // Axis labels
        ctx.fillStyle = '#aaa'; ctx.font = '11px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText(xLabel, pad.left + plotW / 2, pad.top + plotH + 34);
        ctx.save();
        ctx.translate(14, pad.top + plotH / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText(yLabel, 0, 0);
        ctx.restore();
    }

    function drawLegend(ctx, x, y, items) {
        ctx.font = '11px sans-serif';
        items.forEach((item, i) => {
            const lx = x, ly = y + i * 18;
            ctx.strokeStyle = item.color;
            ctx.lineWidth = 2;
            ctx.setLineDash(item.dash ? [5, 3] : []);
            ctx.beginPath(); ctx.moveTo(lx, ly); ctx.lineTo(lx + 20, ly); ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = '#ccc';
            ctx.textAlign = 'left';
            ctx.fillText(item.label, lx + 26, ly + 4);
        });
    }

    // ── Formatting helpers ───────────────────────────────────────
    function setText(id, text) { document.getElementById(id).textContent = text; }

    function fmtPct(v) {
        if (v == null) return '—';
        return (v * 100).toFixed(2) + '%';
    }

    // Collapse the massive waveform sample line into a short summary
    function cleanUpQuilt(src) {
        return src.split('\n').map(function (line) {
            // The DEFWAVEFORM data line is extremely long (hundreds of IQ samples)
            // Collapse to: "    0.028+0.000i, 0.033-0.000i, ... (40 samples total)"
            var trimmed = line.trim();
            if (trimmed.match(/^[\d.-]+[+-][\d.]+i,/)) {
                var samples = trimmed.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
                var n = samples.length;
                if (n > 6) {
                    return '    ' + samples.slice(0, 3).join(', ') + ',  ...  ' +
                           samples.slice(-2).join(', ') +
                           '    ← ' + n + ' IQ samples';
                }
            }
            return line;
        }).join('\n');
    }

    function formatParam(val, idx) {
        if (idx === 0) return (val / 1e6).toFixed(2) + ' MHz';      // amplitude
        if (idx === 1 || idx === 2) return (val * 1e9).toFixed(2) + ' ns'; // time/sigma
        return val.toFixed(4);  // phase, beta
    }

    function formatAxis(v) {
        if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(1) + 'M';
        if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(1) + 'k';
        if (Math.abs(v) < 0.01 && v !== 0) return v.toExponential(1);
        return v.toFixed(2);
    }

    // ── Quil-T syntax highlighting ────────────────────────────
    // Tokenize each line FIRST on the raw text, then wrap tokens in spans.
    // This avoids the bug where regexes match inside our own HTML tags.
    function highlightQuilt(src) {
        return src.split('\n').map(function (line) {
            // Comments — entire line is green
            if (line.trimStart().startsWith('#')) {
                return '<span class="comment">' + esc(line) + '</span>';
            }

            // Tokenize the raw line into segments, then color each
            var tokens = [];
            var rest = line;

            // Pull out leading keyword if present
            var kwMatch = rest.match(/^(\s*)(DECLARE|DEFFRAME|DEFWAVEFORM|DEFCAL|PULSE|MEASURE)\b(.*)/);
            if (kwMatch) {
                tokens.push(esc(kwMatch[1]));  // whitespace
                tokens.push('<span class="kw">' + esc(kwMatch[2]) + '</span>');
                rest = kwMatch[3];
            }

            // Check if it's a bare gate line (e.g. "X 0", "SX 0")
            var gateMatch = rest.match(/^(\s*)(X|SX|Y|Z|H|RX|RZ)\b(.*)/);
            if (gateMatch && tokens.length === 0) {
                tokens.push(esc(gateMatch[1]));
                tokens.push('<span class="gate">' + esc(gateMatch[2]) + '</span>');
                rest = gateMatch[3];
            }

            // Highlight quoted strings in the remainder
            rest = esc(rest).replace(/&quot;([^&]*)&quot;/g, '<span class="str">"$1"</span>');
            // Since esc() turns " to plain " (it doesn't escape quotes), handle raw quotes:
            rest = rest.replace(/"([^"<]*)"/g, '<span class="str">"$1"</span>');

            tokens.push(rest);
            return tokens.join('');
        }).join('\n');
    }

    function esc(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}());
