"""
Sprint 0 gate: prove the full pipeline (mesh -> physics -> solve -> save ->
plot) works on this machine before any MOSFET-level code is written.

Device: a trivial 1D doped-silicon bar with two ohmic contacts, solved with
DEVSIM's "potential only" electrostatic model (Poisson equation, no
drift-diffusion transport -- that step is deliberately deferred to Sprint 1,
which validates the full carrier-transport machinery against the PN
junction). See docs/roadmap.md (Sprint 0) and docs/project_manual.md.
"""

import csv
import pathlib

import devsim
from devsim.python_packages.simple_physics import (
    SetSiliconParameters,
    CreateSiliconPotentialOnly,
    CreateSiliconPotentialOnlyContact,
)
from devsim.python_packages.model_create import CreateNodeModel

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "results" / "raw"
FIGURES_DIR = REPO_ROOT / "results" / "figures"

MESH = "sprint0_mesh"
DEVICE = "sprint0_resistor"
REGION = "bar"
LENGTH_CM = 1e-4  # 1 micron bar
DOPING_CM3 = 1e17  # n-type, simulation input (see docs/physics.md sec 8)
BIAS_POINTS = [0.0, 0.25, 0.5, 0.75, 1.0]


def build_device():
    devsim.create_1d_mesh(mesh=MESH)
    devsim.add_1d_mesh_line(mesh=MESH, tag="left", pos=0.0, ps=LENGTH_CM / 100)
    devsim.add_1d_mesh_line(mesh=MESH, tag="right", pos=LENGTH_CM, ps=LENGTH_CM / 100)
    devsim.add_1d_contact(mesh=MESH, name="anode", tag="left", material="metal")
    devsim.add_1d_contact(mesh=MESH, name="cathode", tag="right", material="metal")
    devsim.add_1d_region(mesh=MESH, tag1="left", tag2="right", region=REGION, material="Silicon")
    devsim.finalize_mesh(mesh=MESH)
    devsim.create_device(mesh=MESH, device=DEVICE)

    SetSiliconParameters(DEVICE, REGION, 300)
    CreateNodeModel(DEVICE, REGION, "NetDoping", str(DOPING_CM3))
    CreateSiliconPotentialOnly(DEVICE, REGION)

    for contact in ("anode", "cathode"):
        devsim.set_parameter(device=DEVICE, name="{0}_bias".format(contact), value=0.0)
        CreateSiliconPotentialOnlyContact(DEVICE, REGION, contact)


def run_bias_sweep():
    x = list(devsim.get_node_model_values(device=DEVICE, region=REGION, name="x"))
    profiles = {}
    for bias in BIAS_POINTS:
        devsim.set_parameter(device=DEVICE, name="cathode_bias", value=bias)
        devsim.solve(
            type="dc",
            absolute_error=1.0,
            relative_error=1e-10,
            maximum_iterations=30,
        )
        potential = list(
            devsim.get_node_model_values(device=DEVICE, region=REGION, name="Potential")
        )
        profiles[bias] = potential
        print(
            "cathode_bias={0:.2f} V  ->  potential range [{1:.6f}, {2:.6f}] V".format(
                bias, min(potential), max(potential)
            )
        )
    return x, profiles


def save_results(x, profiles):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = RAW_DIR / "sprint0_smoke_test.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["x_cm"] + ["potential_V_bias_{0:.2f}".format(b) for b in BIAS_POINTS]
        writer.writerow(header)
        for i, xi in enumerate(x):
            row = [xi] + [profiles[b][i] for b in BIAS_POINTS]
            writer.writerow(row)
    print("Saved raw output to", out_csv)
    return out_csv


def save_plot(x, profiles):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_png = FIGURES_DIR / "sprint0_smoke_test.png"

    fig, ax = plt.subplots(figsize=(6, 4))
    for bias in BIAS_POINTS:
        ax.plot([xi * 1e4 for xi in x], profiles[bias], label="V_cathode = {0:.2f} V".format(bias))
    ax.set_xlabel("Position (um)")
    ax.set_ylabel("Potential (V)")
    ax.set_title("Sprint 0 smoke test: 1D doped-Si bar, potential-only solve")
    ax.legend(fontsize="small")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    print("Saved plot to", out_png)
    return out_png


def main():
    build_device()
    x, profiles = run_bias_sweep()
    save_results(x, profiles)
    save_plot(x, profiles)
    print("Sprint 0 smoke test complete.")


if __name__ == "__main__":
    main()
