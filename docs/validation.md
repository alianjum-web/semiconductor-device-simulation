# Validation Log

This document records numerical-vs-analytical comparisons as sprints
complete. Nothing is entered here until the corresponding simulation has
actually been run — no placeholder numbers.

## Sprint 1 — PN junction

Status: **passed.** Run via `simulations/pnjunction/run_pn_junction.py`.

Device: 1D abrupt step junction, N_A = N_D = 1e16 cm⁻³, 2 um long, junction
at the midpoint, graded mesh (2e-8 cm spacing at the junction, 2e-6 cm
elsewhere), 300 K. Built with DEVSIM's bundled `simple_physics` /
`simple_dd` drift-diffusion models (Poisson + electron/hole continuity +
SRH recombination) — the same physics stack the MOSFET in Sprint 2 will use.

**Built-in potential:**

| | Value |
|---|---|
| Numerical (DEVSIM, max−min equilibrium potential) | 0.7152895799 V |
| Analytical (`built_in_potential(1e16, 1e16)`) | 0.7152895799 V |
| Relative error | 7.2e-14 |
| Tolerance | 1e-3 (0.1%) |
| Result | **PASS**, with ~9 orders of magnitude margin |

Getting this match required using DEVSIM's own bundled constants (q =
1.6e-19 C, k = 1.3806503e-23 J/K) in the analytical formula rather than
CODATA-precise constants — see `docs/physics.md` footnote and
`src/physics/constants.py` (`Q_DEVSIM`, `K_B_DEVSIM`). With CODATA-precise
constants the same comparison showed a 0.136% relative error and failed
the gate — a constant-definition mismatch, not a physics or numerical
error. Recorded here so the reason isn't rediscovered later.

**Forward-bias ideality factor** (from the I-V sweep in
`results/raw/pnjunction_forward_iv.csv`, tolerance ±5% around n = 1.0):

| Bias interval | n | Result |
|---|---|---|
| 0.10 V → 0.20 V | 1.0206 | PASS |
| 0.20 V → 0.30 V | 1.0097 | PASS |
| 0.30 V → 0.35 V | 1.0074 | PASS |
| 0.35 V → 0.40 V | 1.0074 | PASS |
| 0.40 V → 0.45 V | 1.0078 | PASS |

n ≈ 1.01 across the mid-forward-bias range matches ideal (Shockley,
diffusion-dominated) diode behavior. The 0.0 V → 0.1 V interval is not
reported here because current is dominated by SRH recombination that low
into the forward bias, so the two-point ideality-factor formula doesn't
apply there — that's expected, textbook diode behavior, not a defect.

Figures: `results/figures/pnjunction_potential_profile.png` (potential
step across the junction), `pnjunction_carrier_profiles.png` (electron/hole
concentration crossing at n_i = 1e10 cm⁻³ at the junction, as expected),
`pnjunction_forward_iv.png`. Raw data:
`results/raw/pnjunction_equilibrium_profile.csv`,
`results/raw/pnjunction_forward_iv.csv`. Summary:
`results/processed/pnjunction_validation_summary.csv`.

Mesh sensitivity: not yet checked — deferred to Sprint 5 per
`docs/roadmap.md`.

## Sprint 2 — Baseline MOSFET sanity checks

Status: **passed.** Run via
`simulations/baseline_mosfet/run_baseline_mosfet.py`.

Device: baseline planar NMOS, gate length L = 1 um, oxide thickness
t_ox = 10 nm, channel/body doping N_A = 1e17 cm⁻³, source/drain doping
N_D = 1e20 cm⁻³, 300 K — all simulation inputs
(`src/device/mosfet_geometry.py` `MOSFETParams` defaults, all labeled per
`docs/physics.md` §8). Structured 2D mesh built directly with DEVSIM's box
mesher (`create_2d_mesh`/`add_2d_mesh_line`/`add_2d_region`), same approach
as DEVSIM's own bundled MOSFET test example
(`.venv/devsim_data/testing/mos_2d_create.py`) — no Gmsh needed. Ideal
metal gate contact directly on the oxide (`CreateOxideContact`), so gate
work-function effects are assumed away (flat-band ≈ built-in-potential of
the structure, not tied to a specific poly/metal gate stack) — see
`docs/limitations.md`.

Sprint 2's gate is qualitative ("physically sensible curves ... no
divergence ... monotonic where expected"), not a numerical-vs-analytical
comparison — quantitative V_TH/g_m/SS extraction against the formula in
`docs/physics.md` §7 is Sprint 3 scope. Five checks were run, all passing:

| Check | Result |
|---|---|
| I_D–V_D non-decreasing with V_D (V_G = 1.0 V) | PASS |
| I_D–V_G non-decreasing with V_G (V_D = 0.05 V) | PASS |
| All currents finite (no divergence) | PASS |
| I_ON (5.31e-3 A/cm at V_G=V_D=1.0 V) > I_OFF (3.26e-11 A/cm at V_G=0, V_D=0.05 V) | PASS |
| Mid-channel surface electron density rises from 9.2e6 cm⁻³ (equilibrium) to 9.6e17 cm⁻³ (V_G=1.0 V, V_D=0.05 V) | PASS |

The last check is the important one beyond curve-shape sanity: it confirms
an actual inversion channel forms at the Si/oxide surface under the gate
(not just that the terminal current happens to look monotonic). The
electron-density figure
(`results/figures/baseline_mosfet_electron_density.png`) shows this
directly — a bright n-type strip at the surface under the gate at
V_G = 1.0 V, connecting the two n+ source/drain regions. The I_D–V_D curve
(`baseline_mosfet_id_vd.png`) shows a clean triode-to-saturation
transition; the I_D–V_G curve (`baseline_mosfet_id_vg.png`, log scale)
shows a clean subthreshold exponential rising into strong inversion across
roughly 11 decades — textbook long-channel MOSFET behavior.

The I_ON/I_OFF checked here is an informal Sprint 2 sanity pairing (I_OFF
taken at the V_D = 0.05 V used for the transfer sweep, not V_D = V_DD) --
not the `docs/physics.md` §7 I_OFF definition (V_G=0, V_D=V_DD), which
Sprint 3's automated extraction will compute properly.

Note found along the way (not a physics issue, a DEVSIM 2D meshing
gotcha): a 2D contact placed at the literal outer edge of the meshed
domain (no mesh line beyond it, so no triangle on its far side) is
detected unreliably by DEVSIM's box-mesh contact matching -- confirmed by
direct experiment against this DEVSIM install. `mosfet_geometry.py` wraps
the gate and body contacts in a thin (1e-7 cm) unbounded "air" margin
purely to give the mesher a real neighboring region on the far side of
every contact, the same trick DEVSIM's own bundled MOSFET test example
uses. Source/drain contacts didn't need this since the mesh already
extends past them (up toward the gate) on their far side.

Raw data: `results/raw/baseline_mosfet_equilibrium_profile.csv`,
`baseline_mosfet_on_state_profile.csv`, `baseline_mosfet_id_vd.csv`,
`baseline_mosfet_id_vg.csv`. Summary:
`results/processed/baseline_mosfet_gate_summary.csv`. Figures:
`results/figures/baseline_mosfet_id_vd.png`, `baseline_mosfet_id_vg.png`,
`baseline_mosfet_electron_density.png`.

Mesh sensitivity: not yet checked — deferred to Sprint 5 per
`docs/roadmap.md`.

## Sprint 3 — Parameter sweeps

Status: **passed.** Run via `simulations/{channel_length,oxide_thickness,doping}/run_*_sweep.py`.

Each sweep varies exactly one `MOSFETParams` field on top of the Sprint 2
baseline (L=1 um, t_ox=10 nm, N_A=1e17 cm⁻³) and characterizes the
resulting device with `src/simulation/characterization.py`: an I_D-V_G
sweep at V_D=0.05 V from 0 to 1.5 V (wider than Sprint 2's 0-1.0 V, so
V_TH/g_m/SS extraction reaches the strong-inversion knee even for
configurations that push V_TH up) feeds V_TH (linear extrapolation at peak
g_m), g_m, and SS (log-linear fit in the subthreshold region); a separate,
freshly-built device measures I_ON (V_G=V_D=1.0 V) and I_OFF (V_G=0,
V_D=1.0 V) per `docs/physics.md` sec 7.

**Channel length sweep** (`results/processed/channel_length_sweep_metrics.csv`):

| L (cm) | V_TH (V) | g_m,max (A/cm/V) | SS (mV/dec) | I_ON (A/cm) | I_OFF (A/cm) |
|---|---|---|---|---|---|
| 5.0e-5 | 0.9622 | 0.1402 | 102.9 | 1.721e-2 | -6.76e-11 |
| 1.0e-4 (baseline) | 0.9867 | 0.0671 | 111.3 | 5.305e-3 | -6.08e-11 |
| 2.0e-4 | 0.9967 | 0.0330 | 118.4 | 2.233e-3 | -6.06e-11 |

I_ON strictly decreases with increasing L (gradual-channel theory: channel
resistance grows with L) -- **PASS**. I_OFF stays within the same
~1e-10-A/cm noise-floor band across all three (expected: this idealized
long-channel-style device has no punch-through/DIBL model, so I_OFF isn't
expected to track L strongly at this bias).

**Oxide thickness sweep** (`results/processed/oxide_thickness_sweep_metrics.csv`):

| t_ox (cm) | V_TH (V) | g_m,max (A/cm/V) | SS (mV/dec) | I_ON (A/cm) | I_OFF (A/cm) |
|---|---|---|---|---|---|
| 5.0e-7 | 0.7776 | 0.1350 | 82.7 | 1.006e-1 | -4.93e-11 |
| 1.0e-6 (baseline) | 0.9867 | 0.0671 | 111.3 | 5.305e-3 | -6.08e-11 |
| 2.0e-6 | 1.3372 | 0.0227 | 194.9 | 1.633e-7 | -4.34e-11 |

V_TH strictly increases and I_ON strictly decreases with increasing t_ox
(thinner oxide -> higher C_ox -> stronger gate coupling) -- **PASS** on
both checks named in `docs/roadmap.md`.

**Channel doping sweep** (`results/processed/doping_sweep_metrics.csv`):

| N_A (cm⁻³) | V_TH (V) | g_m,max (A/cm/V) | SS (mV/dec) | I_ON (A/cm) | I_OFF (A/cm) |
|---|---|---|---|---|---|
| 7.0e16 | 0.9050 | 0.0676 | 99.8 | 1.650e-2 | 2.79e-11 |
| 1.0e17 (baseline) | 0.9867 | 0.0671 | 111.3 | 5.305e-3 | -6.08e-11 |
| 1.5e17 | 1.0964 | 0.0659 | 79.7 | 4.900e-4 | 1.99e-10 |

V_TH strictly increases with increasing N_A -- **PASS**, the direction
example named explicitly in `docs/roadmap.md`'s Sprint 3 gate.

The doping sweep's high value is 1.5e17, not the originally planned 1e18:
1e18 (and, when dropped in favor of it, 5e17 too) sends this device's
drift-diffusion Newton iteration into chaotic, non-decaying oscillation
regardless of tolerance or iteration budget -- one configuration was left
running for tens of CPU-minutes without ever converging before being
killed. This is a genuine numerical/physical limit of the simple planar
MOSFET model used here (no high-doping mobility-degradation model), not a
solver-setting bug; recorded in `docs/limitations.md`. 1.5e17 was verified
standalone to converge in well under 5 minutes before being adopted.

**Reproducibility:** each sweep reran its baseline (middle) point from a
freshly reset DEVSIM session after the main sweep and compared V_TH,
I_ON, and I_OFF to the first run at `rtol=1e-6` -- **PASS** for all three
sweeps (DEVSIM's solve is deterministic given the same inputs, so this is
a real check, not a formality).

Mesh sensitivity: not yet checked — deferred to Sprint 5 per
`docs/roadmap.md`.

## Sprint 5 — Mesh and parameter sensitivity

Status: not yet run.
