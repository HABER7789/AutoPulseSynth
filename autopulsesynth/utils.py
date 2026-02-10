"""Utility functions for unit conversions and common constants."""
import numpy as np

def hz_to_rad_s(f_hz: float) -> float:
    """Convert frequency in Hz to angular frequency in rad/s."""
    return 2 * np.pi * f_hz

def rad_s_to_hz(w_rad_s: float) -> float:
    """Convert angular frequency in rad/s to frequency in Hz."""
    return w_rad_s / (2 * np.pi)

def ns_to_s(t_ns: float) -> float:
    """Convert time in nanoseconds to seconds."""
    return t_ns * 1e-9

def s_to_ns(t_s: float) -> float:
    """Convert time in seconds to nanoseconds."""
    return t_s * 1e9
