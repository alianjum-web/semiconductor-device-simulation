"""
Sprint 5: mesh-sensitivity check. Runs the baseline MOSFET's full
characterization (src/simulation/characterization.py, same code path as
Sprint 3's sweeps) twice on the exact same MOSFETParams baseline -- once
at the mesh used by every prior sprint (refine=1.0) and once with every
mesh-line spacing halved (refine=2.0, src/device/mosfet_geometry.py) --
and compares V_TH, I_ON, I_OFF, g_m. See docs/roadmap.md Sprint 5 for
scope and gate criteria.
"""

import csv
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.device.mosfet_geometry import MOSFETParams
from src.simulation.characterization import characterize_device
from src.simulation.mosfet_solver import reset_devsim_clean

PROCESSED_DIR = REPO_ROOT / "results" / "processed"

PARAMS = MOSFETParams()  # same baseline device as Sprint 2/3/4

REL_TOLERANCE = 0.05  # 5% -- a mesh-converged result should not move more than this


def relative_diff(a: float, b: float) -> float:
    scale = max(abs(a), abs(b)) or 1.0
    return abs(a - b) / scale


def main():
    print("Running baseline mesh (refine=1.0)...")
    reset_devsim_clean()
    coarse = characterize_device("mesh_sens_coarse_mesh", "mesh_sens_coarse", PARAMS, refine=1.0)

    print("Running refined mesh (refine=2.0, half the spacing everywhere)...")
    reset_devsim_clean()
    fine = characterize_device("mesh_sens_fine_mesh", "mesh_sens_fine", PARAMS, refine=2.0)

    metrics = ["vth_V", "gm_max_A_per_cm_per_V", "ss_mV_per_decade", "i_on_A_per_cm", "i_off_A_per_cm"]
    rows = []
    print("\nMesh-sensitivity comparison (baseline vs. 2x-refined mesh):")
    all_within_tolerance = True
    for m in metrics:
        c, f = coarse[m], fine[m]
        rel = relative_diff(c, f)
        within = rel <= REL_TOLERANCE
        all_within_tolerance = all_within_tolerance and within
        rows.append((m, c, f, rel, within))
        print("  {0}: baseline={1:.6e}, refined={2:.6e}, rel_diff={3:.4%}, within {4:.0%} tol: {5}".format(
            m, c, f, rel, REL_TOLERANCE, "PASS" if within else "FAIL"))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = PROCESSED_DIR / "mesh_sensitivity.csv"
    with open(out_csv, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["metric", "baseline_mesh", "refined_mesh_2x", "relative_diff", "within_5pct_tolerance"])
        for row in rows:
            writer.writerow(row)
    print("\nWrote", out_csv)

    print("\nSprint 5 mesh-sensitivity gate:", "PASS" if all_within_tolerance else "FAIL")
    return 0 if all_within_tolerance else 1


if __name__ == "__main__":
    raise SystemExit(main())
