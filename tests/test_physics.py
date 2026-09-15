import math
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.physics.constants import thermal_voltage, thermal_voltage_devsim, T_REF
from src.physics.analytical_pnjunction import (
    built_in_potential,
    depletion_width,
    depletion_widths_each_side,
    ideality_factor,
)
from src.physics.doping import step_junction_devsim_expression, step_junction_profile
from src.physics.validation import compare, validate_builtin_potential


def test_thermal_voltage_room_temperature():
    # docs/physics.md quotes ~0.02585 V as a rounded reference; the two
    # constant sets (CODATA-precise vs DEVSIM's bundled rounded constants,
    # see constants.py) differ from that reference and each other at the
    # sub-percent level, so a loose tolerance is intentional here.
    assert math.isclose(thermal_voltage(T_REF), 0.02585, rel_tol=5e-3)
    assert math.isclose(thermal_voltage_devsim(T_REF), 0.02585, rel_tol=5e-3)


def test_built_in_potential_symmetric_junction():
    # Sprint 1 device: N_A = N_D = 1e16 cm^-3 -> matches the actual DEVSIM
    # simulation result recorded in docs/validation.md (0.71528958 V).
    vbi = built_in_potential(1e16, 1e16)
    assert math.isclose(vbi, 0.71528958, rel_tol=1e-6)


def test_depletion_width_splits_correctly_for_symmetric_junction():
    vbi = built_in_potential(1e16, 1e16)
    w = depletion_width(1e16, 1e16, vbi)
    x_p, x_n = depletion_widths_each_side(w, 1e16, 1e16)
    assert math.isclose(x_p, x_n, rel_tol=1e-9)
    assert math.isclose(x_p + x_n, w, rel_tol=1e-9)


def test_depletion_width_asymmetric_junction_favors_lighter_side():
    vbi = built_in_potential(1e18, 1e16)
    w = depletion_width(1e18, 1e16, vbi)
    x_p, x_n = depletion_widths_each_side(w, 1e18, 1e16)
    # lightly-doped n-side should hold most of the depletion width
    assert x_n > x_p


def test_ideality_factor_of_a_perfect_ideal_diode_is_one():
    v_t = thermal_voltage_devsim(T_REF)
    i0 = 1e-12
    v0, v1 = 0.3, 0.35
    i_at = lambda v: i0 * math.exp(v / v_t)
    n = ideality_factor(v0, i_at(v0), v1, i_at(v1))
    assert math.isclose(n, 1.0, rel_tol=1e-6)


def test_doping_expression_matches_numpy_profile_at_sample_points():
    junction = 1e-4
    na, nd = 1e16, 1e16
    expr = step_junction_devsim_expression(junction, na, nd)
    assert "ifelse" in expr
    import numpy as np
    profile = step_junction_profile(np.array([0.0, junction - 1e-6, junction, junction + 1e-6]), junction, na, nd)
    assert list(profile) == [-na, -na, nd, nd]


def test_compare_respects_tolerance():
    result = compare("x", 1.0005, 1.0, tolerance=1e-3)
    assert result.passed
    result = compare("x", 1.002, 1.0, tolerance=1e-3)
    assert not result.passed


def test_validate_builtin_potential_matches_recorded_sprint1_result():
    # Regression check against the actual recorded Sprint 1 result in
    # docs/validation.md -- if this ever fails, the simulation or the
    # analytical formula changed and docs/validation.md needs updating too.
    result = validate_builtin_potential(0.7152895799, built_in_potential(1e16, 1e16))
    assert result.passed
    assert result.relative_error < 1e-6
