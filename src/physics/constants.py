"""Physical constants and default reference values.

Values and symbols match docs/physics.md sec 1. Kept as plain module-level
constants (not a class) since every value here is a fixed physical constant
or a documented reference default, not configurable state.
"""

Q = 1.602176634e-19  # elementary charge, C
K_B = 1.380649e-23  # Boltzmann constant, J/K
EPS_0 = 8.8541878128e-12  # vacuum permittivity, F/m (SI)

# DEVSIM's built-in physics models (devsim.python_packages.simple_physics)
# work in cm-based CGS units. This project's own analytical code uses SI
# constants above; EPS_0_CM converts for direct comparison against DEVSIM
# node/edge model output without silently mixing unit systems.
EPS_0_CM = 8.85e-14  # vacuum permittivity, F/cm

EPS_SI = 11.7  # silicon relative permittivity
EPS_SI_DEVSIM = 11.1  # relative permittivity value DEVSIM's bundled model uses
EPS_OX = 3.9  # SiO2 relative permittivity

N_I_300K = 1.0e10  # intrinsic carrier concentration, Si, 300 K, cm^-3
T_REF = 300.0  # reference temperature, K

# devsim.python_packages.simple_physics hardcodes its own rounded constants
# (q = 1.6e-19 C, k = 1.3806503e-23 J/K) rather than CODATA-precise values.
# Any analytical formula being validated against DEVSIM's numerical output
# must use these, not Q/K_B above -- otherwise an apparent mismatch is just
# a constant-definition difference, not a real physics or numerical
# discrepancy (see docs/physics.md footnote, docs/validation.md Sprint 1).
Q_DEVSIM = 1.6e-19
K_B_DEVSIM = 1.3806503e-23


def thermal_voltage(temperature_k: float = T_REF) -> float:
    """V_T = k_B T / q, in volts, using CODATA-precise constants."""
    return K_B * temperature_k / Q


def thermal_voltage_devsim(temperature_k: float = T_REF) -> float:
    """V_T using DEVSIM's own bundled constants -- use this whenever a
    formula's output is compared directly against a DEVSIM simulation
    result."""
    return K_B_DEVSIM * temperature_k / Q_DEVSIM
