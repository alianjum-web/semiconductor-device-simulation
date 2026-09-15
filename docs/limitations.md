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
  in the Sprint 2 baseline sweeps (V_G, V_D each swept 0–1.0 V).
