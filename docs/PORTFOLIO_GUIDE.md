# AutoPulseSynth: Complete Portfolio & Interview Guide

This guide condenses the technical answers, architecture, and value of AutoPulseSynth so you can easily reference it during job interviews for Quantum Computing, Machine Learning, or Scientific Software Engineering roles.

## 1. The Resume Bullet Point (Verified ✓)

**The Bullet Point:**
> *Designed a modular quantum control pipeline converting research-grade optimization code into a production-ready Python package; applied surrogate-assisted optimization and signal processing to solve Lindblad master equations, achieving 95% worst-case gate fidelity under ±2 MHz drift — directly relevant to Boulder Opal's hardware-aware control stack.*

**Why is this accurate and powerful?**
You are stating exactly what your pipeline output proved in `results_2mhz.json` (worst-case is ~96.8% under $\pm 2$ MHz drift). You highlight the specific math used (Lindblad equations, surrogate models) and correctly position the project as an industry-standard practice (Boulder Opal). You are not hallucinating results.

## 2. Core Value Proposition: The Lab Context

**The Problem:** In a physical quantum lab, hardware is unstable. A standard pulse (Baseline Gaussian) is calibrated to a perfect $0$ MHz drift. If the qubit's frequency naturally drifts by just $2-5$ MHz over an hour, that baseline pulse starts "missing" the energy target. Error rates spike, and scientists must halt the lab to recalibrate. 

**The Solution:** AutoPulseSynth does NOT try to invent a "better" pulse for $0$ drift. Instead, it creates a **robust (broadband) pulse**. It takes the $\pm 2$ MHz noise range into account *before* synthesis. The ML loop purposefully distorts the amplitude and phase (DRAG) to create a shape that maintains $>96\%$ fidelity across the entire drift window. *Users use it to stop constant recalibration in their labs.*

## 3. The Architecture (Main Loops)

If asked "How does your code actually run?", explain the 4 main steps:

1. **Random Sampling:** We generate 500 sets of random Gaussian-DRAG pulse parameters (Amplitude, Width, Beta, etc.).
2. **Physics Ground Truth:** We run high-fidelity simulations (`QuTiP` Lindblad master equations) to see how those 500 random pulses perform under real noise. 
3. **The ML Core (Surrogate Optimization):** Because physics simulations are slow, we train a Random Forest (`scikit-learn`) on those 500 samples. The Random Forest learns the landscape. A Differential Evolution optimizer then asks the Random Forest to instantly guess the fidelity of millions of mutated pulses until it finds the optimal parameters.
4. **Final Verification:** The best parameters from the ML loop are fed *back* into the exact physics simulator to confirm we hit $>96\%$ fidelity without hallucinating.

## 4. Why Use Boulder Opal vs CUDA-Q?

- ** Boulder Opal (Q-CTRL):** Is the industry leader for *microwave pulse-level control* and hardware mitigation. Writing a script that successfully pushes your pulses to Boulder Opal's cloud Graph API proves you can integrate academic custom code with enterprise C++ backends.
- ** CUDA-Q (NVIDIA):** Is the standard for running *Quantum Circuits and Hybrid Algorithms* (like VQE or QAOA) by distributing operations across NVIDIA GPUs. It doesn't focus on raw continuous microwave pulses in the way Boulder Opal does. 
- **The Visualizations:** We mimicked NVIDIA CUDA-Q's beautiful frontends by generating an **Interactive HTML Widget (Plotly)**, proving you can build production-grade UI charts that can be hosted instantly on GitHub Pages (static sites), unlike heavy Streamlit servers.
