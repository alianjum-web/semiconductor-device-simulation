import sys
import pathlib

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.extraction.mosfet_metrics import extract_vth, extract_gm, extract_ss, on_off_ratio

VTH_TRUE = 0.42
GM_TRUE = 2.0e-3  # A/cm per V, above threshold
SS_TRUE_MV_DEC = 85.0  # mV/decade, subthreshold


def synthetic_id_vg(vg, vth=VTH_TRUE, gm=GM_TRUE, ss_mv_dec=SS_TRUE_MV_DEC, i_at_vth=1.0e-7):
    """Piecewise curve: exponential subthreshold below V_TH (slope fixed by
    ss_mv_dec, continuous and equal to i_at_vth at V_TH), linear above."""
    vg = np.asarray(vg, dtype=float)
    id_ = np.empty_like(vg)
    below = vg < vth
    decades = (vg[below] - vth) / (ss_mv_dec / 1000.0)
    id_[below] = i_at_vth * 10.0 ** decades
    id_[~below] = i_at_vth + gm * (vg[~below] - vth)
    return id_


def test_extract_vth_recovers_true_threshold_from_linear_region():
    vg = np.round(np.arange(0.0, 1.001, 0.02), 3)
    id_ = synthetic_id_vg(vg)
    vth = extract_vth(vg, id_)
    assert abs(vth - VTH_TRUE) < 0.02


def test_extract_gm_matches_true_slope_in_linear_region():
    vg = np.round(np.arange(0.0, 1.001, 0.02), 3)
    id_ = synthetic_id_vg(vg)
    gm = extract_gm(vg, id_)
    above = vg > VTH_TRUE + 0.1
    assert np.allclose(gm[above], GM_TRUE, rtol=0.05)


def test_extract_ss_recovers_true_subthreshold_swing():
    vg = np.round(np.arange(0.0, 1.001, 0.01), 3)
    id_ = synthetic_id_vg(vg)
    ss = extract_ss(vg, id_, vth=VTH_TRUE)
    assert abs(ss - SS_TRUE_MV_DEC) / SS_TRUE_MV_DEC < 0.05


def test_extract_vth_raises_on_flat_curve():
    vg = np.round(np.arange(0.0, 1.001, 0.02), 3)
    id_ = np.full_like(vg, 1.0e-9)
    try:
        extract_vth(vg, id_)
        assert False, "expected ValueError on non-positive slope"
    except ValueError:
        pass


def test_on_off_ratio_basic():
    assert on_off_ratio(1.0e-3, 1.0e-9) == 1.0e6


def test_on_off_ratio_handles_zero_off_current():
    assert on_off_ratio(1.0e-3, 0.0) == float("inf")
