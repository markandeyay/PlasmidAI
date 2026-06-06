__all__ = [
    "ConstraintEngine",
    "run_codon_check",
    "run_regulatory_check",
    "run_repeat_instability_check",
    "run_restriction_site_check",
    "validate_sequence",
]


def __getattr__(name: str):
    if name in {"ConstraintEngine", "validate_sequence"}:
        from .engine import ConstraintEngine, validate_sequence

        return {"ConstraintEngine": ConstraintEngine, "validate_sequence": validate_sequence}[name]
    if name == "run_codon_check":
        from .codon import run_codon_check

        return run_codon_check
    if name == "run_regulatory_check":
        from .regulatory import run_regulatory_check

        return run_regulatory_check
    if name == "run_repeat_instability_check":
        from .repeats import run_repeat_instability_check

        return run_repeat_instability_check
    if name == "run_restriction_site_check":
        from .restriction import run_restriction_site_check

        return run_restriction_site_check
    raise AttributeError(name)
