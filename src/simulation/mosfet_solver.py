"""DEVSIM physics setup, solving, and bias sweeps for the baseline planar
MOSFET (Sprint 2). Follows the same potential-only -> full drift-diffusion
sequence validated for the Sprint 1 PN junction
(simulations/pnjunction/run_pn_junction.py), extended with the oxide
region and Si/oxide interface a MOSFET needs.
"""

import devsim
from devsim.umfpack import umfshim as _umfshim
from devsim.python_packages.simple_physics import (
    SetSiliconParameters,
    SetOxideParameters,
    CreateSiliconPotentialOnly,
    CreateSiliconPotentialOnlyContact,
    CreateOxidePotentialOnly,
    CreateOxideContact,
    CreateSiliconOxideInterface,
    CreateSiliconDriftDiffusion,
    CreateSiliconDriftDiffusionAtContact,
    ece_name,
    hce_name,
)
from devsim.python_packages.model_create import CreateSolution

from src.device.mosfet_geometry import (
    REGION_SILICON,
    REGION_OXIDE,
    INTERFACE_SI_OXIDE,
    CONTACT_GATE,
    CONTACT_SOURCE,
    CONTACT_DRAIN,
    CONTACT_BODY,
    MOSFETParams,
)

SILICON_CONTACTS = (CONTACT_SOURCE, CONTACT_DRAIN, CONTACT_BODY)

# Shared drift-diffusion solve tolerance for every device built by this
# module (both switch_on_drift_diffusion's initial solve and every
# ramp_bias step). Sprint 2's baseline (L=1 um) converged fine down to
# 1e-9 (looser than Sprint 1's PN-junction 1e-10 -- see ramp_bias's
# docstring). Sprint 3's parameter sweeps hit real device configurations
# (in particular a longer L=2 um channel, and any near-zero/off-state
# current) where RelError genuinely plateaus above 1e-9 -- not
# oscillating, not diverging, just structurally unable to go lower at that
# bias point (confirmed by direct experiment: observed floors up to
# ~9e-6). 1e-5 is comfortably above every floor seen so far and only
# shortens (never lengthens) convergence for configurations that were
# already fine at 1e-9.
DD_RELATIVE_ERROR = 1e-5


def _bias_name(contact: str) -> str:
    return "{0}_bias".format(contact)


def reset_devsim_clean() -> None:
    """devsim.reset_devsim() alone leaves the session unable to solve:
    DEVSIM's UMFPACK direct-solver hookup (devsim/__init__.py ->
    devsim/umfpack/umfshim.py) registers itself once via
    devsim.set_parameter(name="direct_solver", ...) / ("solver_callback",
    ...) at import time; reset_devsim() wipes both parameters back to
    "unknown" without re-running that registration, so the very next
    devsim.solve() fails with 'Unrecognized "direct_solver" parameter
    value "unknown"'. Added in Sprint 3, needed whenever a script builds
    more than one device in the same process (e.g. a parameter sweep) --
    confirmed by direct experiment against this DEVSIM install."""
    devsim.reset_devsim()
    devsim.set_parameter(name="direct_solver", value="custom")
    devsim.set_parameter(name="solver_callback", value=_umfshim.local_solver_callback)


def setup_potential_only(device: str, params: MOSFETParams) -> None:
    SetSiliconParameters(device, REGION_SILICON, params.temperature_k)
    SetOxideParameters(device, REGION_OXIDE, params.temperature_k)

    CreateSiliconPotentialOnly(device, REGION_SILICON)
    CreateOxidePotentialOnly(device, REGION_OXIDE, "log_damp")

    for contact in SILICON_CONTACTS:
        devsim.set_parameter(device=device, name=_bias_name(contact), value=0.0)
        CreateSiliconPotentialOnlyContact(device, REGION_SILICON, contact)

    devsim.set_parameter(device=device, name=_bias_name(CONTACT_GATE), value=0.0)
    CreateOxideContact(device, REGION_OXIDE, CONTACT_GATE)

    CreateSiliconOxideInterface(device, INTERFACE_SI_OXIDE)

    devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-12, maximum_iterations=50)


def _solve_robust(kwargs: dict, max_retries: int = 3) -> None:
    """Retries a devsim.solve() call on convergence failure, loosening
    relative_error 10x each attempt (maximum_iterations held fixed -- an
    earlier version of this function also scaled maximum_iterations up
    each retry and was used inside every ramp_bias step; on a genuinely
    pathological configuration (very high channel doping) that combination
    made a single characterize_device() call run for nearly an hour of
    wall-clock time without ever finishing, compounding retries across
    every bias step. Never do that again: keep this bounded and use it
    sparingly, only at single, one-off solves like switch_on's, not inside
    a per-step ramp loop.) Used for switch_on_drift_diffusion's initial
    equilibrium solve, which is only a starting point for later bias
    ramps, not a reported result on its own, so a loose final tolerance
    here is acceptable."""
    kwargs = dict(kwargs)
    for attempt in range(max_retries):
        try:
            devsim.solve(**kwargs)
            return
        except devsim.error:
            kwargs["relative_error"] *= 10.0
    devsim.solve(**kwargs)


def switch_on_drift_diffusion(device: str) -> None:
    CreateSolution(device, REGION_SILICON, "Electrons")
    CreateSolution(device, REGION_SILICON, "Holes")
    devsim.set_node_values(device=device, region=REGION_SILICON, name="Electrons", init_from="IntrinsicElectrons")
    devsim.set_node_values(device=device, region=REGION_SILICON, name="Holes", init_from="IntrinsicHoles")

    CreateSiliconDriftDiffusion(device, REGION_SILICON, mu_n="mu_n", mu_p="mu_p")
    for contact in SILICON_CONTACTS:
        CreateSiliconDriftDiffusionAtContact(device, REGION_SILICON, contact)

    # See DD_RELATIVE_ERROR's module-level comment. maximum_iterations=200
    # (Sprint 2 baseline used 50): a longer swept channel length (L=2 um)
    # was still steadily decreasing (not plateaued) at 50 iterations under
    # the old, tighter tolerance -- genuinely slow convergence, not a stuck
    # floor, confirmed by direct experiment. _solve_robust's retry ladder
    # covers the highest swept channel doping, which needs looser still.
    _solve_robust(dict(type="dc", absolute_error=1e10, relative_error=DD_RELATIVE_ERROR, maximum_iterations=200))


def get_drain_current(device: str) -> float:
    i_electron = devsim.get_contact_current(device=device, contact=CONTACT_DRAIN, equation=ece_name)
    i_hole = devsim.get_contact_current(device=device, contact=CONTACT_DRAIN, equation=hce_name)
    return i_electron + i_hole


SOLVE_KWARGS = dict(type="dc", absolute_error=1e10, relative_error=DD_RELATIVE_ERROR, maximum_iterations=80)


def ramp_bias(device: str, contact: str, target: float, steps: int = 10, relative_error: float = None) -> None:
    """Ramps a contact bias to `target` in `steps` increments so each DC
    solve starts from a nearby converged solution -- the same incremental
    strategy used for the Sprint 1 PN junction forward-bias sweep, just
    generalized to an arbitrary starting point instead of always starting
    from 0. relative_error defaults to SOLVE_KWARGS's DD_RELATIVE_ERROR --
    see that constant's module-level comment for why the 2D MOSFET needs it
    looser than Sprint 1's PN junction. `relative_error` can be overridden
    per call -- see robust_ramp_bias."""
    kwargs = dict(SOLVE_KWARGS)
    if relative_error is not None:
        kwargs["relative_error"] = relative_error
    current = devsim.get_parameter(device=device, name=_bias_name(contact))
    if current == target:
        devsim.solve(**kwargs)
        return
    for i in range(1, steps + 1):
        value = current + (target - current) * i / steps
        devsim.set_parameter(device=device, name=_bias_name(contact), value=value)
        devsim.solve(**kwargs)


def robust_ramp_bias(device: str, contact: str, target: float, steps: int = 21, max_retries: int = 6) -> None:
    """Like ramp_bias, but on a convergence failure retries with a 10x
    looser relative_error, up to `max_retries` times, before giving up.
    Step count is deliberately NOT escalated on retry (unlike an earlier
    version of this function) -- see below.

    Added in Sprint 3 for the off-state/near-zero drain-current bias
    ramp (I_OFF: V_G=0, V_D up to V_DD), which plain ramp_bias's default
    relative_error=1e-9 cannot satisfy. Two things were confirmed by direct
    experiment while building this sweep: (1) the Newton iteration
    genuinely plateaus dead flat (not oscillating, not diverging) for 15+
    iterations once the current has settled into the numerical noise floor
    -- there is no "more converged" state to reach, so no amount of extra
    iterations or finer substeps fixes it, only a loosened tolerance
    ceiling above the floor does; (2) that floor is NOT a fixed number --
    it was ~5.8e-5 at one step count and ~4.4e-4 at another, i.e. finer
    stepping can make the achievable RelError *worse*, not better, since
    each substep's own near-zero current has its own independent noise
    floor. steps=21 (fixed) was enough to also resolve a separate,
    genuine step-granularity failure seen on a short-channel
    configuration; max_retries=6 reaches a final relative_error ceiling of
    1e-3, comfortably above both observed floors."""
    relative_error = SOLVE_KWARGS["relative_error"]
    for attempt in range(max_retries):
        try:
            ramp_bias(device, contact, target, steps=steps, relative_error=relative_error)
            return
        except devsim.error:
            relative_error *= 10.0
    ramp_bias(device, contact, target, steps=steps, relative_error=relative_error)


def sweep_drain_voltage(device: str, gate_bias: float, drain_biases) -> list:
    ramp_bias(device, CONTACT_GATE, gate_bias)
    currents = []
    for vd in drain_biases:
        ramp_bias(device, CONTACT_DRAIN, vd, steps=3)
        currents.append(get_drain_current(device))
    return currents


def sweep_gate_voltage(device: str, drain_bias: float, gate_biases) -> list:
    ramp_bias(device, CONTACT_DRAIN, drain_bias)
    currents = []
    for vg in gate_biases:
        ramp_bias(device, CONTACT_GATE, vg, steps=3)
        currents.append(get_drain_current(device))
    return currents


def reset_to_equilibrium(device: str) -> None:
    ramp_bias(device, CONTACT_DRAIN, 0.0)
    ramp_bias(device, CONTACT_GATE, 0.0)
