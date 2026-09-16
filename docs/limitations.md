# Limitations

This document is filled in as sprints progress; it exists so limitations
are stated explicitly rather than discovered by a reader from the results
alone.

## Scope limitations (fixed from the start — see `project_manual.md` §7)

- 2D device only — no 3D effects (e.g. FinFET/GAA-specific electrostatics).
- Drift-diffusion transport only — no quantum-confinement, no ballistic or
  Monte Carlo transport.
- No fabrication-derived process variation — all parameters are simulation
  inputs, assumed, analytical, or calibrated (see `docs/physics.md` §8),
  never measured from a real fabricated device.
- Generic device parameters — not calibrated against any specific
  commercial foundry process.
- Recombination modeled via SRH only; no optical generation, no impact
  ionization.
- Parameter study limited to three variables (channel length, oxide
  thickness, channel doping) at three values each, per `project_manual.md`
  §4 — not an exhaustive design-space exploration.

## Device modeling limitations

- The baseline MOSFET (Sprint 2) uses an ideal metal gate directly on the
  oxide (`CreateOxideContact`), not a separate doped polysilicon gate
  region. This assumes away gate work-function effects — the model has no
  concept of an n+/p+ poly or metal gate work function offset, so the
  flat-band voltage is whatever the structure's own built-in potential
  gives, not a value tied to a specific real gate material. Recorded as an
  "assumed" simplification per `docs/physics.md` §8.

## Numerical limitations (to be filled in per sprint)

- Mesh resolution and its effect on results: TBD (Sprint 5).
- Convergence behavior / solver tolerances used: Sprint 1 (1D PN junction)
  converged with `relative_error=1e-10`. Sprint 2's 2D MOSFET needed this
  loosened to `relative_error=1e-9` (`src/simulation/mosfet_solver.py`
  `SOLVE_KWARGS`) — at 1e-10 the solver stagnates (oscillates at ~1e-9)
  once the channel is in strong inversion, well past the point where the
  solution has actually settled. Bias sweeps are ramped in small
  increments from the last converged state (`ramp_bias`), the same
  strategy Sprint 1 used for its forward-bias sweep.
- A 2D contact placed at the literal outer edge of DEVSIM's meshed domain
  (no mesh line beyond it) is detected unreliably by DEVSIM's box-mesh
  contact matching — see `docs/validation.md` Sprint 2 section for the
  worked-around gotcha (an unbounded "air" margin around such contacts).
- Any parameter regimes where the solver failed to converge: none observed
  in the Sprint 2 baseline sweeps (V_G, V_D each swept 0–1.0 V). Sprint 3
  found real ones -- see below.
- **Channel doping is numerically bounded well below what this project
  originally planned to sweep.** The Sprint 3 doping sweep's high value
  was narrowed from 1e18 cm⁻³ (then 5e17 cm⁻³) down to 1.5e17 cm⁻³: at the
  higher values, the drift-diffusion Newton iteration falls into chaotic,
  non-decaying RelError oscillation (not a slow-but-steady approach to
  convergence) regardless of `relative_error`, `maximum_iterations`, or
  bias-ramp step count -- one configuration was left running for tens of
  CPU-minutes without ever converging before being killed. This is judged
  a genuine limitation of the simple planar MOSFET model used here (no
  high-doping mobility-degradation model, e.g. no Caughey-Thomas-style
  doping dependence in `mu_n`/`mu_p`), not a solver-setting bug still
  waiting to be found -- see `docs/validation.md` Sprint 3 section for the
  values actually used and why. A future sprint wanting to probe N_A up
  toward 1e18 cm⁻³ would need a doping-dependent mobility model first.
- `src/simulation/mosfet_solver.py`'s shared drift-diffusion tolerance
  (`DD_RELATIVE_ERROR`) was loosened again in Sprint 3, from Sprint 2's
  `1e-9` to `1e-5`, and `switch_on_drift_diffusion`'s `maximum_iterations`
  raised from 50 to 200: swept configurations away from the Sprint 2
  baseline (a longer channel length, and any near-zero/off-state current)
  hit the same kind of stagnation Sprint 2 already found, just further
  along the same curve. `robust_ramp_bias` (used only for the I_ON/I_OFF
  bias ramps, not the general-purpose `ramp_bias`) retries with a 10x
  looser `relative_error` per attempt for cases where even `1e-5` isn't
  enough near a genuinely near-zero current. Full gotcha history in
  `docs/HANDOFF.md`.
- **The Sprint 3 I_OFF noise floor above propagates directly into Sprint
  4's trade-off score.** `src/optimization/tradeoff.py` min-max-normalizes
  I_OFF across the 7 simulated configurations; since all 7 I_OFF values
  sit within the noise floor (varying by under 1 decade, vs. ~6 decades
  for I_ON), that normalization stretches noise to fill the full scoring
  range rather than resolving a real leakage difference. The weighted
  score's ranking is therefore driven almost entirely by I_ON and g_m, not
  by I_OFF, despite I_OFF carrying the largest weight (0.5) in the score's
  definition. Full interpretation in `docs/optimization.md`; this is a
  consequence of the device model having no DIBL/GIDL/punch-through
  mechanism (see the scope limitation above), not a scoring-code bug.
