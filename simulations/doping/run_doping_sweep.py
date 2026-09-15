"""Sprint 3: channel/body doping (N_A) sweep. Varies
MOSFETParams.channel_doping_cm3 across three values around the Sprint 2
baseline (1e17 cm^-3), everything else held fixed. See docs/roadmap.md
Sprint 3 for gate criteria and docs/project_manual.md sec 4 for scope.

Expected direction (the explicit example named in docs/roadmap.md's Sprint
3 gate): V_TH increases with N_A -- docs/physics.md sec 7's V_TH formula
has both phi_F = V_T ln(N_A/n_i) and the body-charge term increasing with
N_A, so V_TH should rise monotonically as channel doping increases.
"""

import csv
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.device.mosfet_geometry import MOSFETParams
from src.simulation.parameter_sweep import (
    run_sweep, check_reproducibility, save_metrics_csv, save_id_vg_csv, save_plots, PROCESSED_DIR,
)

SWEEP_NAME = "doping"
PARAM_FIELD = "channel_doping_cm3"
PARAM_LABEL = "N_A (cm^-3)"
# baseline is the middle value. Order-of-magnitude swings above baseline
# (5e17, 1e18) were tried and dropped: both push the drift-diffusion solve
# into chaotic, non-decaying RelError oscillation (confirmed by direct
# experiment -- one ran for tens of CPU-minutes without ever finishing) --
# a genuinely hard numerical regime for this simple planar MOSFET (no
# high-doping mobility-degradation model), not a fixable tolerance/
# iteration setting. This narrower +/-50% range around baseline was
# confirmed to converge cleanly (each point tested standalone, <5 min) and
# still gives a clear, physically meaningful doping contrast.
VALUES_CM3 = [7.0e16, 1.0e17, 1.5e17]


def main():
    base_params = MOSFETParams()
    results = run_sweep(SWEEP_NAME, PARAM_FIELD, VALUES_CM3, base_params)

    print("\nReproducibility check (rerunning the baseline N_A = 1e17 cm^-3 point)...")
    baseline_result = results[1]
    reproducible = check_reproducibility(SWEEP_NAME, PARAM_FIELD, VALUES_CM3[1], base_params, baseline_result)
    print("  Reproducible:", "PASS" if reproducible else "FAIL")

    save_metrics_csv(SWEEP_NAME, "channel_doping_cm3", results)
    save_id_vg_csv(SWEEP_NAME, "channel_doping_cm3", results)
    save_plots(SWEEP_NAME, "channel_doping_cm3", PARAM_LABEL, results)

    vth = [r["vth_V"] for r in results]
    vth_increases_with_doping = all(vth[i] < vth[i + 1] for i in range(len(vth) - 1))
    print("\nV_TH by N_A (cm^-3):", ["{0:.4f}".format(v) for v in vth])
    print("V_TH strictly increases with increasing channel doping:", "PASS" if vth_increases_with_doping else "FAIL")

    checks = [
        ("reproducible on rerun", reproducible),
        ("V_TH increases with increasing channel doping", vth_increases_with_doping),
    ]

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_DIR / "{0}_sweep_gate_summary.csv".format(SWEEP_NAME), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["check", "passed"])
        for label, passed in checks:
            writer.writerow([label, passed])

    all_passed = all(passed for _, passed in checks)
    print("\nDoping sweep gate:", "PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
