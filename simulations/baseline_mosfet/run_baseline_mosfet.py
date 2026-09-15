"""
Sprint 2: build the baseline 2D planar NMOS in DEVSIM (geometry, doping,
contacts, mesh), solve Poisson + drift-diffusion + continuity, and produce
first I_D-V_D and I_D-V_G curves. See docs/project_manual.md sec 1/4 and
docs/roadmap.md Sprint 2 for scope and gate criteria.

Device: gate length 1 um, oxide 10 nm, channel doping N_A = 1e17 cm^-3,
source/drain N_D = 1e20 cm^-3 (src/device/mosfet_geometry.py
MOSFETParams defaults). All labeled simulation input / assumed per
docs/physics.md sec 8 -- this is a generic parameterized device, not a
specific commercial process.
"""

import csv
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import devsim

from src.device.mosfet_geometry import (
    build_mosfet,
    MOSFETParams,
    REGION_SILICON,
    CONTACT_GATE,
    CONTACT_DRAIN,
)
from src.simulation.mosfet_solver import (
    setup_potential_only,
    switch_on_drift_diffusion,
    sweep_drain_voltage,
    sweep_gate_voltage,
    reset_to_equilibrium,
)

RAW_DIR = REPO_ROOT / "results" / "raw"
FIGURES_DIR = REPO_ROOT / "results" / "figures"
PROCESSED_DIR = REPO_ROOT / "results" / "processed"

MESH = "baseline_mosfet_mesh"
DEVICE = "baseline_mosfet"

PARAMS = MOSFETParams()

V_DD = 1.0  # assumed supply/reference voltage for this generic device
DRAIN_SWEEP_V = [round(0.1 * i, 2) for i in range(11)]        # 0 .. 1.0 V, at V_G = V_DD
GATE_SWEEP_V = [round(0.05 * i, 2) for i in range(21)]        # 0 .. 1.0 V, at V_D = 0.05 V (linear region)
LINEAR_VD = 0.05


def build_device():
    coords = build_mosfet(MESH, DEVICE, PARAMS)
    setup_potential_only(DEVICE, PARAMS)
    switch_on_drift_diffusion(DEVICE)
    return coords


def save_profile(tag: str):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    x = devsim.get_node_model_values(device=DEVICE, region=REGION_SILICON, name="x")
    y = devsim.get_node_model_values(device=DEVICE, region=REGION_SILICON, name="y")
    potential = devsim.get_node_model_values(device=DEVICE, region=REGION_SILICON, name="Potential")
    electrons = devsim.get_node_model_values(device=DEVICE, region=REGION_SILICON, name="Electrons")
    holes = devsim.get_node_model_values(device=DEVICE, region=REGION_SILICON, name="Holes")
    out_csv = RAW_DIR / "baseline_mosfet_{0}_profile.csv".format(tag)
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["x_cm", "y_cm", "potential_V", "electrons_cm3", "holes_cm3"])
        for row in zip(x, y, potential, electrons, holes):
            writer.writerow(row)
    return out_csv, x, y, potential, electrons, holes


def save_iv(tag: str, sweep_name: str, sweep_values, currents):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = RAW_DIR / "baseline_mosfet_{0}.csv".format(tag)
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([sweep_name, "drain_current_A_per_cm"])
        for v, i in zip(sweep_values, currents):
            writer.writerow([v, i])
    return out_csv


def save_plots(id_vd, id_vg, on_state_profile):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(DRAIN_SWEEP_V, id_vd, marker="o")
    ax.set_xlabel("V_D (V)")
    ax.set_ylabel("I_D (A/cm, per unit device width)")
    ax.set_title("Baseline NMOS output characteristic, V_G = {0} V (Sprint 2)".format(V_DD))
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "baseline_mosfet_id_vd.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy(GATE_SWEEP_V, [max(abs(i), 1e-30) for i in id_vg], marker="o")
    ax.set_xlabel("V_G (V)")
    ax.set_ylabel("|I_D| (A/cm, per unit device width)")
    ax.set_title("Baseline NMOS transfer characteristic, V_D = {0} V (Sprint 2)".format(LINEAR_VD))
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "baseline_mosfet_id_vg.png", dpi=150)
    plt.close(fig)

    x, y, _, electrons, _ = on_state_profile
    fig, ax = plt.subplots(figsize=(7, 4))
    x_um = np.array(x) * 1e4
    y_um = np.array(y) * 1e4
    sc = ax.scatter(x_um, y_um, c=np.log10(np.maximum(electrons, 1.0)), cmap="viridis", s=4)
    ax.invert_yaxis()
    ax.set_xlabel("x (um)")
    ax.set_ylabel("y (um, depth into silicon)")
    ax.set_title("Electron density (log10 cm^-3), V_G={0} V, V_D={1} V (Sprint 2)".format(V_DD, LINEAR_VD))
    fig.colorbar(sc, ax=ax, label="log10(Electrons / cm^-3)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "baseline_mosfet_electron_density.png", dpi=150)
    plt.close(fig)


def check_monotonic_nondecreasing(values, rel_tolerance=1e-6, noise_floor_fraction=1e-6):
    """Allows for numerical noise rather than requiring strict monotonicity.
    Two kinds are expected: (1) genuine off-state leakage/round-off noise,
    where consecutive currents can differ by a large *relative* amount
    while both are far below the on-current -- these pairs are skipped
    entirely via `noise_floor_fraction` of the sweep's max magnitude; (2)
    ordinary solver noise once currents are meaningful, handled by
    `rel_tolerance` relative to the local pair's own scale."""
    global_scale = max(abs(v) for v in values) or 1.0
    noise_floor = noise_floor_fraction * global_scale
    for i in range(1, len(values)):
        if abs(values[i]) < noise_floor and abs(values[i - 1]) < noise_floor:
            continue
        local_scale = max(abs(values[i]), abs(values[i - 1])) or 1.0
        if values[i] < values[i - 1] - rel_tolerance * local_scale:
            return False, i
    return True, None


def channel_surface_max_electrons(profile, x_gate_left, x_gate_right, edge_margin_cm=1.0e-5, surface_depth_cm=5.0e-7):
    """Max electron density in a narrow strip right under the gate, at the
    Si/oxide surface. `edge_margin_cm` excludes the region right at the
    gate edges, where the lateral doping straggle (src/device/mosfet_doping.py)
    still lets source/drain-level doping leak in; without it, the
    heavily-doped (~1e20 cm^-3) source/drain regions would swamp any
    inversion-layer signal in a whole-device max."""
    import numpy as np

    _, x, y, _, electrons, _ = profile
    x = np.asarray(x)
    y = np.asarray(y)
    electrons = np.asarray(electrons)
    mask = (
        (x > x_gate_left + edge_margin_cm)
        & (x < x_gate_right - edge_margin_cm)
        & (y < surface_depth_cm)
    )
    if not mask.any():
        raise ValueError("No mesh nodes found in the mid-channel surface strip -- check geometry/mesh.")
    return float(electrons[mask].max())


def main():
    print("Building baseline MOSFET device...")
    coords = build_device()
    print("Geometry (cm):", coords)

    equilibrium_profile = save_profile("equilibrium")
    print("Equilibrium (zero-bias) profile saved.")

    print("\nRunning I_D-V_D sweep at V_G = {0} V...".format(V_DD))
    id_vd = sweep_drain_voltage(DEVICE, V_DD, DRAIN_SWEEP_V)
    save_iv("id_vd", "drain_bias_V", DRAIN_SWEEP_V, id_vd)
    for v, i in zip(DRAIN_SWEEP_V, id_vd):
        print("  V_D = {0:.2f} V -> I_D = {1:.6e} A/cm".format(v, i))

    reset_to_equilibrium(DEVICE)

    print("\nRunning I_D-V_G sweep at V_D = {0} V...".format(LINEAR_VD))
    id_vg = sweep_gate_voltage(DEVICE, LINEAR_VD, GATE_SWEEP_V)
    save_iv("id_vg", "gate_bias_V", GATE_SWEEP_V, id_vg)
    for v, i in zip(GATE_SWEEP_V, id_vg):
        print("  V_G = {0:.2f} V -> I_D = {1:.6e} A/cm".format(v, i))

    on_state_profile = save_profile("on_state")

    save_plots(id_vd, id_vg, on_state_profile[1:])

    print("\nGate checks:")
    checks = []

    vd_monotonic, bad_i = check_monotonic_nondecreasing(id_vd)
    checks.append(("I_D-V_D non-decreasing with V_D", vd_monotonic))
    print("  I_D-V_D monotonic non-decreasing:", "PASS" if vd_monotonic else "FAIL at index {0}".format(bad_i))

    vg_monotonic, bad_i = check_monotonic_nondecreasing(id_vg)
    checks.append(("I_D-V_G non-decreasing with V_G", vg_monotonic))
    print("  I_D-V_G monotonic non-decreasing:", "PASS" if vg_monotonic else "FAIL at index {0}".format(bad_i))

    finite = all(v == v and abs(v) != float("inf") for v in id_vd + id_vg)  # v == v excludes NaN
    checks.append(("all currents finite (no divergence)", finite))
    print("  All currents finite:", "PASS" if finite else "FAIL")

    on_current = id_vd[-1]
    off_current = id_vg[0]
    inversion_ratio = on_current / off_current if off_current not in (0, 0.0) else float("inf")
    on_off_sensible = on_current > 0 and abs(inversion_ratio) > 1.0
    checks.append(("I_ON > I_OFF (gate turns the channel on)", on_off_sensible))
    print("  I_ON ({0:.3e} A/cm) > I_OFF ({1:.3e} A/cm):".format(on_current, off_current),
          "PASS" if on_off_sensible else "FAIL")

    equilibrium_channel_n = channel_surface_max_electrons(equilibrium_profile, coords["x_gate_left"], coords["x_gate_right"])
    on_state_channel_n = channel_surface_max_electrons(on_state_profile, coords["x_gate_left"], coords["x_gate_right"])
    inversion_forms = on_state_channel_n > 1e3 * equilibrium_channel_n
    checks.append(("channel inversion forms under gate bias", inversion_forms))
    print("  Mid-channel surface electron density: equilibrium = {0:.3e} cm^-3, on-state (V_G={1} V) = {2:.3e} cm^-3:".format(
        equilibrium_channel_n, V_DD, on_state_channel_n), "PASS" if inversion_forms else "FAIL")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_DIR / "baseline_mosfet_gate_summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["check", "passed"])
        for label, passed in checks:
            writer.writerow([label, passed])

    all_passed = all(passed for _, passed in checks)
    print("\nSprint 2 gate:", "PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
