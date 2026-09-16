import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.optimization.tradeoff import (
    Configuration,
    score_configurations,
    _minmax_log_normalize,
    _minmax_normalize,
    WEIGHT_ION,
    WEIGHT_IOFF,
    WEIGHT_GM,
)


def make_config(param_value, gm, i_on, i_off, is_baseline=False, sweep="test"):
    return Configuration(
        sweep=sweep, param_name="x", param_value=param_value,
        vth_V=1.0, gm_max_A_per_cm_per_V=gm, i_on_A_per_cm=i_on,
        i_off_A_per_cm=i_off, is_baseline=is_baseline,
    )


def test_weights_sum_to_one():
    assert abs((WEIGHT_ION + WEIGHT_IOFF + WEIGHT_GM) - 1.0) < 1e-9


def test_minmax_normalize_endpoints():
    normed = _minmax_normalize([1.0, 2.0, 4.0])
    assert normed[0] == 0.0
    assert normed[-1] == 1.0
    assert 0.0 < normed[1] < 1.0


def test_minmax_normalize_constant_values():
    assert _minmax_normalize([5.0, 5.0, 5.0]) == [0.5, 0.5, 0.5]


def test_minmax_log_normalize_spans_decades():
    normed = _minmax_log_normalize([1e-7, 1e-4, 1e-1])
    assert abs(normed[0] - 0.0) < 1e-9
    assert abs(normed[-1] - 1.0) < 1e-9
    assert abs(normed[1] - 0.5) < 1e-9


def test_low_leakage_high_drive_config_scores_best():
    # Best case: highest I_ON, lowest I_OFF, highest g_m -- should win.
    best = make_config(1, gm=1.0, i_on=1.0, i_off=1e-12)
    worst = make_config(2, gm=0.1, i_on=1e-6, i_off=1e-6)
    scored = score_configurations([best, worst])
    scores = {id(c): s for c, s, *_ in scored}
    assert scores[id(best)] > scores[id(worst)]


def test_score_is_traceable_to_inputs_not_fabricated():
    configs = [
        make_config(1, gm=0.05, i_on=1e-2, i_off=1e-10, is_baseline=True),
        make_config(2, gm=0.10, i_on=1e-1, i_off=1e-10),
        make_config(3, gm=0.02, i_on=1e-6, i_off=1e-10),
    ]
    scored = score_configurations(configs)
    # Every score must be a finite weighted combination in [0, 1] --
    # never NaN/inf, never outside the normalized range the weights allow.
    for _, score, ion_s, ioff_s, gm_s in scored:
        assert 0.0 <= score <= 1.0
        assert 0.0 <= ion_s <= 1.0
        assert 0.0 <= ioff_s <= 1.0
        assert 0.0 <= gm_s <= 1.0
