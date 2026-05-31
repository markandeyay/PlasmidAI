from __future__ import annotations

from packages.data_pipeline.marker_terms import contains_marker_term


def test_marker_terms_match_named_resistance_features_and_gene_families() -> None:
    assert contains_marker_term("beta-lactamase bla")
    assert contains_marker_term("chloramphenicol resistance cat")
    assert contains_marker_term("tetracycline resistance protein TetA")
    assert contains_marker_term("blaZ")


def test_marker_terms_do_not_match_short_aliases_inside_unrelated_words() -> None:
    assert not contains_marker_term("replication initiator protein A")
    assert not contains_marker_term("replication initiation factor domain-containing protein")
    assert not contains_marker_term("catalase family protein")
    assert not contains_marker_term("blastocyst development protein")
    assert not contains_marker_term("tetrahydrofolate synthase")
