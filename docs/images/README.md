# Screenshots Directory

This directory contains visual documentation for the README.

## Required Screenshots

### 1. `01_synthesis_output.png`
**Status:** ⚠️ **TODO - Take terminal screenshot**

**Command to run:**
```bash
python -m autopulsesynth.cli synthesize \
    --gate X \
    --duration 40e-9 \
    --t1 15e-6 \
    --det-max-hz 2e6 \
    --det-min-hz=-2e6 \
    --amp-error 0.05 \
    --out demo_pulse.json \
    --seed 42
```

**What to capture:** Terminal showing the command and full output ending with:
```
RESULT: Mean Fidelity = 0.98492 | Worst Case = 0.96845
Saved results to demo_pulse.json
```

**How to take:**
- Mac: Cmd+Shift+4, Space, click terminal window
- Linux: Flameshot or gnome-screenshot -a
- Windows: Win+Shift+S

---

### 2. `02_analysis_output.png`
**Status:** ⚠️ **TODO - Take terminal screenshot**

**Command to run:**
```bash
python -m autopulsesynth.cli analyze --input screenshot_demo.json
```

**What to capture:** Terminal showing:
```
Analysis of screenshot_demo.json
----------------------------------------
Gate: X
Duration: 4e-08 s
Optimization R2: 0.8998
Verification Metrics:
  Mean Fidelity: 0.98492
  Worst Fidelity: 0.96845
```

---

### 3. `03_robustness_plot.png`
**Status:** ✅ **DONE** (auto-generated)

This is the output from `scripts/plot_robustness.py` showing:
- Blue line: Optimized pulse (flat plateau across ±20 MHz)
- Red dashed: Standard Gaussian (sharp degradation)

**No action needed** - file is already in place.

---

## Instructions

See [SCREENSHOT_INSTRUCTIONS.md](../SCREENSHOT_INSTRUCTIONS.md) for detailed steps.

**Quick setup (5 minutes):**
1. Run the synthesis command (90 seconds)
2. Screenshot terminal → save as `01_synthesis_output.png`
3. Run the analysis command
4. Screenshot terminal → save as `02_analysis_output.png`
5. Image 3 is already generated!

---

## Image Specifications

- Format: PNG
- Max size: 500KB recommended
- Terminal screenshots: Dark theme, 14-16pt font, readable text
- Plot: Already optimized (no changes needed)
