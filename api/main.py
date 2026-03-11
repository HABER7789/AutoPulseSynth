import sys
import os
import numpy as np
import logging

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from autopulsesynth.model import QubitHamiltonianModel, UncertaintyModel
from autopulsesynth.pulses import GaussianDragPulse
from autopulsesynth.optimize import SurrogateDataset, train_surrogate, optimize_under_uncertainty, verify_in_simulator
from autopulsesynth.ir import PulseIR
from autopulsesynth.utils import hz_to_rad_s
from autopulsesynth.simulate import simulate_evolution, target_unitary, fidelity_metric
from autopulsesynth.export import export_azure_quilt

app = FastAPI(title="AutoPulseSynth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SynthesisRequest(BaseModel):
    gate: str = "X"
    duration: float = Field(40e-9, ge=5e-9, le=500e-9)
    t1: Optional[float] = None
    t2: Optional[float] = None
    det_max_hz: float = Field(2e6, ge=0.0, le=50e6)
    det_min_hz: float = Field(-2e6, ge=-50e6, le=0.0)
    amp_error: float = Field(0.05, ge=0.0, le=0.5)
    n_train: int = Field(500, ge=10, le=1000)
    n_theta_train: int = Field(5, ge=1, le=20)
    seed: int = 42
    boulder_opal_key: Optional[str] = None
    quick: bool = False


def gate_aware_baseline_params(gate: str, duration: float, amp_max: float) -> np.ndarray:
    """Compute baseline pulse params with correct amplitude for the target gate.
    
    The amplitude is set so the Gaussian pulse integral equals the rotation
    angle needed for the gate (pi for X, pi/2 for SX, etc.).
    """
    sigma = duration / 4.0
    center = duration / 2.0
    # rotation_angle = amp * sigma * sqrt(2*pi) for a Gaussian
    gate_angles = {'X': np.pi, 'SX': np.pi / 2.0}
    angle = gate_angles.get(gate, np.pi)  # default to pi
    amp = angle / (sigma * np.sqrt(2 * np.pi))
    amp = min(amp, amp_max)  # clamp to max
    return np.array([amp, center, sigma, 0.0, 0.0])

@app.post("/api/synthesize")
def synthesize_pulse(req: SynthesisRequest):
    try:
        det_max_rad = hz_to_rad_s(req.det_max_hz)
        det_min_rad = hz_to_rad_s(req.det_min_hz)

        model = QubitHamiltonianModel(t1=req.t1, t2=req.t2)
        uncertainty = UncertaintyModel(
            detuning_min=det_min_rad, detuning_max=det_max_rad,
            scale_min=1.0 - req.amp_error, scale_max=1.0 + req.amp_error,
            rng_seed=req.seed
        )

        amp_max = 2 * np.pi / req.duration * 4.0
        pulse = GaussianDragPulse(
            duration=req.duration,
            n_steps=int(req.duration * 20e9),
            amp_max=amp_max,
            sigma_min=req.duration / 20.0
        )

        target_ir = PulseIR.from_abstract_gate(req.gate, req.duration)

        dataset = SurrogateDataset.build(
            pulse_family=pulse,
            model=model,
            uncertainty=uncertainty,
            target_ir=target_ir,
            n_pulses=req.n_train,
            n_theta=req.n_theta_train,
            rng_seed=req.seed
        )

        surrogate, metrics = train_surrogate(dataset, rng_seed=req.seed)

        # Quick mode: fewer DE iterations for fast demo
        de_maxiter = 15 if req.quick else 120
        de_popsize = 8 if req.quick else 18
        n_theta_eval = 8 if req.quick else 64
        n_theta_verify = 16 if req.quick else 128

        opt_res = optimize_under_uncertainty(
            pulse_family=pulse,
            surrogate=surrogate,
            uncertainty=uncertainty,
            mode="worst",
            target_ir=target_ir,
            n_theta_eval=n_theta_eval,
            rng_seed=req.seed,
            maxiter=de_maxiter,
            popsize=de_popsize
        )

        verify_res = verify_in_simulator(
            model=model,
            pulse_family=pulse,
            params=opt_res["best_params"],
            uncertainty=uncertainty,
            target_ir=target_ir,
            n_theta=n_theta_verify,
            rng_seed=req.seed+1
        )

        # Gate-aware baseline: correct amplitude for target rotation
        base_params = gate_aware_baseline_params(req.gate, req.duration, amp_max)
        
        # Safeguard: verify baseline in simulator
        base_verify = verify_in_simulator(
            model=model, pulse_family=pulse, params=base_params,
            uncertainty=uncertainty, target_ir=target_ir,
            n_theta=n_theta_verify, rng_seed=req.seed+1
        )

        # If baseline wins on worst-case, fall back to baseline
        used_baseline_fallback = False
        if base_verify["f_worst"] > verify_res["f_worst"]:
            used_baseline_fallback = True
            final_params = base_params
            verify_res = base_verify
        else:
            final_params = opt_res["best_params"]

        ox_opt, oy_opt = pulse.sample_controls(final_params)
        ox_base, oy_base = pulse.sample_controls(base_params)
        time_grid = pulse.time_grid()

        det_bound = req.det_max_hz * 1.5
        detunings = np.linspace(-det_bound, det_bound, 41)
        det_rad = detunings * 2 * np.pi

        fids_opt = []
        fids_base = []
        target = target_unitary(req.gate)
        for d in det_rad:
            th = np.array([d, 1.0, 0.0, 0.0])
            res_opt = simulate_evolution(model, req.duration, ox_opt, oy_opt, th)
            res_base = simulate_evolution(model, req.duration, ox_base, oy_base, th)
            fids_opt.append(fidelity_metric(res_opt, target))
            fids_base.append(fidelity_metric(res_base, target))

        bo_fidelities = None
        bo_error = None
        if req.boulder_opal_key:
            os.environ["QCTRL_PLATFORM_API_KEY"] = req.boulder_opal_key
            try:
                import boulderopal as bo
                # Simple PWC time evolution using BO
                graph = bo.Graph()
                detunings_tensor = graph.tensor(detunings)
                det_coefs = graph.reshape(detunings_tensor, [41, 1, 1]) * 2.0 * np.pi
                sz_t = graph.reshape(graph.tensor(np.array([[1, 0], [0, -1]], dtype=complex)), [1, 2, 2])
                h_detuning = 0.5 * det_coefs * sz_t
                h_det_rep = graph.reshape(h_detuning, [41, 1, 2, 2])
                n_steps = len(ox_opt)
                h_det_t = graph.repeat(h_det_rep, repeats=n_steps, axis=1)

                ox_sh = graph.reshape(graph.tensor(ox_opt), [1, n_steps, 1, 1])
                oy_sh = graph.reshape(graph.tensor(oy_opt), [1, n_steps, 1, 1])
                sx_t = graph.reshape(graph.tensor(np.array([[0, 1], [1, 0]], dtype=complex)), [1, 1, 2, 2])
                sy_t = graph.reshape(graph.tensor(np.array([[0, -1j], [1j, 0]], dtype=complex)), [1, 1, 2, 2])
                h_x_vals = 0.5 * ox_sh * sx_t
                h_y_vals = 0.5 * oy_sh * sy_t

                h_total_vals = h_det_t + h_x_vals + h_y_vals
                h_total_pwc = graph.pwc(values=h_total_vals, durations=np.array([req.duration / n_steps] * n_steps), time_dimension=1)

                unitaries = graph.time_evolution_operators_pwc(hamiltonian=h_total_pwc, sample_times=np.array([req.duration]))
                final_unitaries = unitaries[:, 0, :, :]

                target_tensor = graph.tensor(np.array([[0, 1], [1, 0]], dtype=complex) if req.gate == 'X' else np.array([[0.5+0.5j, 0.5-0.5j], [0.5-0.5j, 0.5+0.5j]], dtype=complex))
                target_tensor_rep = graph.repeat(graph.reshape(target_tensor, [1, 2, 2]), repeats=41, axis=0)
                products = graph.matmul(graph.adjoint(target_tensor_rep), final_unitaries)
                fidelities_tr = graph.abs(graph.trace(products)) ** 2
                infidelities = 1.0 - (fidelities_tr / 4.0)
                infidelities.name = "infidelities"

                result = bo.execute_graph(graph=graph, output_node_names=["infidelities"])
                bo_infs = result["output"]["infidelities"]["value"]
                bo_fidelities_np = ((1 - bo_infs) * 4 + 2) / 6
                bo_fidelities = bo_fidelities_np.tolist()
            except Exception as e:
                logging.error(f"BO Benchmark Error: {e}")
                bo_error = str(e)

        return {
            "status": "success",
            "metrics": metrics,
            "optimized_params": opt_res["best_params"].tolist(),
            "verification": {
                "f_mean": verify_res["f_mean"],
                "f_worst": verify_res["f_worst"],
                "f_std": verify_res["f_std"],
            },
            "quilt_program": export_azure_quilt(
                pulse_family=pulse, params=opt_res["best_params"], gate_name=req.gate.lower(), qubit_index=0
            ),
            "baseline_comparison": {
                "used_baseline_fallback": used_baseline_fallback,
                "baseline_f_mean": base_verify["f_mean"],
                "baseline_f_worst": base_verify["f_worst"],
            },
            "plot_data": {
                "time_ns": (time_grid * 1e9).tolist(),
                "i_wave": ox_opt.tolist(),
                "q_wave": oy_opt.tolist(),
                "detunings_mhz": (detunings / 1e6).tolist(),
                "fidelities": fids_opt,
                "fidelities_baseline": fids_base,
                "bo_fidelities": bo_fidelities,
                "bo_error": bo_error
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─── SSE Streaming Endpoint ────────────────────────────────────────
from fastapi import Request
from fastapi.responses import StreamingResponse
import json as json_mod
import time

def _sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event."""
    payload = json_mod.dumps(data, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    return f"event: {event_type}\ndata: {payload}\n\n"

@app.get("/api/synthesize-stream")
async def synthesize_stream(
    gate: str = "X",
    duration: float = 40e-9,
    det_max_hz: float = 2e6,
    det_min_hz: float = -2e6,
    amp_error: float = 0.05,
    n_train: int = 500,
    n_theta_train: int = 5,
    seed: int = 42,
    quick: bool = False,
    boulder_opal_key: Optional[str] = None,
):
    def generate():
        try:
            t_start = time.time()
            det_max_rad = hz_to_rad_s(det_max_hz)
            det_min_rad = hz_to_rad_s(det_min_hz)

            model = QubitHamiltonianModel(t1=None, t2=None)
            uncertainty = UncertaintyModel(
                detuning_min=det_min_rad, detuning_max=det_max_rad,
                scale_min=1.0 - amp_error, scale_max=1.0 + amp_error,
                rng_seed=seed
            )

            amp_max = 2 * np.pi / duration * 4.0
            n_steps = int(duration * 20e9)
            pulse = GaussianDragPulse(
                duration=duration, n_steps=n_steps,
                amp_max=amp_max, sigma_min=duration / 20.0
            )
            target_ir = PulseIR.from_abstract_gate(gate, duration)

            # Event 1: Setup — Hamiltonian & target
            yield _sse_event("setup", {
                "hamiltonian": "H(t) = (Δ/2)σz + (Ωx/2)σx + (Ωy/2)σy",
                "sigma_z": [[1, 0], [0, -1]],
                "target_unitary": target_ir.unitary_matrix.tolist(),
                "gate": gate,
                "delta_range_rad": [float(det_min_rad), float(det_max_rad)],
                "delta_range_mhz": [det_min_hz / 1e6, det_max_hz / 1e6],
                "amp_max": float(amp_max),
                "n_steps": n_steps,
                "duration_ns": duration * 1e9,
                "elapsed": round(time.time() - t_start, 2),
            })

            # Determine quick mode params
            de_maxiter = 15 if quick else 120
            de_popsize = 8 if quick else 18
            n_theta_eval = 8 if quick else 64
            n_theta_verify = 16 if quick else 128
            actual_n_train = 30 if quick else n_train
            actual_n_theta = 2 if quick else n_theta_train
            total_sims = actual_n_train * actual_n_theta

            # Event 2: Training start
            yield _sse_event("training_start", {
                "n_pulses": actual_n_train,
                "n_theta": actual_n_theta,
                "total_sims": total_sims,
                "elapsed": round(time.time() - t_start, 2),
            })

            dataset = SurrogateDataset.build(
                pulse_family=pulse, model=model, uncertainty=uncertainty,
                target_ir=target_ir, n_pulses=actual_n_train,
                n_theta=actual_n_theta, rng_seed=seed
            )

            # Event 3: Training complete
            yield _sse_event("training_done", {
                "total_sims": total_sims,
                "elapsed": round(time.time() - t_start, 2),
            })

            surrogate, metrics = train_surrogate(dataset, rng_seed=seed)

            # Event 4: Surrogate trained
            yield _sse_event("surrogate", {
                "r2": round(metrics["r2"], 4),
                "mae": round(metrics["mae"], 6),
                "n_estimators": 100,
                "n_features": int(surrogate.n_features_in_),
                "elapsed": round(time.time() - t_start, 2),
            })

            # DE optimization with per-generation callback
            gen_counter = [0]
            def de_callback(xk, convergence):
                gen_counter[0] += 1

            opt_res = optimize_under_uncertainty(
                pulse_family=pulse, surrogate=surrogate, uncertainty=uncertainty,
                mode="worst", target_ir=target_ir, n_theta_eval=n_theta_eval,
                rng_seed=seed, maxiter=de_maxiter, popsize=de_popsize,
                callback=de_callback
            )

            # Event 5: Optimization complete
            yield _sse_event("optimization", {
                "generations": gen_counter[0],
                "maxiter": de_maxiter,
                "popsize": de_popsize,
                "pred_f_mean": round(opt_res["pred_f_mean"], 4),
                "pred_f_worst": round(opt_res["pred_f_worst"], 4),
                "elapsed": round(time.time() - t_start, 2),
            })

            verify_res = verify_in_simulator(
                model=model, pulse_family=pulse, params=opt_res["best_params"],
                uncertainty=uncertainty, target_ir=target_ir,
                n_theta=n_theta_verify, rng_seed=seed+1
            )

            # Gate-aware baseline + safeguard
            base_params = gate_aware_baseline_params(gate, duration, amp_max)
            base_verify = verify_in_simulator(
                model=model, pulse_family=pulse, params=base_params,
                uncertainty=uncertainty, target_ir=target_ir,
                n_theta=n_theta_verify, rng_seed=seed+1
            )

            used_baseline_fallback = False
            if base_verify["f_worst"] > verify_res["f_worst"]:
                used_baseline_fallback = True
                final_params = base_params
                verify_res = base_verify
            else:
                final_params = opt_res["best_params"]

            # Compute achieved unitary at zero detuning
            ox_opt, oy_opt = pulse.sample_controls(final_params)
            zero_theta = np.array([0.0, 1.0, 0.0, 0.0])
            achieved_U = simulate_evolution(model, duration, ox_opt, oy_opt, zero_theta)

            # Event 6: Verification
            yield _sse_event("verification", {
                "f_mean": round(verify_res["f_mean"], 4),
                "f_worst": round(verify_res["f_worst"], 4),
                "f_std": round(verify_res["f_std"], 6),
                "n_theta": n_theta_verify,
                "target_U": target_ir.unitary_matrix.tolist(),
                "achieved_U": [
                    [complex_to_str(achieved_U[i][j]) for j in range(2)] for i in range(2)
                ],
                "used_baseline_fallback": used_baseline_fallback,
                "baseline_f_worst": round(base_verify["f_worst"], 4),
                "elapsed": round(time.time() - t_start, 2),
            })

            # Now compute full results (robustness scan, BO, etc.)
            # Event 7: Robustness scan
            yield _sse_event("robustness_scan", {
                "n_points": 41,
                "elapsed": round(time.time() - t_start, 2),
            })
            ox_base, oy_base = pulse.sample_controls(base_params)
            time_grid = pulse.time_grid()

            det_bound = det_max_hz * 1.5
            detunings = np.linspace(-det_bound, det_bound, 41)
            det_rad = detunings * 2 * np.pi

            fids_opt = []
            fids_base = []
            target = target_unitary(gate)
            for d in det_rad:
                th = np.array([d, 1.0, 0.0, 0.0])
                res_opt = simulate_evolution(model, duration, ox_opt, oy_opt, th)
                res_base = simulate_evolution(model, duration, ox_base, oy_base, th)
                fids_opt.append(fidelity_metric(res_opt, target))
                fids_base.append(fidelity_metric(res_base, target))

            bo_fidelities = None
            bo_error = None
            if boulder_opal_key:
                # Event 8: Boulder Opal benchmarking
                yield _sse_event("boulder_opal", {
                    "status": "connecting",
                    "elapsed": round(time.time() - t_start, 2),
                })
                os.environ["QCTRL_PLATFORM_API_KEY"] = boulder_opal_key
                try:
                    import boulderopal as bo
                    graph = bo.Graph()
                    detunings_tensor = graph.tensor(detunings)
                    det_coefs = graph.reshape(detunings_tensor, [41, 1, 1]) * 2.0 * np.pi
                    sz_t = graph.reshape(graph.tensor(np.array([[1, 0], [0, -1]], dtype=complex)), [1, 2, 2])
                    h_detuning = 0.5 * det_coefs * sz_t
                    h_det_rep = graph.reshape(h_detuning, [41, 1, 2, 2])
                    h_det_t = graph.repeat(h_det_rep, repeats=n_steps, axis=1)

                    ox_sh = graph.reshape(graph.tensor(ox_opt), [1, n_steps, 1, 1])
                    oy_sh = graph.reshape(graph.tensor(oy_opt), [1, n_steps, 1, 1])
                    sx_t = graph.reshape(graph.tensor(np.array([[0, 1], [1, 0]], dtype=complex)), [1, 1, 2, 2])
                    sy_t = graph.reshape(graph.tensor(np.array([[0, -1j], [1j, 0]], dtype=complex)), [1, 1, 2, 2])
                    h_x_vals = 0.5 * ox_sh * sx_t
                    h_y_vals = 0.5 * oy_sh * sy_t

                    h_total_vals = h_det_t + h_x_vals + h_y_vals
                    h_total_pwc = graph.pwc(values=h_total_vals, durations=np.array([duration / n_steps] * n_steps), time_dimension=1)

                    unitaries = graph.time_evolution_operators_pwc(hamiltonian=h_total_pwc, sample_times=np.array([duration]))
                    final_unitaries = unitaries[:, 0, :, :]

                    target_tensor = graph.tensor(np.array([[0, 1], [1, 0]], dtype=complex) if gate == 'X' else np.array([[0.5+0.5j, 0.5-0.5j], [0.5-0.5j, 0.5+0.5j]], dtype=complex))
                    target_tensor_rep = graph.repeat(graph.reshape(target_tensor, [1, 2, 2]), repeats=41, axis=0)
                    products = graph.matmul(graph.adjoint(target_tensor_rep), final_unitaries)
                    fidelities_tr = graph.abs(graph.trace(products)) ** 2
                    infidelities = 1.0 - (fidelities_tr / 4.0)
                    infidelities.name = "infidelities"

                    result = bo.execute_graph(graph=graph, output_node_names=["infidelities"])
                    bo_infs = result["output"]["infidelities"]["value"]
                    bo_fidelities_np = ((1 - bo_infs) * 4 + 2) / 6
                    bo_fidelities = bo_fidelities_np.tolist()
                except Exception as e:
                    logging.error(f"BO Benchmark Error: {e}")
                    bo_error = str(e)

            # Event 7: Complete — full results payload
            yield _sse_event("complete", {
                "status": "success",
                "metrics": metrics,
                "optimized_params": opt_res["best_params"].tolist(),
                "verification": {
                    "f_mean": verify_res["f_mean"],
                    "f_worst": verify_res["f_worst"],
                    "f_std": verify_res["f_std"],
                },
                "quilt_program": export_azure_quilt(
                    pulse_family=pulse, params=opt_res["best_params"], gate_name=gate.lower(), qubit_index=0
                ),
                "baseline_comparison": {
                    "used_baseline_fallback": used_baseline_fallback,
                    "baseline_f_mean": base_verify["f_mean"],
                    "baseline_f_worst": base_verify["f_worst"],
                },
                "plot_data": {
                    "time_ns": (time_grid * 1e9).tolist(),
                    "i_wave": ox_opt.tolist(),
                    "q_wave": oy_opt.tolist(),
                    "detunings_mhz": (detunings / 1e6).tolist(),
                    "fidelities": fids_opt,
                    "fidelities_baseline": fids_base,
                    "bo_fidelities": bo_fidelities,
                    "bo_error": bo_error
                },
                "elapsed": round(time.time() - t_start, 2),
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream")


def complex_to_str(c):
    """Format a complex number for display."""
    r, i = c.real, c.imag
    if abs(i) < 1e-10:
        return f"{r:.3f}"
    if abs(r) < 1e-10:
        return f"{i:.3f}i"
    sign = "+" if i >= 0 else "-"
    return f"{r:.3f}{sign}{abs(i):.3f}i"

