from __future__ import annotations

from packages.validation.codon import codon_adaptation_index, run_codon_check
from tests.validation.helpers import annotated, feature, spec


def test_codon_optimized_bacterial_goi_passes() -> None:
    cds = "GCCCGCGGCCTG" * 12
    report = run_codon_check(annotated(cds, [feature("GOI", 0, len(cds), "optimized protein")]), spec())

    assert report.status == "PASS"


def test_rare_bacterial_goi_fails() -> None:
    cds = "AGGAGAAGGCTA" * 12
    report = run_codon_check(annotated(cds, [feature("GOI", 0, len(cds), "rare protein")]), spec())

    assert report.status == "FAIL"


def test_codon_check_skips_when_no_goi() -> None:
    report = run_codon_check(annotated("ATGC" * 40), spec())

    assert report.status == "PASS"
    assert "skipped" in report.message
