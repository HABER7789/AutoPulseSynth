# Screenshot Instructions for README

## Quick Setup (5 minutes total)

### Screenshot 1: CLI Synthesis Command + Output

**Run this command in terminal:**
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

**What to capture:**
- The command itself (make sure it's visible)
- The full output showing:
  - "Synthesizing X pulse..."
  - "Training surrogate..."
  - "R2: 0.90, MAE: 0.042"
  - **"RESULT: Mean Fidelity = 0.9849 | Worst Case = 0.9685"**
  - "Saved results to demo_pulse.json"

**Screenshot settings:**
- Terminal: Dark theme, 14pt font
- Crop to show just the relevant output (no extra whitespace)
- Save as: `docs/images/01_synthesis_output.png`

---

### Screenshot 2: Analysis Command + Metrics

**Run this command:**
```bash
python -m autopulsesynth.cli analyze --input demo_pulse.json
```

**What to capture:**
- The command
- Output showing:
  - "Analysis of demo_pulse.json"
  - "Gate: X"
  - "Duration: 4e-08 s"
  - "Optimization R2: 0.90"
  - "Verification Metrics:"
  - "  Mean Fidelity: 0.9849"
  - "  Worst Fidelity: 0.9685"

**Screenshot settings:**
- Same terminal theme
- Save as: `docs/images/02_analysis_output.png`

---

### Screenshot 3: Robustness Plot

**Run this command:**
```bash
python scripts/plot_robustness.py --input demo_pulse.json
```

**What happens:**
- Generates `robustness_plot.png` in current directory
- Shows fidelity vs detuning curve (±20 MHz sweep)
- Blue line = optimized pulse (flat plateau)
- Red dashed = standard Gaussian (steep drop-off)

**What to do:**
1. Open `robustness_plot.png`
2. Save a copy as: `docs/images/03_robustness_plot.png`
3. Or just move it: `mv robustness_plot.png docs/images/03_robustness_plot.png`

**No editing needed** - the plot is already publication-ready.

---

## File Organization

Create the images directory:
```bash
mkdir -p docs/images
```

Your final structure:
```
docs/
├── images/
│   ├── 01_synthesis_output.png
│   ├── 02_analysis_output.png
│   └── 03_robustness_plot.png
├── CURRENT_STATUS.md
├── ROADMAP.md
└── ...
```

---

## Alternative: Use Existing Results

If you've already run these commands and have `results_2mhz.json` or `screenshot_demo.json`:

**For Screenshot 2:**
```bash
python -m autopulsesynth.cli analyze --input results_2mhz.json
```

**For Screenshot 3:**
```bash
python scripts/plot_robustness.py --input results_2mhz.json
```

---

## Tips for Good Screenshots

### Terminal Screenshots (Mac):
1. **Open Terminal** → Set to "Pro" or "Dracula" theme
2. **Increase font size:** Cmd+Plus a few times
3. **Run command** and wait for output
4. **Take screenshot:**
   - Cmd+Shift+4, then Space, click terminal window (auto-crops)
   - Or: Cmd+Shift+4, drag to select region

### Terminal Screenshots (Linux):
- Use `gnome-screenshot -a` or Flameshot
- Or: Screenshot tool in your DE

### Terminal Screenshots (Windows):
- Use Snipping Tool or Win+Shift+S
- PowerShell or WSL terminal with dark theme

### Plot Screenshot:
- Open `robustness_plot.png` in Preview/Image Viewer
- It's already a PNG, just copy to docs/images/
- No screenshot needed, it's already an image file!

---

## Verification Checklist

Before committing:
- [ ] All 3 images exist in `docs/images/`
- [ ] Images are PNG format
- [ ] File sizes reasonable (<500KB each)
- [ ] Terminal screenshots show command + full output
- [ ] Text in screenshots is readable (not too small)
- [ ] Plot shows both curves (blue = optimized, red = standard)

---

## Quick One-Liner (After running synthesis)

```bash
# Create directory and generate all needed outputs
mkdir -p docs/images && \
python -m autopulsesynth.cli analyze --input screenshot_demo.json && \
python scripts/plot_robustness.py --input screenshot_demo.json && \
mv robustness_plot.png docs/images/03_robustness_plot.png && \
echo "Now take screenshots of terminal output for images 01 and 02"
```

Then manually screenshot the terminal for the first two images.

---

**Estimated Time:** 5 minutes total (2 min for commands, 3 min for screenshots)
