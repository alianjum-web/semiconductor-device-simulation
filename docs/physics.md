# Physics Reference

This document expands the equations summarized in `project_manual.md` §3
with the constants, derived quantities, and analytical formulas used for
validation throughout the project. Implementations live in
`src/physics/`; this file is the reference they are checked against.

## 1. Physical constants (`src/physics/constants.py`)

| Symbol | Meaning | Value | Unit |
|---|---|---|---|
| q | elementary charge | 1.602176634e-19 | C |
| k_B | Boltzmann constant | 1.380649e-23 | J/K |
| ε₀ | vacuum permittivity | 8.8541878128e-12 | F/m |
| ε_Si | silicon relative permittivity | 11.7 | — |
| ε_ox | SiO₂ relative permittivity | 3.9 | — |
| n_i (300K) | intrinsic carrier concentration, Si | 1.0e10 | cm⁻³ |
| T | reference temperature | 300 | K |

Derived: thermal voltage `V_T = k_B T / q ≈ 0.02585 V` at 300 K.

**Footnote — two constant sets in this codebase, deliberately.** DEVSIM's
bundled physics module (`devsim.python_packages.simple_physics`) hardcodes
its own slightly rounded constants (`q = 1.6e-19 C`, `k = 1.3806503e-23
J/K`, `eps_si = 11.1` rather than 11.7) instead of CODATA-precise values.
`src/physics/constants.py` keeps both: `Q`/`K_B`/`EPS_SI` (CODATA-precise,
for general reference) and `Q_DEVSIM`/`K_B_DEVSIM`/`EPS_SI_DEVSIM` (matching
DEVSIM exactly). Any analytical formula whose output is compared directly
against a DEVSIM simulation result (see `src/physics/analytical_pnjunction.py`,
`src/physics/validation.py`) must use the `_DEVSIM` constants — otherwise an
apparent mismatch is just a constant-definition difference, not a real
physics or numerical discrepancy. This was found and fixed in Sprint 1: see
`docs/validation.md`.

## 2. Semiconductor statistics

Non-degenerate carrier concentrations:

```
n = n_i exp((E_F - E_i) / (k_B T))
p = n_i exp((E_i - E_F) / (k_B T))
np = n_i²                     (equilibrium, mass-action law)
```

Doped-region approximations (full ionization assumed):

```
n ≈ N_D      (n-type, N_D >> n_i)
p ≈ N_A      (p-type, N_A >> n_i)
```

## 3. PN junction (validation device, Sprint 1)

Built-in potential:

```
V_bi = V_T ln(N_A N_D / n_i²)
```

Depletion width (step junction, zero bias):

```
W = sqrt( 2 ε_Si ε₀ (N_A + N_D) V_bi / (q N_A N_D) )
```

Depletion width split between the two sides:

```
x_n = W N_A / (N_A + N_D)
x_p = W N_D / (N_A + N_D)
```

Ideal diode current (reference only — real DEVSIM output includes
recombination and series effects the ideal law omits):

```
I = I_0 [ exp(V / V_T) - 1 ]
```

These formulas are implemented in `src/physics/analytical_pnjunction.py`
and compared against DEVSIM's numerical solution in
`src/physics/validation.py`. Comparison tolerance and results are recorded
in `docs/validation.md` once Sprint 1 runs.

## 4. Poisson equation

```
∇·(ε∇ψ) = -q(p - n + N_D⁺ - N_A⁻)
```

Solved self-consistently with the continuity equations below; this is the
electrostatic core of every DEVSIM simulation in this project.

## 5. Continuity equations

```
∂n/∂t =  (1/q)∇·J_n + G - R
∂p/∂t = -(1/q)∇·J_p + G - R
```

Scope for this project: `G ≈ 0`; recombination `R` via a standard
Shockley-Read-Hall (SRH) model. No optical generation, no impact
ionization — both are out of scope per `project_manual.md` §7.

## 6. Drift-diffusion transport

```
J_n = qμ_n n E + q D_n ∇n
J_p = qμ_p p E - q D_p ∇p
E   = -∇ψ
```

Einstein relation ties mobility and diffusivity: `D = μ V_T`.

## 7. MOSFET operating-point quantities (Sprint 2+)

Long-channel threshold voltage (reference formula, used only as a sanity
check against the extracted numerical value, never as the reported result):

```
V_TH = V_FB + 2φ_F + sqrt(4 ε_Si ε₀ q N_A φ_F) / C_ox
```

with `φ_F = V_T ln(N_A / n_i)` and `C_ox = ε_ox ε₀ / t_ox`.

Extraction definitions used by `src/extraction/`:

- **V_TH** — linear extrapolation of I_D vs. V_G in the linear region to
  I_D = 0, at fixed small V_D.
- **g_m** — `∂I_D/∂V_G`, numerically differentiated from the I_D–V_G sweep.
- **I_ON** — I_D at V_G = V_D = V_DD (supply/reference voltage used for the
  sweep).
- **I_OFF** — I_D at V_G = 0, V_D = V_DD.
- **SS** — subthreshold swing, `dV_G / d(log10 I_D)` in the subthreshold
  region, reported in mV/decade.

## 8. Labeling convention for parameters

Every parameter value that appears in a results table or figure caption
must be tagged as one of:

- **simulation input** — set directly in the DEVSIM script
- **assumed** — a literature-typical value not independently derived here
- **analytical** — computed from a closed-form formula in this document
- **calibrated** — adjusted to match a target analytical or reference value

This avoids presenting any parameter as if it came from a real fabricated
device or a specific commercial process when it did not.
