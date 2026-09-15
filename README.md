# Semiconductor Device Simulation

Physics-based 2D MOSFET device simulation and low-power parameter
optimization, built on the open-source DEVSIM TCAD engine.

This repository simulates a 2D planar silicon MOSFET from first-principles
semiconductor equations (Poisson + drift-diffusion + continuity), extracts
standard device metrics (V_TH, I_ON, I_OFF, g_m, subthreshold swing), and
runs a systematic parameter study across channel length, gate oxide
thickness, and channel doping to characterize the trade-off between drive
current and leakage current relevant to low-power digital design.

DEVSIM solves the device physics; this repository owns geometry and doping
definition, simulation automation, bias sweeps, metric extraction, and
analysis. See `docs/project_manual.md` for the full scope and design
decisions — it is the canonical reference for this project.

## Status

Sprints 0 (environment + baseline) and 1 (semiconductor physics
validation) are complete and gated — see `docs/roadmap.md` and
`docs/validation.md` for recorded results. Sprint 2 (2D MOSFET
construction) is next. Sprints are completed in order, each gated before
the next starts.

## Repository layout

```
docs/            project manual, physics reference, roadmap, validation, limitations
src/
  physics/       constants, semiconductor equations, analytical models
  device/        MOSFET geometry, doping, materials, contacts
  simulation/    DEVSIM setup, solver invocation, bias sweeps
  extraction/    V_TH, current, transconductance extraction
  optimization/  low-power trade-off scoring
simulations/     one subfolder per experiment (pnjunction, baseline_mosfet, sweeps)
results/         raw/processed simulation output, tables, figures
tests/           unit tests for physics and extraction code
scripts/         setup.sh, run_baseline.sh, run_experiments.sh
```

## Requirements

- Ubuntu Linux (developed/targeted at 8 GB RAM)
- Python 3.9+
- DEVSIM, NumPy, SciPy, Matplotlib, Pandas (see `requirements.txt`)

## Setup

```bash
./scripts/setup.sh
source .venv/bin/activate
```

`scripts/setup.sh` creates a virtual environment, installs pinned
dependencies, and runs a smoke test to confirm DEVSIM is working before any
device work is attempted.

## Documentation

- [`docs/project_manual.md`](docs/project_manual.md) — scope, physics
  model, device parameters, repository conventions (start here)
- [`docs/physics.md`](docs/physics.md) — equations and analytical formulas
  used for validation
- [`docs/roadmap.md`](docs/roadmap.md) — sprint-by-sprint plan and gates
- [`docs/validation.md`](docs/validation.md) — numerical-vs-analytical
  validation results (filled in as sprints complete)
- [`docs/limitations.md`](docs/limitations.md) — known limitations and
  scope boundaries
- [`AGENTS.md`](AGENTS.md) — operating rules for any AI agent (or
  contributor) working in this repository
- [`docs/HANDOFF.md`](docs/HANDOFF.md) — running cross-session summary: what's
  built, current status, gotchas already found, what's next (read this
  first when resuming work in a new session)
