"""Fidelity metrics for quantum gates and states."""
import numpy as np

def average_gate_fidelity_unitary(U: np.ndarray, V: np.ndarray) -> float:
    """Compute average gate fidelity between implemented unitary U and target V for d=2.
    
    Formula: F_avg = (|Tr(V^† U)|^2 + d) / (d(d+1))
    """
    d = 2
    # Ensure matrices are numpy arrays
    U = np.array(U, dtype=complex)
    V = np.array(V, dtype=complex)
    
    tr = np.trace(np.conjugate(V.T) @ U)
    return float((np.abs(tr) ** 2 + d) / (d * (d + 1)))

def average_state_fidelity_proxy(states_out: list[np.ndarray], target_U: np.ndarray) -> float:
    """Compute average state fidelity over a specific basis set (Cardinal States).
    
    This is a proxy for open-system performance when full process tomography is too expensive
    or not needed. It averages the overlap Tr(rho_target * rho_out) for the 4 states:
    |0>, |1>, |+>, |+i>.
    
    Args:
        states_out: List of 4 density matrices [rho_0, rho_1, rho_+, rho_+i] from simulation.
        target_U: Target unitary matrix (2x2) that defines the ideal states.
    """
    # Define the 4 input states corresponding to the simulation order
    input_states = [
        np.array([[1],[0]], dtype=complex),                      # |0>
        np.array([[0],[1]], dtype=complex),                      # |1>
        np.array([[1],[1]], dtype=complex)/np.sqrt(2),           # |+>
        np.array([[1],[1j]], dtype=complex)/np.sqrt(2),          # |+i>
    ]
    
    if len(states_out) != 4:
        raise ValueError(f"Expected 4 output states, got {len(states_out)}")
        
    f_sum = 0.0
    for i, rho_out in enumerate(states_out):
        psi_in = input_states[i]
        psi_target = target_U @ psi_in
        # Create pure target density matrix
        rho_target = psi_target @ psi_target.conj().T
        
        # Compute overlap: Tr(rho_target * rho_out)
        # Since rho_target is pure (|psi><psi|), this is equivalent to <psi|rho_out|psi>
        overlap = np.real(np.trace(rho_target @ rho_out))
        f_sum += overlap
        
    return float(f_sum / 4.0)
