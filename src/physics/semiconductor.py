"""Generic (non-junction-specific) semiconductor statistics.

Formulas match docs/physics.md sec 2. These operate on a single uniform
region; PN-junction-specific formulas (built-in potential, depletion width)
live in analytical_pnjunction.py since they need two doping levels.
"""

import math

from .constants import thermal_voltage, N_I_300K, T_REF


def electron_concentration(fermi_level_ev: float, intrinsic_level_ev: float,
                            temperature_k: float = T_REF, n_i: float = N_I_300K) -> float:
    """n = n_i * exp((E_F - E_i) / (k_B T)), non-degenerate approximation."""
    v_t = thermal_voltage(temperature_k)
    return n_i * math.exp((fermi_level_ev - intrinsic_level_ev) / v_t)


def hole_concentration(fermi_level_ev: float, intrinsic_level_ev: float,
                        temperature_k: float = T_REF, n_i: float = N_I_300K) -> float:
    """p = n_i * exp((E_i - E_F) / (k_B T)), non-degenerate approximation."""
    v_t = thermal_voltage(temperature_k)
    return n_i * math.exp((intrinsic_level_ev - fermi_level_ev) / v_t)


def mass_action_product(n: float, p: float, n_i: float = N_I_300K) -> float:
    """Returns n*p / n_i^2; should be ~1 at equilibrium (np = n_i^2)."""
    return (n * p) / (n_i ** 2)


def majority_carrier_from_doping(doping_cm3: float, n_i: float = N_I_300K) -> float:
    """Full-ionization approximation: majority carrier ~= |doping| when
    |doping| >> n_i (n ~= N_D for n-type, p ~= N_A for p-type)."""
    return abs(doping_cm3)
