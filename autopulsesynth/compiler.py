"""OpenQASM and QIR ingestion compiler layer.

Uses Qiskit to parse OpenQASM 2.0 circuits and translate them 
into the hardware-agnostic PulseIR arrays for downstream optimization.
"""

from typing import List
import warnings
from qiskit import QuantumCircuit
from autopulsesynth.ir import PulseIR

def parse_qasm_to_ir(qasm_string: str, default_duration: float = 40e-9) -> List[PulseIR]:
    """Parse an OpenQASM string into a list of PulseIR sequences.
    
    Args:
        qasm_string: OpenQASM 2.0 valid string.
        default_duration: Default duration in seconds for mapped single-qubit gates.
        
    Returns:
        List of PulseIR objects forming the sequential hardware schedule.
    """
    circuit = QuantumCircuit.from_qasm_str(qasm_string)
    
    ir_schedule = []
    
    for instruction in circuit.data:
        gate_name = instruction.operation.name.upper()
        
        # We silently ignore measurements and barriers for the physical pulse schedule.
        if gate_name in ['MEASURE', 'BARRIER']:
            continue
            
        # In a real environment, we'd decompose arbitrary unitaries.
        # Here we map basis gates (X, SX) to our PulseIR.
        if gate_name not in ['X', 'SX']:
            warnings.warn(f"Warning: Gate '{gate_name}' is not directly natively supported by AutoPulseSynth's DRAG backend. Approximating via X gate for demonstration.")
            gate_name = 'X'
            
        pulse_ir = PulseIR.from_abstract_gate(gate_name, duration=default_duration)
        ir_schedule.append(pulse_ir)
        
    return ir_schedule
