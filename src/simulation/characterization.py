"""Runs one full device characterization -- build, solve, extract V_TH,
g_m, SS, I_ON, I_OFF -- for a given MOSFETParams (Sprint 3). Reuses
src/device/mosfet_geometry.py, src/device/mosfet_doping.py, and
src/simulation/mosfet_solver.py exactly as Sprint 2 left them; only the
swept MOSFETParams field changes between calls. See docs/physics.md sec 7
for the extraction definitions and docs/roadmap.md Sprint 3 for scope.
"""

from src.device.mosfet_geometry import build_mosfet, MOSFETParams, CONTACT_GATE, CONTACT_DRAIN
from src.simulation.mosfet_solver import (
    setup_potential_only,
    switch_on_drift_diffusion,
    sweep_gate_voltage,
    ramp_bias,
    robust_ramp_bias,
    get_drain_current,
    reset_to_equilibrium,
    reset_devsim_clean,
)
from src.extraction.mosfet_metrics import extract_vth, extract_gm, extract_ss, on_off_ratio

V_DD = 1.0  # same assumed supply/reference voltage as Sprint 2
LINEAR_VD = 0.05  # same linear-region V_D as Sprint 2's I_D-V_G sweep

# Wider than Sprint 2's 0..1.0 V transfer sweep: some swept configurations
# (e.g. higher channel doping) push V_TH up, and the linear-extrapolation
# V_TH/g_m fit needs the sweep to actually reach the strong-inversion,
# linear-region knee above V_TH, not stop right at it.
GATE_SWEEP_V = [round(0.05 * i, 2) for i in range(31)]  # 0 .. 1.5 V


def characterize_device(mesh_name: str, device_name: str, params: MOSFETParams,
                         v_dd: float = V_DD, linear_vd: float = LINEAR_VD,
                         gate_sweep=GATE_SWEEP_V, refine: float = 1.0) -> dict:
    """Runs the I_D-V_G linear-region sweep used for V_TH/g_m/SS
    extraction, then two extra bias points (V_G=V_D=v_dd for I_ON, V_G=0/
    V_D=v_dd for I_OFF, per docs/physics.md sec 7). Returns a dict of the
    raw sweep and every extracted metric.

    Builds *two* separate devices (mesh_name/device_name for the V_TH
    sweep, "<mesh_name>_ion"/"<device_name>_ion" for I_ON/I_OFF) rather
    than reusing one device for everything: reusing the V_TH-sweep device
    (which is ramped up to gate_sweep's max, 1.5 V, well past v_dd) for the
    I_ON ramp afterward hit a "Convergence failure!" on the baseline
    configuration even with 800+ substeps -- a stagnating Newton iteration
    (relative_error=1e-9 never quite satisfied within maximum_iterations),
    not a step-granularity problem. A device fresh from equilibrium
    converges fine for the exact same v_dd target (this is exactly Sprint
    2's proven I_D-V_D sequence). Confirmed by direct experiment while
    building this sweep.

    `refine` (Sprint 5 mesh-sensitivity check) is passed straight through
    to build_mosfet's own `refine` -- see its docstring."""
    coords = build_mosfet(mesh_name, device_name, params, refine=refine)
    setup_potential_only(device_name, params)
    switch_on_drift_diffusion(device_name)

    id_vg_linear = sweep_gate_voltage(device_name, linear_vd, gate_sweep)

    vth = extract_vth(gate_sweep, id_vg_linear)
    gm = extract_gm(gate_sweep, id_vg_linear)
    ss = extract_ss(gate_sweep, id_vg_linear, vth)

    reset_devsim_clean()
    ion_device = "{0}_ion".format(device_name)
    build_mosfet("{0}_ion".format(mesh_name), ion_device, params, refine=refine)
    setup_potential_only(ion_device, params)
    switch_on_drift_diffusion(ion_device)

    ramp_bias(ion_device, CONTACT_GATE, v_dd)
    robust_ramp_bias(ion_device, CONTACT_DRAIN, v_dd)
    i_on = get_drain_current(ion_device)

    reset_to_equilibrium(ion_device)
    robust_ramp_bias(ion_device, CONTACT_DRAIN, v_dd)
    i_off = get_drain_current(ion_device)

    return {
        "coords": coords,
        "gate_sweep_V": list(gate_sweep),
        "id_vg_linear_A_per_cm": [float(v) for v in id_vg_linear],
        "gm_A_per_cm_per_V": [float(v) for v in gm],
        "vth_V": float(vth),
        "gm_max_A_per_cm_per_V": float(max(gm)),
        "ss_mV_per_decade": float(ss),
        "i_on_A_per_cm": float(i_on),
        "i_off_A_per_cm": float(i_off),
        "ion_ioff_ratio": float(on_off_ratio(i_on, i_off)),
        "v_dd_V": v_dd,
        "linear_vd_V": linear_vd,
    }
