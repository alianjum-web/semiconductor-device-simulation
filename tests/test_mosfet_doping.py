import sys
import pathlib

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.device.mosfet_doping import mosfet_netdoping_expression, mosfet_netdoping_profile

X_GATE_LEFT = 5.0e-5
X_GATE_RIGHT = 1.5e-4
Y_JUNCTION = 5.0e-6
NA = 1.0e17
ND = 1.0e20
DECAY = 1.0e-6


def _profile(x, y):
    return mosfet_netdoping_profile(x, y, X_GATE_LEFT, X_GATE_RIGHT, Y_JUNCTION, NA, ND, DECAY, DECAY)


def test_expression_contains_erfc_and_both_dopant_terms():
    expr = mosfet_netdoping_expression(X_GATE_LEFT, X_GATE_RIGHT, Y_JUNCTION, NA, ND, DECAY, DECAY)
    assert expr.count("erfc") == 4
    assert str(ND) in expr
    assert str(NA) in expr


def test_deep_source_region_is_n_type_at_the_doping_magnitude():
    value = _profile(np.array([0.0]), np.array([0.0]))[0]
    assert np.isclose(value, ND - NA, rtol=1e-6)


def test_deep_drain_region_is_n_type_at_the_doping_magnitude():
    value = _profile(np.array([2.0e-4]), np.array([0.0]))[0]
    assert np.isclose(value, ND - NA, rtol=1e-6)


def test_mid_channel_surface_is_p_type_body_doping():
    x_mid = 0.5 * (X_GATE_LEFT + X_GATE_RIGHT)
    value = _profile(np.array([x_mid]), np.array([0.0]))[0]
    assert np.isclose(value, -NA, rtol=1e-6)


def test_doping_vanishes_below_the_junction_depth_in_source_region():
    deep_value = _profile(np.array([0.0]), np.array([Y_JUNCTION + 10 * DECAY]))[0]
    assert np.isclose(deep_value, -NA, rtol=1e-6)
