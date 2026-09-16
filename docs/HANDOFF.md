# Handoff — Read This First In A New Session

This file exists so a session that starts with **no conversation memory**
(after `/clear`) can pick up exactly where the last one left off, without
re-deriving anything or guessing. It is updated at the end of every sprint,
before the conversation is cleared. If you are an agent starting fresh:
read this file, then `docs/roadmap.md`, then get to work — don't re-read
the whole codebase from scratch.

## Where things stand right now

**Sprints 0, 1, 2, 3, and 4 are done and gated. Sprint 5 (validation +
documentation packaging) is next and has not been started.**

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
- **Parameter sweeps + automated extraction** (Sprint 3): V_TH/g_m/SS/I_ON/
  I_OFF extraction (`src/extraction/mosfet_metrics.py`, unit-tested against
  synthetic curves in `tests/test_extraction.py`), a per-value device
  characterization runner (`src/simulation/characterization.py`) and shared
  sweep plumbing (`src/simulation/parameter_sweep.py`), driven by
  `simulations/{channel_length,oxide_thickness,doping}/run_*_sweep.py`.
  All three sweeps passed their gates: I_ON decreases with channel length;
  V_TH increases and I_ON decreases with oxide thickness; V_TH increases
  with channel doping. All three reproduced on rerun (rtol=1e-6). Full
  numbers in `docs/validation.md` Sprint 3 section. The doping sweep's
  high value ended up much closer to baseline than planned (1.5e17 cm⁻³,
  not 1e18) — see gotcha #8 below and `docs/limitations.md` before trying
  to push channel doping further in a later sprint.
- **Low-power trade-off scoring** (Sprint 4): `src/optimization/tradeoff.py`
  scores the 7 unique Sprint 3 configurations (baseline + 2 swept values
  each for L/t_ox/N_A) on a weighted, normalized combination of I_ON,
  I_OFF, and g_m — see `docs/optimization.md` for the full result table and
  written interpretation, `docs/roadmap.md` Sprint 4 section for the
  summary. Headline finding: I_OFF varies by under 1 decade across all 7
  configurations (inside this solver's numerical noise floor — gotcha #7
  below), so the score's leakage term doesn't resolve a real signal; the
  ranking is driven almost entirely by I_ON and g_m, which do vary by real,
  multi-decade margins. Best-supported low-power answer from raw I_ON/g_m
  alone: t_ox=2e-6 cm (20 nm) has this dataset's lowest I_ON and g_m.
  `tests/test_optimization.py` (6 tests) covers the scoring/normalization
  logic against synthetic data, no DEVSIM needed.

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
Sprint 3 found this same stagnation pattern recurs at ever-looser floors
for swept configurations away from the baseline (gotcha #7 below) —
`SOLVE_KWARGS`'s `relative_error` (renamed `DD_RELATIVE_ERROR`) is now
`1e-5`, not `1e-9`.

5. `devsim.reset_devsim()` alone is not enough to build a second device in
the same process (needed for any sweep that runs multiple parameter
values without restarting Python): it resets DEVSIM's UMFPACK
direct-solver hookup (`direct_solver`/`solver_callback` parameters, set at
import time by `devsim/__init__.py` → `devsim/umfpack/umfshim.py`) back to
`"unknown"`, and the next `devsim.solve()` fails with `Unrecognized
"direct_solver" parameter value "unknown"`. Fix: re-set both parameters
from the already-imported `umfshim` module right after every
`reset_devsim()` — `src/simulation/mosfet_solver.py`'s
`reset_devsim_clean()` does this; always call it, never bare
`devsim.reset_devsim()`, when a script builds more than one device.

6. Reusing one live device across very different bias regimes in the same
DEVSIM session is fragile even with `reset_devsim_clean()` between
*different* devices — reusing the *same* device for a wide V_TH-extraction
gate sweep (0–1.5 V) and then immediately ramping it to V_G=V_D=V_DD for
I_ON hit a "Convergence failure!" on the baseline configuration even at
800+ substeps, while a device built fresh from equilibrium converges fine
for the identical V_DD target. `characterize_device` now builds two
separate devices per parameter value — one for the V_TH sweep, one fresh
one for I_ON/I_OFF — rather than reusing one for everything.

7. Near-zero/off-state drain current (I_OFF: V_G=0, V_D up to V_DD) can
make a Newton iteration plateau dead flat for 15+ iterations at a
RelError floor well above whatever `relative_error` is set to — not
oscillating, not diverging, genuinely stuck, because at a near-zero true
current even tiny absolute fluctuations look like large relative ones.
That floor is **not a fixed number** — it was ~5.8e-5 at one step count
and ~4.4e-4 at another on the same device, so finer bias-ramp stepping can
make the achievable RelError *worse*, not better. Fix used only for the
I_ON/I_OFF drain ramp (not the general-purpose `ramp_bias`):
`robust_ramp_bias` (`src/simulation/mosfet_solver.py`) retries the same
ramp with `relative_error` loosened 10x per attempt (step count held
fixed) up to a ceiling of `1e-3`.

8. **Channel doping has a hard numerical ceiling well below what this
project originally planned to sweep**, and this cost real wall-clock time
(one configuration was left running for tens of CPU-minutes, pinning a
CPU core, before being killed — don't let a "just retry with a looser
tolerance" fix run unbounded like that again). At N_A=5e17 and 1e18 cm⁻³,
the drift-diffusion Newton iteration falls into **chaotic, non-decaying
RelError oscillation** — not slow convergence, not a stagnant floor, a
value that bounces by 1-2 orders of magnitude iteration to iteration with
no decaying trend. No `relative_error`/`maximum_iterations` combination
tried fixed this; it's treated as a genuine limitation of this simple
planar MOSFET model (no doping-dependent mobility degradation), not a
solver-setting bug — see `docs/limitations.md`. The doping sweep actually
run uses `[7e16, 1e17, 1.5e17]`, each individually confirmed to converge
in well under 5 minutes before being adopted. **If a later sprint wants
higher channel doping, verify convergence on a single standalone point
first (with a hard wall-clock `timeout` wrapper), before wiring it into a
sweep script that will retry indefinitely.**

9. `extract_vth`'s "flat curve should raise" guard (`src/extraction/
mosfet_metrics.py`) originally checked only `slope <= 0` after
`np.polyfit` on a perfectly flat I_D window. On an exactly-flat curve the
fitted slope is pure floating-point cancellation noise (~1e-24 scale here)
whose *sign* is not stable — `tests/test_extraction.py::
test_extract_vth_raises_on_flat_curve` passed in isolation but failed when
run after other tests in the same `pytest` process (importing DEVSIM's
compiled extension earlier evidently shifts which numpy SIMD code path
gets used, flipping the noise's sign). Fixed by checking the fit window's
actual peak-to-peak I_D range against its scale (`np.ptp(id_window) <=
1e-9 * id_scale`) *before* trusting the fitted slope's sign — verified
stable across repeated full-suite runs.

## How the DEVSIM simulations are actually built (reusable pattern, confirmed through Sprint 3)

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
  characterization.py           Sprint 3: one full V_TH/g_m/SS/I_ON/I_OFF characterization per device
  parameter_sweep.py            Sprint 3: shared per-value run + CSV/plot/reproducibility plumbing
src/extraction/
  mosfet_metrics.py             Sprint 3: V_TH/g_m/SS/I_ON-I_OFF-ratio extraction, pure NumPy
src/optimization/
  tradeoff.py                   Sprint 4: weighted I_ON/I_OFF/g_m trade-off score, pure Python
simulations/
  sprint0_smoke_test/smoke_test.py     Sprint 0 device
  pnjunction/run_pn_junction.py        Sprint 1 device — full working reference implementation
  baseline_mosfet/run_baseline_mosfet.py   Sprint 2 device — full working reference implementation
  channel_length/run_channel_length_sweep.py   Sprint 3 sweep A
  oxide_thickness/run_oxide_thickness_sweep.py Sprint 3 sweep B
  doping/run_doping_sweep.py                   Sprint 3 sweep C
results/{raw,processed,figures}/       populated by the above scripts; gitignored by default
tests/
  test_environment.py         Sprint 0 gate check
  test_physics.py             Sprint 1 physics unit tests (10 tests, all passing)
  test_mosfet_doping.py       Sprint 2 doping-profile unit tests (5 tests, all passing)
  test_extraction.py          Sprint 3 extraction unit tests (6 tests, all passing)
  test_optimization.py        Sprint 4 trade-off scoring unit tests (6 tests, all passing)
scripts/setup.sh               venv + deps + runs the Sprint 0 smoke test
docs/optimization.md           Sprint 4 written interpretation (result table + research-question answer)
```

## What Sprint 5 needs to do (from `docs/roadmap.md`, restated briefly)

Stress-test and package the whole pipeline: a mesh-sensitivity check (does
refining `mosfet_geometry.py`'s mesh change Sprint 2/3 results
materially?), parameter-sensitivity/numerical-stability notes (a lot of
this is already written up as gotchas #4/#7/#8 above and in
`docs/limitations.md` — Sprint 5 should verify/consolidate, not
necessarily rediscover), an independent rerun from a clean environment
(`scripts/setup.sh` + the run scripts) to confirm reproducibility,
`docs/validation.md`/`docs/limitations.md` fully filled in (both already
have real content through Sprint 4; Sprint 5 adds its own sections rather
than starting from scratch), a final figure set in `results/figures/`, and
`CITATION.cff` + a finalized `requirements.txt`. Gate: a clean clone +
`scripts/setup.sh` + the run scripts reproduce the Sprint 3/4 headline
results without manual fixes.

## Operating reminders for whoever resumes this

- Read `AGENTS.md` — gate discipline (don't skip/compress sprints),
  anti-hallucination rules (verify DEVSIM calls against the installed
  package before using them, exactly as Sprints 0-4 did), and content
  rules (no scholarship/portfolio language anywhere in this repo).
- If this environment's background/long-running shell commands don't
  survive between messages (observed repeatedly during Sprint 3 — `/tmp`
  was wiped and running DEVSIM processes vanished mid-run, apparently from
  the host machine sleeping/restarting between turns): run sweep scripts
  with the harness's own `run_in_background` tracking rather than manual
  `nohup`, wrap anything that might hang in a hard `timeout N` (see
  gotcha #8 — an un-timed retry loop once pinned a CPU core for nearly an
  hour), and don't be surprised if a run needs relaunching after a resume.
  Sprint 4 also hit a variant of this: a stale/orphaned process from an
  earlier attempt kept running invisibly in the background (reparented to
  `systemd --user`) while a second attempt was launched on top of it,
  producing spurious convergence failures from two solves competing for
  RAM on this 8 GB machine — always check `ps -ef | grep <script name>`
  for stragglers before trusting a "the process died" signal, and before
  starting a fresh run.
- After Sprint 5's gate passes: record the result in `docs/roadmap.md` and
  `docs/validation.md` (same style as Sprint 0-4 above), update this
  file's "where things stand" section, then tell the user it's safe to
  `/clear`.
