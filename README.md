# AutoPulseSynth

![AutoPulseSynth Banner](docs/images/image%2024.png)

AutoPulseSynth is a machine learning-assisted optimization framework for synthesizing Gaussian-DRAG microwave control pulses for superconducting qubits. 

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/frontend-Next.js-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-teal.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

The framework uses a Random Forest surrogate model to drive a Differential Evolution optimizer. This process selects pulse parameters that maximize state fidelity, specifically targeting robustness against hardware uncertainty, such as charge noise and Two-Level System (TLS) defects. 

The optimized waveform arrays can be exported for execution on arbitrary waveform generators (AWGs) and cross-validated against cloud-based physics simulators.

## Installation

### Quick Start

A provided shell script automatically configures the Python backend, installs dependencies, and launches both frontend and backend servers.

```bash
git clone https://github.com/HABER7789/AutoPulseSynth.git
cd AutoPulseSynth
./run.sh
```

### Manual Setup

Alternatively, you can start the components independently.

**Backend (API + QuTiP Simulators)**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-api.txt
uvicorn api.main:app --reload --port 8000
```

**Frontend (Next.js Dashboard)**
```bash
cd frontend
npm install
npm run dev
```

## Features and Usage

### Simulation and Optimization
The pipeline utilizes QuTiP for Hamiltonian propagation to simulate arbitrary qubit drift. Optimization can be run via two profiles:
- **Full Run**: Exhaustive search over 450 training samples and 120 DE iterations for maximum fidelity.
- **Quick Demo**: Parameterized for rapid execution (under 15 seconds) with reduced sampling, useful for testing and demonstrations.

### VS Code Extension
The project includes a custom Visual Studio Code extension (`autopulsesynth-inspector`) that provides an interactive `.pulse.json` UI.
- **Visual Inspector**: Renders pulse waveforms, fidelity plots, and metrics directly inside the editor. 
- **Quick Optimization**: Integrates with the local FastAPI backend to trigger pulse generation via the command palette (`AutoPulseSynth: Quick Optimize`).
- **Installation**: Navigate to the `vscode-extension` directory, compile using `npm run compile`, and launch the extension host in VS Code.

### Q-CTRL Boulder Opal Integration
During local execution, users can supply a Q-CTRL API key to cross-validate generated pulses against the Boulder Opal infrastructure. Note that this feature requires a local deployment due to OAuth requirements.

### Azure Quantum Export
Optimized parameter sets can be exported into the Rigetti Quil-T instruction set (`.quil`). This file packages an IQ waveform envelope, a custom `DEFCAL` block, and readout instructions formatted for Azure Quantum execution. 
*(Note: AutoPulseSynth provides formatting capabilities only; hardware execution requires an active Azure subscription).*

## Structure

```
AutoPulseSynth/
├── api/                  # FastAPI backend
├── autopulsesynth/       # Core optimization and physics package
│   ├── cli.py            # Command-line interface definitions
│   ├── export.py         # JSON and Rigetti Quil-T export logic
│   ├── ir.py             # Intermediate Representation models
│   ├── metrics.py        # Fidelity calculations (Horodecki metrics)
│   ├── model.py          # Hamiltonian and Lindblad system construction
│   ├── optimize.py       # Surrogate and Differential Evolution controllers
│   ├── pulses.py         # Gaussian-DRAG parameter definitions
│   ├── simulate.py       # QuTiP state propagation backends
│   └── utils.py          # Utilities
├── frontend/             # Next.js web dashboard
├── vscode-extension/     # AutoPulseSynth UI extension for VS Code
├── docs/                 # Associated documentation and images
├── tests/                # Unit testing suite
├── scripts/              # Independent analysis tooling
├── run.sh                # Automated application launcher
├── render.yaml           # Deployment configuration for the Render platform
├── requirements-api.txt  # Core application dependencies
└── requirements.txt      # Total dependencies
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
