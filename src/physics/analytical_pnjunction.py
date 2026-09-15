"""Analytical PN-junction formulas, matching docs/physics.md sec 3.

These are the closed-form predictions that the DEVSIM numerical PN-junction
simulation (simulations/pnjunction/run_pn_junction.py) is checked against
in validation.py.
"""

import math

from .constants import (
    Q_DEVSIM,
    EPS_0_CM,
    EPS_SI_DEVSIM,
    N_I_300K,
    thermal_voltage_devsim,
    T_REF,
)


def built_in_potential(na_cm3: float, nd_cm3: float,
                        temperature_k: float = T_REF, n_i: float = N_I_300K) -> float:
    """V_bi = V_T * ln(N_A * N_D / n_i^2).

    Uses DEVSIM's own bundled constants (see constants.py Q_DEVSIM /
    thermal_voltage_devsim) since this is validated directly against a
    DEVSIM numerical result -- see docs/physics.md footnote.
    """
    v_t = thermal_voltage_devsim(temperature_k)
    return v_t * math.log((na_cm3 * nd_cm3) / (n_i ** 2))


def depletion_width(na_cm3: float, nd_cm3: float, v_bi: float,
                     eps_si_rel: float = EPS_SI_DEVSIM) -> float:
    """Total depletion width W (cm), step junction, zero applied bias.

    eps_si_rel defaults to DEVSIM's own bundled constant (11.1) rather than
    the textbook value (11.7, see docs/physics.md footnote) so this matches
    what the numerical simulation actually uses.
    """
    eps = eps_si_rel * EPS_0_CM
    return math.sqrt(2 * eps * (na_cm3 + nd_cm3) * v_bi / (Q_DEVSIM * na_cm3 * nd_cm3))


def depletion_widths_each_side(w_cm: float, na_cm3: float, nd_cm3: float):
    """Returns (x_p, x_n): depletion extent into the p-side and n-side."""
    x_p = w_cm * nd_cm3 / (na_cm3 + nd_cm3)
    x_n = w_cm * na_cm3 / (na_cm3 + nd_cm3)
    return x_p, x_n


def ideal_diode_current(voltage: float, i_0: float, temperature_k: float = T_REF) -> float:
    """Ideal (Shockley) diode law: I = I_0 * (exp(V / V_T) - 1).

    Reference only -- the DEVSIM numerical result includes SRH
    recombination and is not expected to match this exactly at low bias
    (see docs/validation.md); it is used to check the forward-bias slope
    (ideality factor) in the mid-bias region.
    """
    v_t = thermal_voltage_devsim(temperature_k)
    return i_0 * (math.exp(voltage / v_t) - 1.0)


def ideality_factor(v0: float, i0: float, v1: float, i1: float,
                     temperature_k: float = T_REF) -> float:
    """Local ideality factor n from two forward-bias (V, I) points:
    n = (V1 - V0) / (V_T * ln(I1 / I0)). n ~= 1 indicates ideal
    diffusion-current behavior. Uses DEVSIM's constants since v0/i0/v1/i1
    come from a DEVSIM simulation."""
    v_t = thermal_voltage_devsim(temperature_k)
    return (v1 - v0) / (v_t * math.log(i1 / i0))
