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

        opt_res = optimize_under_uncertainty(
            pulse_family=pulse,
            surrogate=surrogate,
            uncertainty=uncertainty,
            mode="worst",
            target_ir=target_ir,
            n_theta_eval=64,
            rng_seed=req.seed
        )

        verify_res = verify_in_simulator(
            model=model,
            pulse_family=pulse,
            params=opt_res["best_params"],
            uncertainty=uncertainty,
            target_ir=target_ir,
            n_theta=128,
            rng_seed=req.seed+1
        )

        ox_opt, oy_opt = pulse.sample_controls(opt_res["best_params"])
        base_params = np.array([amp_max/2.0, req.duration/2.0, req.duration/4.0, 0.0, 0.0])
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
