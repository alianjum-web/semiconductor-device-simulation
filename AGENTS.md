# Agent Rules

This file is the source of truth for how an AI agent (or a human) should
operate in this repository. It holds only operating rules — project content
(scope, physics, results) lives in `docs/`, not here. Read this before
making changes; if something you're about to do conflicts with a rule
below, stop and follow the rule.

## Canonical references, in order

1. `docs/HANDOFF.md` — read this **first, always, at the start of any
   session**. It's the running "resume here" summary: current sprint
   status, what's been built, non-obvious gotchas already found (so they
   don't get rediscovered), and what the next sprint needs to do. This
   project is worked on across many short, deliberately `/clear`'d
   sessions (see "Session and context-budget discipline" below) — this
   file is what makes that safe.
2. `docs/roadmap.md` — which sprint is active, its status, its gate. Check
   this first. Do not start work belonging to a sprint that isn't active.
3. `docs/project_manual.md` — scope, device parameters, what's explicitly
   out of scope.
4. `docs/physics.md` — the equations and analytical formulas that any
   simulation result must be checked against.

## Session and context-budget discipline

This project is built one sprint at a time, across separate sessions, to
keep each session's context small and keep the user's usage budget from
being burned by one long-running conversation. Follow this cycle:

1. Do not start a sprint that isn't the next unstarted one in
   `docs/roadmap.md`.
2. Implement that sprint's deliverables, run them for real (never fabricate
   a result), and check the gate.
3. If genuinely stuck (a gate won't pass, a design decision only the user
   can make, missing credentials/hardware) — stop and say so plainly rather
   than guessing past it or quietly lowering the bar to force a pass.
4. Once the gate passes: record the real result in `docs/roadmap.md` and
   `docs/validation.md`, update `docs/HANDOFF.md`'s "where things stand"
   section for the next session, then tell the user the sprint is done and
   that it's safe to run `/clear`.
5. Prefer `/clear` over `/compact` between sprints: `/compact` still spends
   a model call summarizing the old conversation and can lossily compress
   detail; `/clear` drops it for free since `docs/HANDOFF.md` (plus
   `AGENTS.md`, auto-loaded every session) already carries everything the
   next session needs. Recommend `/compact` instead only if the user wants
   to keep debugging within the same still-open sprint rather than move to
   the next one.
6. Never start the next sprint's implementation work in the same breath as
   declaring the previous one done — that defeats the point of clearing
   between them. End the turn, hand it back to the user.

If you're unsure whether something is in scope, these three files answer
it. Don't infer scope from what would be "cool to add."

## Sprint discipline

Five sprints, defined in `docs/roadmap.md`. Each has a gate. A sprint is
not complete, and the next one does not start, until its gate criteria are
met and recorded in `docs/roadmap.md`. Do not compress sprints together,
skip ahead, or start Sprint N+1 code because Sprint N "will obviously
pass." Finish, verify, record the result, then move on.

## Anti-hallucination rules

- Every numeric result that appears in docs, figures, tables, or commit
  messages must come from an actual run of the code in this repository.
  Never write a placeholder or illustrative number as if it were a result.
- Before calling a DEVSIM function or using a physics helper, check it
  actually exists — either in DEVSIM's installed `python_packages` modules
  (`simple_physics.py`, `simple_dd.py`, `model_create.py`, `mos_physics.py`
  under the installed `devsim` package) or in DEVSIM's own documentation.
  Prefer DEVSIM's bundled helpers over re-deriving solver-level physics
  from memory.
- Label every device parameter in results as one of: simulation input,
  assumed, analytical, or calibrated (see `docs/physics.md` §8). Never
  present a parameter as if it came from a real fabricated device or a
  specific commercial process.
- When editing a doc, don't restate content that already lives in another
  canonical file — link to it instead. Duplication is how docs drift out
  of sync and start contradicting the code.

## Content rules

- Do not write about scholarships, admissions, portfolios, applications, or
  any similar framing anywhere in this repository — not in docs, README,
  code comments, or commit messages. Keep all content strictly technical:
  what the project is, how it's built, what it found.
- Default to no code comments; add one only when it captures a non-obvious
  reason (a workaround, a physical constraint, a solver quirk), never to
  restate what the code already says.

## Repository conventions

- Constants and material parameters live in `src/physics/constants.py`,
  never scattered as magic numbers elsewhere.
- Every experiment gets a dedicated subfolder under `simulations/`, raw
  output under `results/raw/`, processed tables/figures under
  `results/{processed,tables,figures}/`.
- `results/` is regenerated by the scripts in `simulations/` and is
  gitignored by default — it's not a store of hand-curated output. Final
  headline figures are committed deliberately during Sprint 5 packaging,
  not accumulated automatically during development.
- A scope or physics change is made in `docs/project_manual.md` /
  `docs/physics.md` first, deliberately, and the code follows — not the
  reverse.

## Keeping this file in sync

`CLAUDE.md` at the repo root is a one-line pointer to this file — Claude
Code auto-loads that filename specifically. If you need to change agent
behavior, edit this file (`AGENTS.md`); don't fork the rules into
`CLAUDE.md` separately.
