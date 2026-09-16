"""Sprint 4: low-power trade-off scoring across Sprint 3's parameter
sweeps. Answers the research question in docs/project_manual.md sec 1 by
combining I_ON, I_OFF, and g_m (docs/roadmap.md Sprint 4 deliverable) into
one score per swept configuration, with normalization bounds taken from
the actual Sprint 3 sweep CSVs rather than chosen in advance. See
docs/validation.md Sprint 4 section for the weight rationale and results,
docs/optimization.md for the written interpretation, and
docs/limitations.md for why I_OFF barely differentiates these
configurations.
"""

import csv
import dataclasses
import math
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "results" / "processed"

SWEEPS = {
    "channel_length": "channel_length_cm",
    "oxide_thickness": "oxide_thickness_cm",
    "doping": "channel_doping_cm3",
}

# Low-power weighting, fixed before looking at which configuration would
# "win" under it and never adjusted afterward: leakage (I_OFF) carries the
# most weight since project_manual.md sec 1 frames the research question
# around a low-power trade-off; g_m carries the least weight because a
# low-power design already accepts a softer switching edge in exchange for
# less leakage, so it is the metric this scoring is most willing to
# sacrifice. Weights sum to 1.0.
WEIGHT_ION = 0.3
WEIGHT_IOFF = 0.5
WEIGHT_GM = 0.2


@dataclasses.dataclass
class Configuration:
    sweep: str
    param_name: str
    param_value: float
    vth_V: float
    gm_max_A_per_cm_per_V: float
    i_on_A_per_cm: float
    i_off_A_per_cm: float
    is_baseline: bool


def load_configurations() -> list:
    """Reads every row of the three Sprint 3 `*_sweep_metrics.csv` files,
    deduplicating the shared baseline point: the middle value of every
    sweep is the same Sprint 2 baseline device (L=1e-4 cm, t_ox=1e-6 cm,
    N_A=1e17 cm^-3), re-solved from a fresh DEVSIM session per sweep as
    Sprint 3's reproducibility check -- docs/validation.md confirms all
    three agree to rtol=1e-6, so counting it three times would triple-
    weight one data point in the scoring below."""
    configs = []
    baseline_seen = False
    for sweep, param_name in SWEEPS.items():
        path = PROCESSED_DIR / "{0}_sweep_metrics.csv".format(sweep)
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        mid = len(rows) // 2
        for i, row in enumerate(rows):
            is_baseline = (i == mid)
            if is_baseline:
                if baseline_seen:
                    continue
                baseline_seen = True
            configs.append(Configuration(
                sweep="baseline" if is_baseline else sweep,
                param_name=param_name,
                param_value=float(row[param_name]),
                vth_V=float(row["vth_V"]),
                gm_max_A_per_cm_per_V=float(row["gm_max_A_per_cm_per_V"]),
                i_on_A_per_cm=float(row["i_on_A_per_cm"]),
                i_off_A_per_cm=float(row["i_off_A_per_cm"]),
                is_baseline=is_baseline,
            ))
    return configs


def _minmax_log_normalize(values):
    """0..1 min-max normalization on log10(|value|) -- used for I_ON and
    I_OFF, which each span several decades across these configurations, so
    a linear min-max would let the single largest value dominate."""
    logs = [math.log10(abs(v)) for v in values]
    lo, hi = min(logs), max(logs)
    span = hi - lo
    if span == 0:
        return [0.5 for _ in logs]
    return [(v - lo) / span for v in logs]


def _minmax_normalize(values):
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0:
        return [0.5 for _ in values]
    return [(v - lo) / span for v in values]


def score_configurations(configs: list) -> list:
    """Attaches a low-power trade-off score to every configuration. Higher
    is better. Returns a list of (Configuration, score, ion_norm,
    ioff_norm, gm_norm) tuples. Normalization bounds are the min/max
    across exactly this set of configurations -- they shift if Sprint 3's
    sweep data changes, never hand-picked."""
    ion_norm = _minmax_log_normalize([c.i_on_A_per_cm for c in configs])
    ioff_norm = _minmax_log_normalize([abs(c.i_off_A_per_cm) for c in configs])
    gm_norm = _minmax_normalize([c.gm_max_A_per_cm_per_V for c in configs])

    scored = []
    for c, ion_s, ioff_s, gm_s in zip(configs, ion_norm, ioff_norm, gm_norm):
        score = WEIGHT_ION * ion_s + WEIGHT_IOFF * (1.0 - ioff_s) + WEIGHT_GM * gm_s
        scored.append((c, score, ion_s, ioff_s, gm_s))
    return scored


def save_table_csv(scored: list) -> pathlib.Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = PROCESSED_DIR / "low_power_tradeoff_scores.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "sweep", "param_name", "param_value", "vth_V", "gm_max_A_per_cm_per_V",
            "i_on_A_per_cm", "i_off_A_per_cm", "ion_norm", "ioff_norm", "gm_norm",
            "tradeoff_score", "is_baseline",
        ])
        for c, score, ion_s, ioff_s, gm_s in scored:
            writer.writerow([
                c.sweep, c.param_name, c.param_value, c.vth_V, c.gm_max_A_per_cm_per_V,
                c.i_on_A_per_cm, c.i_off_A_per_cm, ion_s, ioff_s, gm_s, score, c.is_baseline,
            ])
    return out_csv


def main():
    configs = load_configurations()
    scored = score_configurations(configs)
    scored.sort(key=lambda t: t[1], reverse=True)
    out = save_table_csv(scored)
    print("Low-power trade-off ranking (highest score = best low-power trade-off):")
    for c, score, ion_s, ioff_s, gm_s in scored:
        tag = " (baseline)" if c.is_baseline else ""
        print("  {0:<16s} {1:>20s} = {2:<10.4g} score={3:.4f}{4}".format(
            c.sweep, c.param_name, c.param_value, score, tag))
    print("\nSaved:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
