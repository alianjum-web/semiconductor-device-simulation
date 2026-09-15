"""2D doping profile for the baseline planar MOSFET (Sprint 2).

Net doping is a uniform p-type channel/body concentration overlaid with
n-type source/drain regions that decay smoothly away from the gate edges
and down from the surface (an erfc profile), the same functional form
DEVSIM's own bundled 2D MOSFET test example uses
(.venv/devsim_data/testing/mos_2d_create.py). Decay lengths here are tied
to the junction depth (see src/device/mosfet_geometry.py) rather than the
near-zero values that example uses, so the profile reads as an actual
diffused/implanted junction rather than an idealized abrupt step.

Provides both the DEVSIM symbolic expression (for CreateNodeModel) and a
NumPy evaluator built from the same parameters, so the two can't silently
drift apart -- same pairing convention as src/physics/doping.py.
"""

import numpy as np
from scipy.special import erfc


def mosfet_netdoping_expression(x_gate_left: float, x_gate_right: float, y_junction: float,
                                 na_cm3: float, nd_cm3: float,
                                 x_decay_cm: float, y_decay_cm: float) -> str:
    """DEVSIM symbolic NetDoping expression (donors positive, acceptors
    negative) for use with model_create.CreateNodeModel(..., "NetDoping", ...).
    The 0.25 factor normalizes the product of two erfc terms (each ranging
    0-2) back to a peak of 1 x nd_cm3."""
    source = "0.25*{nd}*erfc((x-{xgl})/{xd})*erfc((y-{yj})/{yd})".format(
        nd=nd_cm3, xgl=x_gate_left, xd=x_decay_cm, yj=y_junction, yd=y_decay_cm)
    drain = "0.25*{nd}*erfc(-(x-{xgr})/{xd})*erfc((y-{yj})/{yd})".format(
        nd=nd_cm3, xgr=x_gate_right, xd=x_decay_cm, yj=y_junction, yd=y_decay_cm)
    return "{0} + {1} - {2}".format(source, drain, na_cm3)


def mosfet_netdoping_profile(x_cm: np.ndarray, y_cm: np.ndarray,
                              x_gate_left: float, x_gate_right: float, y_junction: float,
                              na_cm3: float, nd_cm3: float,
                              x_decay_cm: float, y_decay_cm: float) -> np.ndarray:
    """NumPy evaluator matching mosfet_netdoping_expression exactly, for
    analysis/plotting/tests without needing a DEVSIM session."""
    x_cm = np.asarray(x_cm, dtype=float)
    y_cm = np.asarray(y_cm, dtype=float)
    source = 0.25 * nd_cm3 * erfc((x_cm - x_gate_left) / x_decay_cm) * erfc((y_cm - y_junction) / y_decay_cm)
    drain = 0.25 * nd_cm3 * erfc(-(x_cm - x_gate_right) / x_decay_cm) * erfc((y_cm - y_junction) / y_decay_cm)
    return source + drain - na_cm3
