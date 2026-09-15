"""Doping profile generation.

Provides both a NumPy evaluator (for analytical/plotting use) and the
matching DEVSIM symbolic expression string, generated from the same
parameters, so the profile used in analysis and the profile used in the
DEVSIM simulation can never silently drift apart.
"""

import numpy as np


def step_junction_profile(x_cm: np.ndarray, junction_position_cm: float,
                           na_cm3: float, nd_cm3: float) -> np.ndarray:
    """Net doping (N_D - N_A) for an abrupt step junction.

    x < junction_position_cm  -> p-type region, NetDoping = -na_cm3
    x >= junction_position_cm -> n-type region, NetDoping = +nd_cm3
    """
    x_cm = np.asarray(x_cm, dtype=float)
    return np.where(x_cm < junction_position_cm, -na_cm3, nd_cm3)


def step_junction_devsim_expression(junction_position_cm: float,
                                     na_cm3: float, nd_cm3: float) -> str:
    """DEVSIM symbolic expression for the same abrupt step junction, for use
    directly in devsim.python_packages.model_create.CreateNodeModel(...,
    "NetDoping", <this expression>)."""
    return "ifelse(x < {0}, -{1}, {2})".format(junction_position_cm, na_cm3, nd_cm3)
