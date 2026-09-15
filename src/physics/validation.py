"""Numerical-vs-analytical comparison used to gate Sprint 1.

See docs/roadmap.md (Sprint 1 gate) and docs/validation.md for the
recorded result. The tolerance chosen here is deliberately loose relative
to what the simulation actually achieves (see docs/validation.md) -- it is
a gate, not a target to approach.
"""

from dataclasses import dataclass

BUILTIN_POTENTIAL_TOLERANCE = 1e-3  # 0.1% relative error
IDEALITY_FACTOR_TOLERANCE = 0.05  # +/- 5% around n = 1.0


@dataclass
class ComparisonResult:
    label: str
    numerical: float
    analytical: float
    relative_error: float
    tolerance: float
    passed: bool


def compare(label: str, numerical: float, analytical: float, tolerance: float) -> ComparisonResult:
    relative_error = abs(numerical - analytical) / abs(analytical)
    return ComparisonResult(
        label=label,
        numerical=numerical,
        analytical=analytical,
        relative_error=relative_error,
        tolerance=tolerance,
        passed=relative_error <= tolerance,
    )


def validate_builtin_potential(numerical_vbi: float, analytical_vbi: float) -> ComparisonResult:
    return compare("built-in potential (V_bi)", numerical_vbi, analytical_vbi, BUILTIN_POTENTIAL_TOLERANCE)


def validate_ideality_factor(measured_n: float) -> ComparisonResult:
    return compare("forward-bias ideality factor (n)", measured_n, 1.0, IDEALITY_FACTOR_TOLERANCE)
