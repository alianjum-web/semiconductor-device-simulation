# Sprint 4 — Low-Power Trade-off Interpretation

This document answers the research question posed in `project_manual.md`
§1 ("how do channel length, gate oxide thickness, and channel doping
influence the trade-off between drive current, leakage current, and
switching behavior in a low-power context?") using only the numbers in
`results/processed/{channel_length,oxide_thickness,doping}_sweep_metrics.csv`
(Sprint 3) and the derived
`results/processed/low_power_tradeoff_scores.csv` (Sprint 4, produced by
`src/optimization/tradeoff.py`). For the scoring method itself (weights,
normalization) see the module docstring; this file is the interpretation,
not a restatement of the method.

## The score, and what it actually measures

`tradeoff_score = 0.3 * ion_norm + 0.5 * (1 - ioff_norm) + 0.2 * gm_norm`,
each term min-max normalized (I_ON and I_OFF on a log10 scale, g_m
linear) across the 7 unique configurations simulated in Sprint 3 (the
Sprint 2 baseline plus two swept values each for L, t_ox, N_A). Leakage
avoidance is weighted highest because the research question is framed
around a low-power trade-off; g_m lowest because a low-power design is
the one most willing to accept a softer switching edge. Weights were
fixed before computing any score and never adjusted afterward.

## Result table

| Rank | Sweep | Parameter | Value | I_ON (A/cm) | I_OFF (A/cm) | g_m,max (A/cm/V) | Score |
|---|---|---|---|---|---|---|---|
| 1 | oxide_thickness | t_ox (cm) | 5.0e-7 | 1.006e-1 | -4.93e-11 | 0.1350 | 0.8463 |
| 2 | doping | N_A (cm⁻³) | 7.0e16 | 1.650e-2 | 2.79e-11 | 0.0676 | 0.8357 |
| 3 | channel_length | L (cm) | 5.0e-5 | 1.721e-2 | -6.76e-11 | 0.1402 | 0.7353 |
| 4 | baseline | L (cm) | 1.0e-4 | 5.305e-3 | -6.08e-11 | 0.0671 | 0.6112 |
| 5 | channel_length | L (cm) | 2.0e-4 | 2.233e-3 | -6.06e-11 | 0.0330 | 0.5347 |
| 6 | oxide_thickness | t_ox (cm) | 2.0e-6 | 1.633e-7 | -4.34e-11 | 0.0227 | 0.3880 |
| 7 | doping | N_A (cm⁻³) | 1.5e17 | 4.900e-4 | 1.99e-10 | 0.0659 | 0.2536 |

(Source: `results/processed/low_power_tradeoff_scores.csv`, which also
carries the three normalized sub-scores per row.)

## Interpretation

**The ranking is driven almost entirely by I_ON and g_m, not by I_OFF —
and that is a finding about this device model, not an artifact to hide.**
Across all 7 configurations, I_ON spans roughly 6 decades (1.6e-7 to
1.0e-1 A/cm) while |I_OFF| spans less than 1 decade (2.8e-11 to 2.0e-10
A/cm). That I_OFF band sits entirely inside the near-zero-current
numerical noise floor already documented for this solver setup (see
`docs/limitations.md` and `docs/HANDOFF.md`'s Sprint 3 gotchas — I_OFF
even changes *sign* between configurations, which is a current-direction
artifact at this magnitude, not a physical reversal of leakage). Min-max
normalization stretches whatever range exists to fill [0, 1] regardless
of whether that range is physically meaningful, so `ioff_norm` still
spans the full 0-to-1 scale in the table above even though none of these
differences are distinguishable from solver noise. Concretely: the
worst-ranked configuration (N_A = 1.5e17) is penalized specifically for
having the single largest |I_OFF| in the set (1.99e-10 A/cm) — a value
about 3x the smallest (7.1e-11 would be the geometric middle) and well
inside noise-floor scatter, not a resolved leakage difference.

The reason I_OFF doesn't move with these parameters is scope, not a bug:
this project's MOSFET model (`docs/project_manual.md` §2, §7) is an ideal
long-channel drift-diffusion device with no DIBL, GIDL, or punch-through
model, so off-state leakage at a fixed V_D = V_DD has no mechanism in this
model to depend on L, t_ox, or N_A the way it would in a real short- or
even moderate-channel device. **This means the trade-off score above is,
in practice, a drive-current/transconductance score weighted 60/40
(0.3 vs 0.2 before renormalization) with a 0.5-weighted noise term mixed
in — not a genuine drive-vs-leakage trade-off**, because there is no real
leakage signal in this data for the score to trade against.

What the data *does* support, directly and without caveats:

- **Thinner oxide and lower channel doping both increase I_ON and g_m
  substantially** (oxide: 1.63e-7 → 1.006e-1 A/cm across the sweep, ~6
  decades; doping: 4.90e-4 → 1.65e-2 A/cm, ~1.5 decades) — consistent with
  stronger gate coupling (higher C_ox = ε_ox/t_ox) and lower V_TH (`docs/
  physics.md` §7), both confirmed as monotonic, gate-passing checks in
  Sprint 3 (`docs/validation.md`).
- **Shorter channel length increases I_ON** (2.233e-3 → 1.721e-2 A/cm from
  L = 2e-4 to 5e-5 cm) via reduced channel resistance, with no modeled
  short-channel penalty (this device has no velocity-saturation or
  DIBL model — see `docs/limitations.md`).
- **None of the three swept parameters produced a resolvable change in
  I_OFF** at V_G=0, V_D=V_DD in this model, across either direction of any
  sweep.

## Answer to the research question

Within this project's scope (an idealized long-channel drift-diffusion
MOSFET, §7 out-of-scope items in `project_manual.md`), **channel length,
oxide thickness, and channel doping all trade drive current and
transconductance against each other in the expected qualitative
directions (thinner oxide, lower doping, and shorter channel each raise
I_ON and g_m; the reverse of each lowers them), but none of the three
produces a measurable leakage-current trade-off in this model** — I_OFF
stays pinned to the solver's numerical noise floor regardless of the
swept parameter. A low-power design pulling from this specific dataset
would therefore choose based on drive-current/switching-speed
requirements alone (higher t_ox / higher N_A / longer L for lower dynamic
current draw, at the cost of switching speed via lower g_m), not on any
leakage evidence this device model can supply. Resolving a real I_ON vs.
I_OFF leakage trade-off would require a device model with short-channel
leakage mechanisms (DIBL, GIDL, punch-through) — explicitly out of scope
for this project (`docs/project_manual.md` §7) — or a solver precision
improvement beyond what was found practical in Sprint 2/3 (`docs/
limitations.md`).

By raw I_ON/g_m alone (the two metrics this data can actually resolve),
the most conservative, lowest-drive operating point among the 7 simulated
is **t_ox = 2.0e-6 cm (20 nm): I_ON = 1.633e-7 A/cm, g_m,max = 0.0227
A/cm/V** — both are the global minimum across every configuration
simulated. The weighted score instead ranks **N_A = 1.5e17 cm⁻³** last
(0.2536, vs. t_ox = 2.0e-6's 0.3880), purely because that configuration
happens to carry the single largest |I_OFF| noise-floor value in the set
(1.99e-10 A/cm) — a direct illustration of the point above: with a
0.5 weight on a term that is mostly noise, the score's bottom rank is not
reliable evidence of which configuration is actually lowest-power. The
t_ox = 2.0e-6 cm configuration is the better-supported answer to "which
configuration favors low power," because it rests on I_ON and g_m, the
two metrics this dataset resolves with real, multi-decade signal.
