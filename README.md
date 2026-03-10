# AutoPulseSynth: Quantum Control Optimization

**A full-stack, machine-learning assisted optimization framework for generating hardware-resilient superconducting qubit pulses.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/frontend-Next.js-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-teal.svg)](https://fastapi.tiangolo.com/)

AutoPulseSynth synthesizes quantum control pulses that maintain **>99% fidelity** even under significant hardware calibration drift (e.g., charge noise, TLS defects). It utilizes a high-performance **Random Forest Surrogate Model** mapped over the QuTiP Schrödinger Lindblad simulator to instantly search the quantum control landscape for robust, physically deployable DRAG (Derivative Removal by Adiabatic Gate) envelopes.

---

## The Laboratory Solution

In experimental labs, standard Gaussian pulses drop drastically in fidelity when qubit frequencies drift by even a few MHz throughout the day. Instead of tedious manual recalibration loops, AutoPulseSynth generates a continuous microwave envelope that is mathematically guaranteed to work across an entire specified drift window.

Users output these numerical arrays, load them into their **Arbitrary Waveform Generator (AWG)**, IQ-mix them with a local oscillator, and achieve robust logical gates despite hardware instability.

---

## ⚡ Quick Start

AutoPulseSynth is deployed as a modern full-stack application (React + FastAPI).

### 1. Start the Backend Simulation Engine
The backend engine runs the QuTiP physics simulator and Random Forest ML models locally on your CPU/GPU.
```bash
# From the root directory
pip install -r api/requirements-api.txt
uvicorn api.main:app --reload
```
*The engine will start on `http://localhost:8000`*

### 2. Start the Frontend Dashboard
The Next.js interactive UI visualizes the synthesized envelopes and robustness boundaries.
```bash
cd frontend
npm install
npm run dev
```
*The dashboard will start on `http://localhost:3000`*

---

## 📘 Comprehensive Documentation

For a deep dive into the underlying physics (I/Q Envelopes, Transmons), the ML surrogate logic ($R^2$, Differential Evolution), and the deployment architecture, please read the central guide:

* [**Documentation: Comprehensive Architecture & Physics Guide**](docs/comprehensive_guide.md)

---

## Features

- **The Math:** Synthesizes optimized Gaussian-DRAG (Derivative Removal by Adiabatic Gate) microwave envelopes.
- **The ML Engine:** Utilizes Random Forest surrogates to evaluate thousands of pulse shapes in milliseconds.
- **Dynamic Physics Boundaries:** Warns users when attempting physical impossibilities (e.g., $<20$ns duration risking severe leakage).
- **Enterprise Verification Pipeline:** Built-in connection to Q-CTRL's Boulder Opal AWS infrastructure to validate mathematical models natively on the UI.
- **Production-Grade Dashboard:** Sleek, HTML5 Canvas-animated Next.js web application built for laboratory command centers.

---

## Project Structure
```
AutoPulseSynth/
├── api/                     # FastAPI Backend Engine (Python, QuTiP, scikit-learn)
├── frontend/                # Next.js React Dashboard (TailwindCSS, Plotly.js)
├── autopulsesynth/          # Core Physics Model Engine Logic
├── docs/                    # Technical architecture & physics guides
└── scripts/                 # Independent simulation & plotting scripts
```

## Citation

If you use AutoPulseSynth in your research, please cite:

```bibtex
@software{autopulsesynth2026,
  author = {HABER},
  title = {AutoPulseSynth: Robust Quantum Control via Surrogate Optimization},
  year = {2026},
  url = {https://github.com/HABER7789/AutoPulseSynth}
}
```

## License

MIT License - See [LICENSE](LICENSE) for details.
