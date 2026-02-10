# AutoPulseSynth: Robust Quantum Control

**A surrogate-assisted optimization framework for superconducting qubit pulses.**

AutoPulseSynth creates control pulses that remain high-fidelity ($>99\%$) even when your quantum hardware drifts. It uses machine learning to find "robust" islands in the control landscape.

---

## 🚀 Quick Start

### 1. Installation
```bash
pip install -e .
```

### 2. Synthesize a Robust Pulse
Generate an X-gate pulse robust to $\pm 10$ MHz frequency drift.
```bash
autopulsesynth synthesize \
    --gate X \
    --duration 40e-9 \
    --t1 15e-6 \
    --det-max-hz 10e6 \
    --det-min-hz -10e6 \
    --out my_pulse.json
```
*(Runtime: ~2 minutes)*

### 3. Verify Physics
Check that the pulse performs a correct rotation at resonance.
```bash
python scripts/verify_pulse.py my_pulse.json
```
*Look for: Fidelity > 0.99, Angle ~ 3.14 rad.*

### 4. Visualize
See the "V-curve" of robustness.
```bash
python scripts/plot_robustness.py --input my_pulse.json
```

---

## 📚 Documentation
For a complete explanation of the physics, the optimization algorithm, and the "Hallucination Fix" we implemented, see the **[Technical Report](docs/TECHNICAL_REPORT.md)**.

## 📂 Project Structure
*   `autopulsesynth/`: Core package (Physics model, pulse definitions, optimizer).
*   `scripts/`: Verification and plotting tools.
*   `tests/`: Unit tests for physics validation.
*   `docs/`: Detailed documentation.

---
*Built for the Advanced Agentic Coding Challenge.*