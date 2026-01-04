# AutoPulseSynth (baseline)

**AutoPulseSynth** is a small, reproducible baseline project for **single-qubit pulse synthesis** targeting **X** and **SX** gates under a **fixed, physically meaningful Hamiltonian** with **parameter uncertainty**.

> All results are **simulated** and explicitly labeled as such.

## What this repo does

Given a target gate (X or SX), I synthesize constrained control pulses to maximize **average gate fidelity** under a driven qubit Hamiltonian:

$$
H(t) = \frac{\Delta}{2}\sigma_z + \frac{\Omega_x(t)}{2}\sigma_x + \frac{\Omega_y(t)}{2}\sigma_y
$$

I *do not* learn arbitrary Hamiltonians. Imperfect physics and calibration are modeled via uncertain parameters $\theta$ (detuning, amplitude scale error, IQ imbalance, quasi-static detuning noise).

A **surrogate-assisted optimization** loop (scikit-learn + scipy) searches pulse parameters for performance under parameter variation across $\theta$.

## Quickstart (local)
```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Open:
- `notebooks/01_single_qubit_autopulsesynth.ipynb`

## Notes on reproducibility

- Random seeds are fixed in the notebook.
- Dataset generation is deterministic given the seeds and versions in `requirements.txt`.

## Optional: qBraid

This notebook is designed to run on hosted Jupyter environments. If QuTiP is missing, install it with:
```bash
pip install qutip
```

## License

MIT (see `LICENSE`).