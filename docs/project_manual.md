# Project Manual

This document is the canonical technical reference for this project: scope,
physics model, device parameters, and repository layout. It answers "what
is this project and how is it structured" — for sprint status and gates see
`docs/roadmap.md`; for operating rules an agent must follow, see
`AGENTS.md` at the repo root.

## 1. Scope

**Main device:** 2D planar silicon MOSFET.

**Supporting device:** PN junction, used only as a physics validation step
before the MOSFET is attempted. It is not a separate deliverable.

**Research question:** How do MOSFET geometric and doping parameters
(channel length, gate oxide thickness, channel doping) influence the
trade-off between drive current, leakage current, and switching behavior in
a low-power context?

**Out of scope for this project** (explicitly excluded, see §7).

## 2. Simulation approach

Hybrid: an open-source TCAD engine solves the device physics PDEs
numerically; a Python layer around it owns geometry definition, doping
profiles, bias sweeps, automation, parameter extraction, and analysis.

- **TCAD engine:** [DEVSIM](https://devsim.org) — finite-volume PDE solver
  for semiconductor devices, scriptable from Python, supports user-defined
  physics models, 1D/2D/3D, DC/AC/transient analysis.
- **Meshing:** DEVSIM's built-in meshing first; Gmsh only if geometry/mesh
  control requirements exceed what DEVSIM's mesher offers.
- **Everything else (this repository's own code):** physical constants,
  device geometry, doping profiles, simulation setup/automation, bias
  sweeps, parameter extraction (V_TH, I_ON, I_OFF, g_m, SS), sweeps across
  device parameters, result processing, plotting, and a trade-off scoring
  step for the optimization sprint.

The distinction matters for how the code is organized: `src/` never
reimplements a PDE solver — it configures and drives DEVSIM and processes
its output.

## 3. Physics model

### Poisson equation

```
∇·(ε∇ψ) = -q(p - n + N_D⁺ - N_A⁻)
```

- ψ: electrostatic potential
- n, p: electron / hole concentration
- N_D⁺, N_A⁻: ionized donor / acceptor concentration
- ε: permittivity, q: elementary charge

### Continuity equations

```
∂n/∂t =  (1/q)∇·J_n + G - R
∂p/∂t = -(1/q)∇·J_p + G - R
```

Initial scope: G ≈ 0 (no generation), a standard recombination model
(SRH) rather than an expanded generation-recombination framework.

### Drift-diffusion currents

```
J_n = qμ_n n E + q D_n ∇n
J_p = qμ_p p E - q D_p ∇p
E   = -∇ψ
```

DEVSIM solves this system on a finite-volume mesh; the physics.md reference
document expands on parameter values and derivations used for validation.

## 4. Device parameters under study

Primary sweep variables:

1. Channel length, L
2. Gate oxide thickness, t_ox
3. Channel/body doping, N_A

A fourth variable (source/drain doping) may be added only if the first
three sweeps remain numerically stable and tractable on the target hardware
(§6). No more than these are in scope — the study is deliberately narrow so
each sweep can be fully characterized rather than left shallow.

## 5. Metrics extracted from every simulation

- I_D–V_G (transfer characteristic)
- I_D–V_D (output characteristic)
- Threshold voltage, V_TH
- Transconductance, g_m = ∂I_D/∂V_G
- On-current, I_ON
- Off-current, I_OFF
- On/off ratio, I_ON / I_OFF
- Subthreshold swing, SS = dV_G / d(log10 I_D)

## 6. Technology / hardware constraints

- **Device model:** a generic, physically-parameterized planar silicon
  MOSFET. This project does **not** claim to model any specific commercial
  foundry node. Every parameter used is labeled in results as one of:
  simulation input, assumed, analytically derived, or calibrated.
- **Target machine:** Ubuntu Linux, 8 GB RAM. The baseline pipeline
  (Sprint 0 through Sprint 3's baseline device) must run entirely on this
  machine. Google Colab is optional, only for sweeps that turn out to be too
  slow or memory-heavy locally — never a hard dependency.
- **Language/tooling:** Python 3, virtual environment, DEVSIM, NumPy, SciPy,
  Matplotlib, Pandas, Gmsh (conditional), Git.

## 7. Explicitly out of scope

Full custom TCAD solver development, 3D FinFET or nanosheet/GAA devices,
quantum transport, Monte Carlo transport, full fabrication-process
simulation, physical fabrication, dependency on a commercial PDK, massive
(>3-variable) parameter sweeps, machine-learning-driven optimization,
multiphysics thermal simulation, and device-circuit co-simulation (unless a
later, explicitly-scoped extension revisits this).

## 8. Repository layout

```
semiconductor-device-simulation/
├── README.md
├── AGENTS.md            operating rules for any agent working in this repo
├── CLAUDE.md            pointer to AGENTS.md (Claude Code auto-loads this filename)
├── requirements.txt
├── docs/
│   ├── project_manual.md      (this file)
│   ├── physics.md
│   ├── roadmap.md
│   ├── validation.md
│   └── limitations.md
├── src/
│   ├── physics/       constants, semiconductor equations, analytical models
│   ├── device/         geometry, doping, materials, contacts
│   ├── simulation/     DEVSIM setup, solver invocation, bias sweeps
│   ├── extraction/     V_TH, current, transconductance extraction
│   └── optimization/   parameter trade-off scoring
├── simulations/         one subfolder per experiment family
├── results/{raw,processed,tables,figures}
├── tests/
├── notebooks/
└── scripts/             setup.sh, run_baseline.sh, run_experiments.sh
```

## 9. Sprint plan and operating rules

Sprint-by-sprint deliverables, status, and gate criteria are tracked in
`docs/roadmap.md` — that file, not this one, is the up-to-date status
source. The five sprints are: environment + baseline, physics validation,
MOSFET construction, characterization + parameter study, and low-power
optimization + packaging.

For how work in this repository should be carried out (gate discipline,
anti-hallucination checks, content rules, repository conventions), see
`AGENTS.md` at the repo root.
