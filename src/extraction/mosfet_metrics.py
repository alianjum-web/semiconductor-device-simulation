"""Automated extraction of MOSFET figures of merit from an I_D-V_G sweep
(Sprint 3). Implements the definitions in docs/physics.md sec 7. Pure NumPy
-- no DEVSIM dependency -- so these are unit-testable against synthetic
curves independently of any simulation run.
"""

import numpy as np


def extract_vth(vg, id_linear, fit_window_v=0.3):
    """Linear extrapolation of I_D vs V_G to I_D = 0, at whatever fixed
    small V_D the caller swept at. Finds the point of maximum dI_D/dV_G
    (the linear-region strong-inversion knee), fits a line through a
    `fit_window_v`-wide window centered there, and extrapolates that line
    to I_D = 0 -- the standard linear-extrapolation V_TH method."""
    vg = np.asarray(vg, dtype=float)
    id_linear = np.asarray(id_linear, dtype=float)
    gm = np.gradient(id_linear, vg)
    peak_i = int(np.argmax(gm))
    lo = vg[peak_i] - fit_window_v / 2.0
    hi = vg[peak_i] + fit_window_v / 2.0
    mask = (vg >= lo) & (vg <= hi)
    if mask.sum() < 2:
        mask = np.zeros_like(vg, dtype=bool)
        lo_i = max(0, peak_i - 1)
        hi_i = min(len(vg), peak_i + 2)
        mask[lo_i:hi_i] = True
    id_window = id_linear[mask]
    # A curve that is flat to floating-point noise has no real slope to
    # extrapolate. Must be checked before polyfit: on a genuinely flat
    # window, polyfit's least-squares slope is pure cancellation noise
    # (~1e-24 scale here) whose *sign* is not stable -- confirmed by this
    # exact case flipping sign between an isolated pytest run and a
    # full-suite run on this machine, so a bare `slope <= 0` check is
    # flaky rather than wrong-but-consistent.
    id_scale = np.max(np.abs(id_window))
    if id_scale == 0 or np.ptp(id_window) <= 1e-9 * id_scale:
        raise ValueError("I_D is flat across the fit window -- cannot extrapolate V_TH.")
    slope, intercept = np.polyfit(vg[mask], id_window, 1)
    if slope <= 0:
        raise ValueError("Non-positive slope at peak-g_m point -- cannot extrapolate V_TH.")
    return -intercept / slope


def extract_gm(vg, id_linear):
    """g_m = dI_D/dV_G, numerically differentiated (docs/physics.md sec 7)."""
    vg = np.asarray(vg, dtype=float)
    id_linear = np.asarray(id_linear, dtype=float)
    return np.gradient(id_linear, vg)


def extract_ss(vg, id_linear, vth, id_floor=1e-18):
    """Subthreshold swing, dV_G / d(log10 I_D), mV/decade (docs/physics.md
    sec 7). Fit over the subthreshold region: V_G < V_TH and I_D above
    `id_floor` (excludes points at/near the numerical noise floor, which
    would otherwise flatten the log-I_D vs V_G slope and bias SS high)."""
    vg = np.asarray(vg, dtype=float)
    id_linear = np.asarray(id_linear, dtype=float)
    mask = (vg < vth) & (id_linear > id_floor)
    if mask.sum() < 2:
        raise ValueError("Not enough subthreshold points above the noise floor to fit SS.")
    log_id = np.log10(id_linear[mask])
    slope, _ = np.polyfit(vg[mask], log_id, 1)
    if slope <= 0:
        raise ValueError("Non-positive d(log10 I_D)/dV_G in subthreshold region -- cannot compute SS.")
    return 1000.0 / slope  # V/decade -> mV/decade


def on_off_ratio(i_on, i_off):
    """I_ON / I_OFF (docs/physics.md sec 7)."""
    if i_off == 0:
        return float("inf")
    return abs(i_on / i_off)
