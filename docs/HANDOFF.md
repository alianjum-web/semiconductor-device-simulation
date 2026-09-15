# Handoff — Read This First In A New Session

This file exists so a session that starts with **no conversation memory**
(after `/clear`) can pick up exactly where the last one left off, without
re-deriving anything or guessing. It is updated at the end of every sprint,
before the conversation is cleared. If you are an agent starting fresh:
read this file, then `docs/roadmap.md`, then get to work — don't re-read
the whole codebase from scratch.

## Where things stand right now

**Sprints 0, 1, and 2 are done and gated. Sprint 3 (device characterization
+ parameter study) is next and has not been started.**

Full detail lives in `docs/roadmap.md` (status + gates) and
`docs/validation.md` (recorded numerical results). This file summarizes
only what's needed to resume work without re-reading everything.

## What has been built so far

- **Environment** (Sprint 0): Python venv at `.venv/`, DEVSIM 2.11.0 +
  NumPy/SciPy/Matplotlib/Pandas installed and verified on this machine
  (Ubuntu 24.04, 8 GB RAM). `scripts/setup.sh` reproduces this from a clean
  clone and runs the Sprint 0 smoke test.
- **Physics validation** (Sprint 1): a 1D PN junction built directly in
  DEVSIM (`simulations/pnjunction/run_pn_junction.py`), validated against
  closed-form analytical formulas (`src/physics/analytical_pnjunction.py`).
  Built-in potential matches to a relative error of 7.2e-14. Forward-bias
  ideality factor ≈ 1.01, matching ideal diode theory.
- **Baseline 2D MOSFET** (Sprint 2): a planar NMOS (L=1um, t_ox=10nm,
  N_A=1e17, N_D=1e20 cm⁻³) built directly in DEVSIM with its own box mesher
  (`src/device/mosfet_geometry.py`, `src/device/mosfet_doping.py`), solved
  with the same potential-only → drift-diffusion sequence as Sprint 1
  (`src/simulation/mosfet_solver.py`), driven by
  `simulations/baseline_mosfet/run_baseline_mosfet.py`. Clean I_D–V_D
  triode-to-saturation curve, clean I_D–V_G subthreshold-to-strong-inversion
  curve across ~11 decades, and a confirmed inversion channel forming at
  the surface under the gate (electron density 9.2e6 → 9.6e17 cm⁻³). All
  gate checks passed — see `docs/validation.md` Sprint 2 section.

## Gotchas found so far (don't rediscover these)

1. DEVSIM's bundled physics module (`devsim.python_packages.simple_physics`)
hardcodes its own rounded constants — `q = 1.6e-19 C`, `k = 1.3806503e-23
J/K`, `eps_si = 11.1` (not 11.7) — instead of CODATA-precise values. Any
analytical formula compared directly against a DEVSIM result must use
these, or the comparison shows a fake ~0.1%+ "error" that's actually just a
constant-definition mismatch. `src/physics/constants.py` has both sets:
plain names (`Q`, `K_B`, `EPS_SI`) are CODATA-precise; `_DEVSIM`-suffixed
names (`Q_DEVSIM`, `K_B_DEVSIM`, `EPS_SI_DEVSIM`) match DEVSIM. Full story
in `docs/physics.md`'s footnote and `docs/validation.md` Sprint 1 section.

2. `devsim.add_2d_mesh_line` requires **both** `ns` and `ps` on every call
(the DEVSIM reference example's own scripts sometimes omit one, but this
DEVSIM install rejects that with "missing required FLOAT parameter").

3. A 2D contact (`add_2d_contact`) placed at the literal outer edge of the
meshed domain — no mesh line, hence no triangle, beyond it in that
direction — is detected unreliably (often 0 or a handful of nodes instead
of the whole intended edge), confirmed by direct experiment against this
DEVSIM install. Fix: wrap every such contact in a thin margin of an
unbounded background region (e.g. `material="Air"`, no xl/xh/yl/yh) so the
mesher always has a real neighboring region on the far side — the same
trick DEVSIM's own bundled MOSFET test example
(`.venv/devsim_data/testing/mos_2d_create.py`) uses via its `air_thickness`
margin. `src/device/mosfet_geometry.py`'s `air_margin_cm` does this for the
gate (top) and body (bottom) contacts; source/drain didn't need it because
the mesh already extends past them toward the gate. Also: any mesh cell not
claimed by an explicit region shows up as "Triangle has no region" and
corrupts nearby contact matching — the same unbounded background region
fixes this too.

4. `relative_error=1e-10` (used for Sprint 1's 1D PN junction) makes the
solver stagnate/oscillate on the 2D MOSFET once the channel reaches strong
inversion — it never converges below ~1e-9 even though the solution has
actually settled well before that. Sprint 2 loosened this to
`relative_error=1e-9` (`src/simulation/mosfet_solver.py` `SOLVE_KWARGS`).

## How the DEVSIM simulations are actually built (reusable pattern for Sprint 3)

This sequence is confirmed working (not guessed) for both the 1D PN
junction and the 2D MOSFET, and will carry over to Sprint 3's sweeps
(same device, just varying L / t_ox / N_A per run):

1. Build mesh: 1D via `create_1d_mesh`/`add_1d_mesh_line`/`add_1d_region`/
   `add_1d_contact`; 2D via `create_2d_mesh`/`add_2d_mesh_line`/
   `add_2d_region`/`add_2d_contact`/`add_2d_interface`. DEVSIM's own box
   mesher was sufficient for the MOSFET too (no Gmsh) — see
   `project_manual.md` §2 and `src/device/mosfet_geometry.py`.
   **`add_2d_mesh_line` needs both `ns` and `ps` every time** (gotcha #2
   above). **Every contact needs a real mesh region on both sides of it,
   including an unbounded "air" region wrapping the domain where nothing
   else is there** (gotcha #3 above) — this cost significant trial-and-error
   time in Sprint 2 and should not need rediscovering.
2. `SetSiliconParameters(device, region, T)` / `SetOxideParameters(device,
   region, T)` from `devsim.python_packages.simple_physics` set
   Permittivity, n_i, V_t, mu_n, mu_p, SRH taus as DEVSIM parameters.
3. Set `NetDoping` via `CreateNodeModel` — a symbolic DEVSIM expression
   string built by a paired numpy/DEVSIM-expression module (see
   `src/physics/doping.py` for the 1D step junction, `src/device/
   mosfet_doping.py` for the 2D erfc-based source/drain profile).
4. Solve **potential-only** first for a good initial guess:
   `CreateSiliconPotentialOnly`/`CreateOxidePotentialOnly` +
   `CreateSiliconPotentialOnlyContact`/`CreateOxideContact` per contact,
   `CreateSiliconOxideInterface` for any Si/oxide interface, then
   `devsim.solve(type="dc", ...)`.
5. Create `Electrons`/`Holes` solutions (`CreateSolution`) in the silicon
   region(s) only, initialize from the potential-only equilibrium guess via
   `devsim.set_node_values(..., init_from="IntrinsicElectrons"/
   "IntrinsicHoles")`.
6. Switch on full transport: `CreateSiliconDriftDiffusion(device, region,
   mu_n=, mu_p=)` (wires Poisson + Bernoulli/Scharfetter-Gummel + SRH +
   electron/hole continuity) and `CreateSiliconDriftDiffusionAtContact` per
   silicon contact. Re-solve.
7. Bias sweeps: ramp each contact's `<contact>_bias` parameter in small
   increments toward the target value (`ramp_bias` in
   `src/simulation/mosfet_solver.py`), re-solving after each increment
   rather than jumping straight to the target — needed for convergence once
   V_G/V_D are more than ~0.1 V from the last converged point. Read current
   via `devsim.get_contact_current(device, contact, equation=ece_name/
   hce_name)`.

**DEVSIM's `mos_physics.py` (element-based 2D current models) turned out
NOT to be needed** — that module is for unstructured triangular (Gmsh)
meshes; DEVSIM's own box mesher (used here, matching DEVSIM's own bundled
MOSFET test example) produces a structured mesh where the ordinary
edge-based `simple_physics` functions above apply directly. Don't reach for
`mos_physics.py` unless Sprint 3+ genuinely needs Gmsh for geometry control
`project_manual.md` §2 doesn't already cover.

## Repository map (see `docs/project_manual.md` §8 for the full intended layout)

```
AGENTS.md                    operating rules (read this in every session)
CLAUDE.md                    pointer to AGENTS.md
docs/
  project_manual.md          scope, physics model, parameters (content, not status)
  physics.md                 equations + analytical formulas + the constants footnote
  roadmap.md                 sprint status + gates (check this first)
  validation.md              recorded numerical-vs-analytical results
  limitations.md             known limitations, filled in as sprints land
  HANDOFF.md                 this file
src/physics/
  constants.py                Q/K_B/EPS_* (CODATA) and Q_DEVSIM/K_B_DEVSIM/EPS_SI_DEVSIM
  semiconductor.py             generic carrier-statistics helpers
  doping.py                    step-junction profile (numpy + matching DEVSIM expression)
  analytical_pnjunction.py     V_bi, depletion width, ideal diode law, ideality factor
  validation.py                compare()/tolerance-gate helpers
src/device/
  mosfet_geometry.py           MOSFETParams, 2D mesh/regions/contacts/interface builder
  mosfet_doping.py             2D erfc source/drain doping (numpy + matching DEVSIM expression)
src/simulation/
  mosfet_solver.py              potential-only setup, drift-diffusion switch-on, bias ramps/sweeps
simulations/
  sprint0_smoke_test/smoke_test.py     Sprint 0 device
  pnjunction/run_pn_junction.py        Sprint 1 device — full working reference implementation
  baseline_mosfet/run_baseline_mosfet.py   Sprint 2 device — full working reference implementation
  channel_length/, oxide_thickness/, doping/   empty, for Sprint 3's sweeps
results/{raw,processed,figures}/       populated by the above scripts; gitignored by default
tests/
  test_environment.py         Sprint 0 gate check
  test_physics.py             Sprint 1 physics unit tests (10 tests, all passing)
  test_mosfet_doping.py       Sprint 2 doping-profile unit tests (5 tests, all passing)
scripts/setup.sh               venv + deps + runs the Sprint 0 smoke test
```

## What Sprint 3 needs to do (from `docs/roadmap.md`, restated briefly)

Turn the Sprint 2 baseline device into a systematic parameter study
(`src/extraction/`, `simulations/{channel_length,oxide_thickness,doping}/`):
automated extraction of V_TH (linear extrapolation of I_D–V_G at fixed
small V_D to I_D=0), I_ON, I_OFF (both per the exact bias points in
`docs/physics.md` §7 — note Sprint 2's informal I_ON/I_OFF check used
different bias points, see `docs/validation.md`), g_m = dI_D/dV_G, and SS
(subthreshold swing); then three 3-value sweeps (channel length, oxide
thickness, channel doping — `docs/project_manual.md` §4), each producing a
CSV under `results/processed/` and plots under `results/figures/`. Gate:
all three sweeps complete, extracted metrics shift in the expected
direction (e.g. V_TH vs. doping), and results reproduce on rerun. Each
sweep run will reuse `src/device/mosfet_geometry.py`/`mosfet_doping.py`/
`src/simulation/mosfet_solver.py` as-is, just varying the relevant
`MOSFETParams` field per run.

## Operating reminders for whoever resumes this

- Read `AGENTS.md` — gate discipline (don't skip/compress sprints),
  anti-hallucination rules (verify DEVSIM calls against the installed
  package before using them, exactly as Sprints 0-2 did), and content
  rules (no scholarship/portfolio language anywhere in this repo).
- After Sprint 3's gate passes: record the result in `docs/roadmap.md` and
  `docs/validation.md` (same style as Sprint 0/1/2 above), update this
  file's "where things stand" section, then tell the user it's safe to
  `/clear`.
