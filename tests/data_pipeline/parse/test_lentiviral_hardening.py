from packages.data_pipeline.parse.viral_signals import evaluate_viral_signals


# Hallmark rationale:
# - https://www.addgene.org/guides/lentivirus/
# - https://www.ncbi.nlm.nih.gov/pmc/articles/PMC515268/


def test_transferase_names_do_not_emit_ltr_signal() -> None:
    result = evaluate_viral_signals(
        "spectinomycin adenyltransferase n-acetyltransferase alpha-glucosyltransferase"
    )

    assert result.is_transfer_vector is False
    assert result.matched_signals == ()
    assert result.corroborating_rule is None


def test_single_ltr_is_insufficient() -> None:
    result = evaluate_viral_signals("5' LTR")

    assert result.is_transfer_vector is False
    assert result.matched_signals == ("5-prime LTR",)


def test_wpre_alone_is_insufficient() -> None:
    result = evaluate_viral_signals("WPRE")

    assert result.is_transfer_vector is False
    assert result.matched_signals == ("WPRE",)


def test_both_terminal_ltrs_are_sufficient() -> None:
    result = evaluate_viral_signals("5' LTR transfer cassette 3' LTR")

    assert result.is_transfer_vector is True
    assert result.matched_signals == ("5-prime LTR", "3-prime LTR")
    assert result.corroborating_rule == "both 5-prime and 3-prime LTRs"


def test_ltr_plus_psi_packaging_signal_is_sufficient() -> None:
    result = evaluate_viral_signals("LTR psi packaging signal")

    assert result.is_transfer_vector is True
    assert result.matched_signals == ("LTR", "psi packaging signal")
    assert result.corroborating_rule == "LTR plus packaging signal"


def test_ltr_plus_backbone_element_is_sufficient() -> None:
    result = evaluate_viral_signals("long terminal repeat WPRE")

    assert result.is_transfer_vector is True
    assert result.matched_signals == ("LTR", "WPRE")
    assert result.corroborating_rule == "LTR plus known viral-backbone element"


def test_ltr_plus_fragment_alias_is_sufficient() -> None:
    result = evaluate_viral_signals("3-prime LTR env fragment")

    assert result.is_transfer_vector is True
    assert result.matched_signals == ("3-prime LTR", "env")


def test_boundary_matching_does_not_match_polylinker() -> None:
    result = evaluate_viral_signals("LTR polylinker")

    assert result.is_transfer_vector is False
    assert result.matched_signals == ("LTR",)

