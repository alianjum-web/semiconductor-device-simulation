"""
Sprint 1: build a 1D silicon PN junction in DEVSIM, solve it at equilibrium
and under forward bias, and validate the result against the analytical
formulas in src/physics/analytical_pnjunction.py.

Device: abrupt step junction, N_A = N_D = 1e16 cm^-3, 2 um long, junction at
the midpoint, graded mesh (fine near the junction). See
docs/project_manual.md sec 1 and docs/physics.md sec 3.
"""

import csv
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import devsim
from devsim.python_packages.simple_physics import (
    SetSiliconParameters,
    CreateSiliconPotentialOnly,
    CreateSiliconPotentialOnlyContact,
    CreateSiliconDriftDiffusion,
    CreateSiliconDriftDiffusionAtContact,
    ece_name,
    hce_name,
)
from devsim.python_packages.model_create import CreateNodeModel, CreateSolution

from src.physics.doping import step_junction_devsim_expression
from src.physics.analytical_pnjunction import built_in_potential, ideality_factor
from src.physics.validation import validate_builtin_potential, validate_ideality_factor

RAW_DIR = REPO_ROOT / "results" / "raw"
FIGURES_DIR = REPO_ROOT / "results" / "figures"
PROCESSED_DIR = REPO_ROOT / "results" / "processed"

MESH = "pnjunction_mesh"
DEVICE = "pnjunction"
REGION = "diode_region"

NA_CM3 = 1.0e16
ND_CM3 = 1.0e16
JUNCTION_POSITION_CM = 1.0e-4
DEVICE_LENGTH_CM = 2.0e-4
TEMPERATURE_K = 300.0

FORWARD_BIAS_SWEEP_V = [0.0, 0.1, 0.2, 0.3, 0.35, 0.4, 0.45]


def build_device():
    devsim.create_1d_mesh(mesh=MESH)
    devsim.add_1d_mesh_line(mesh=MESH, tag="left", pos=0.0, ps=2e-6)
    devsim.add_1d_mesh_line(mesh=MESH, pos=JUNCTION_POSITION_CM - 2e-5, ps=2e-6)
    devsim.add_1d_mesh_line(mesh=MESH, tag="junction", pos=JUNCTION_POSITION_CM, ps=2e-8)
    devsim.add_1d_mesh_line(mesh=MESH, pos=JUNCTION_POSITION_CM + 2e-5, ps=2e-6)
    devsim.add_1d_mesh_line(mesh=MESH, tag="right", pos=DEVICE_LENGTH_CM, ps=2e-6)
    devsim.add_1d_contact(mesh=MESH, name="anode", tag="left", material="metal")
    devsim.add_1d_contact(mesh=MESH, name="cathode", tag="right", material="metal")
    devsim.add_1d_region(mesh=MESH, tag1="left", tag2="right", region=REGION, material="Silicon")
    devsim.finalize_mesh(mesh=MESH)
    devsim.create_device(mesh=MESH, device=DEVICE)

    SetSiliconParameters(DEVICE, REGION, TEMPERATURE_K)
    doping_expr = step_junction_devsim_expression(JUNCTION_POSITION_CM, NA_CM3, ND_CM3)
    CreateNodeModel(DEVICE, REGION, "NetDoping", doping_expr)


def solve_to_equilibrium():
    """Potential-only solve for a good initial guess, then switch on full
    drift-diffusion transport and re-solve at zero bias."""
    CreateSiliconPotentialOnly(DEVICE, REGION)
    for contact in ("anode", "cathode"):
        devsim.set_parameter(device=DEVICE, name="{0}_bias".format(contact), value=0.0)
        CreateSiliconPotentialOnlyContact(DEVICE, REGION, contact)
    devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-12, maximum_iterations=50)

    CreateSolution(DEVICE, REGION, "Electrons")
    CreateSolution(DEVICE, REGION, "Holes")
    devsim.set_node_values(device=DEVICE, region=REGION, name="Electrons", init_from="IntrinsicElectrons")
    devsim.set_node_values(device=DEVICE, region=REGION, name="Holes", init_from="IntrinsicHoles")

    CreateSiliconDriftDiffusion(DEVICE, REGION, mu_n="mu_n", mu_p="mu_p")
    for contact in ("anode", "cathode"):
        CreateSiliconDriftDiffusionAtContact(DEVICE, REGION, contact)
    devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-10, maximum_iterations=50)


def get_numerical_builtin_potential():
    potential = devsim.get_node_model_values(device=DEVICE, region=REGION, name="Potential")
    return max(potential) - min(potential)


def run_forward_bias_sweep():
    currents = []
    for bias in FORWARD_BIAS_SWEEP_V:
        devsim.set_parameter(device=DEVICE, name="anode_bias", value=bias)
        devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-10, maximum_iterations=50)
        i_electron = devsim.get_contact_current(device=DEVICE, contact="anode", equation=ece_name)
        i_hole = devsim.get_contact_current(device=DEVICE, contact="anode", equation=hce_name)
        currents.append(i_electron + i_hole)
    devsim.set_parameter(device=DEVICE, name="anode_bias", value=0.0)  # restore equilibrium
    devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-10, maximum_iterations=50)
    return currents


def save_equilibrium_profile():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    x = devsim.get_node_model_values(device=DEVICE, region=REGION, name="x")
    potential = devsim.get_node_model_values(device=DEVICE, region=REGION, name="Potential")
    electrons = devsim.get_node_model_values(device=DEVICE, region=REGION, name="Electrons")
    holes = devsim.get_node_model_values(device=DEVICE, region=REGION, name="Holes")
    out_csv = RAW_DIR / "pnjunction_equilibrium_profile.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["x_cm", "potential_V", "electrons_cm3", "holes_cm3"])
        for row in zip(x, potential, electrons, holes):
            writer.writerow(row)
    return out_csv, x, potential, electrons, holes


def save_iv_sweep(currents):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = RAW_DIR / "pnjunction_forward_iv.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["anode_bias_V", "current_A_per_cm2"])
        for v, i in zip(FORWARD_BIAS_SWEEP_V, currents):
            writer.writerow([v, i])
    return out_csv


def save_plots(x, potential, electrons, holes, currents):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([xi * 1e4 for xi in x], potential)
    ax.set_xlabel("Position (um)")
    ax.set_ylabel("Potential (V)")
    ax.set_title("PN junction equilibrium potential (Sprint 1)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "pnjunction_potential_profile.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy([xi * 1e4 for xi in x], electrons, label="Electrons")
    ax.semilogy([xi * 1e4 for xi in x], holes, label="Holes")
    ax.set_xlabel("Position (um)")
    ax.set_ylabel("Carrier concentration (cm^-3)")
    ax.set_title("PN junction equilibrium carrier profiles (Sprint 1)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "pnjunction_carrier_profiles.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy(FORWARD_BIAS_SWEEP_V, [abs(i) for i in currents], marker="o")
    ax.set_xlabel("Anode bias (V)")
    ax.set_ylabel("Current density (A/cm^2)")
    ax.set_title("PN junction forward I-V (Sprint 1)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "pnjunction_forward_iv.png", dpi=150)
    plt.close(fig)


def main():
    build_device()
    solve_to_equilibrium()

    numerical_vbi = get_numerical_builtin_potential()
    analytical_vbi = built_in_potential(NA_CM3, ND_CM3, TEMPERATURE_K)
    vbi_result = validate_builtin_potential(numerical_vbi, analytical_vbi)
    print("V_bi numerical  = {0:.10f} V".format(vbi_result.numerical))
    print("V_bi analytical = {0:.10f} V".format(vbi_result.analytical))
    print("relative error  = {0:.3e}  (tolerance {1:.1e})  -> {2}".format(
        vbi_result.relative_error, vbi_result.tolerance,
        "PASS" if vbi_result.passed else "FAIL"))

    _, x, potential, electrons, holes = save_equilibrium_profile()
    currents = run_forward_bias_sweep()
    save_iv_sweep(currents)
    save_plots(x, potential, electrons, holes, currents)

    print("\nForward-bias ideality factor (mid-range, should be ~1.0):")
    ideality_results = []
    for i in range(2, len(FORWARD_BIAS_SWEEP_V)):
        v0, i0 = FORWARD_BIAS_SWEEP_V[i - 1], currents[i - 1]
        v1, i1 = FORWARD_BIAS_SWEEP_V[i], currents[i]
        n = ideality_factor(v0, i0, v1, i1, TEMPERATURE_K)
        result = validate_ideality_factor(n)
        ideality_results.append(result)
        print("  {0:.2f}V -> {1:.2f}V : n = {2:.4f}  -> {3}".format(
            v0, v1, n, "PASS" if result.passed else "FAIL"))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_DIR / "pnjunction_validation_summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["check", "numerical", "analytical", "relative_error", "tolerance", "passed"])
        writer.writerow([vbi_result.label, vbi_result.numerical, vbi_result.analytical,
                          vbi_result.relative_error, vbi_result.tolerance, vbi_result.passed])
        for r in ideality_results:
            writer.writerow([r.label, r.numerical, r.analytical, r.relative_error, r.tolerance, r.passed])

    all_passed = vbi_result.passed and all(r.passed for r in ideality_results)
    print("\nSprint 1 gate:", "PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
