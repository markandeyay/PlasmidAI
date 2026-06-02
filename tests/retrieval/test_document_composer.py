from __future__ import annotations

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, Plasmid
from packages.retrieval.document_composer import DOCUMENT_VERSION, compose_plasmid_document


def test_document_composer_renders_deterministic_summary_without_raw_dna() -> None:
    plasmid = Plasmid(
        id="curated:pEGFP-N1",
        source="curated",
        name="pEGFP-N1",
        sequence="ACGT" * 100,
        length=400,
        organism="Cloning vector pEGFP-N1",
        vector_type="plasmid",
        markers=["NeoR/KanR"],
        promoters=["CMV immediate-early enhancer/promoter"],
        use_cases=[
            "CMV-driven C-terminal EGFP fusion vector with neomycin/G418 mammalian selectable marker and kanamycin bacterial marker",
            "reporter_fluorescent",
            "complete sequence",
        ],
        annotation_complete=True,
        raw_ref="raw/curated/pEGFP-N1.gb",
    )
    annotated = AnnotatedSequence(
        sequence=plasmid.sequence,
        topology="circular",
        vector_profile="mammalian_reporter_vector",
        annotation_complete=True,
        features=[
            AnnotatedFeature(type="GOI", start=5, end=50, strand=1, name="EGFP", confidence=0.95),
            AnnotatedFeature(type="MCS", start=51, end=80, strand=0, name="restriction-site dense MCS", confidence=0.55),
            AnnotatedFeature(type="terminator", start=81, end=100, strand=1, name="SV40 late polyA", confidence=0.95),
            AnnotatedFeature(type="ORI", start=101, end=150, strand=1, name="pMB1/pUC origin", confidence=0.95),
            AnnotatedFeature(type="marker", start=151, end=200, strand=1, name="neomycin phosphotransferase", confidence=0.95),
        ],
    )

    composed = compose_plasmid_document(plasmid, annotated)

    assert composed.text == (
        "Mammalian reporter vector pEGFP-N1. "
        "Source description: CMV-driven C-terminal EGFP fusion vector with neomycin/G418 mammalian selectable marker and kanamycin bacterial marker. "
        "Organism annotation: Cloning vector pEGFP-N1. "
        "Promoters: CMV immediate-early enhancer/promoter. "
        "Payloads: EGFP. "
        "Cloning sites: restriction-site dense MCS candidate. "
        "Terminators: SV40 late polyA. "
        "Selectable markers: NeoR/KanR and neomycin phosphotransferase. "
        "Replication origins: pMB1/pUC origin. "
        "Used for: fluorescent reporting. "
        "400 bp circular plasmid. Source: curated."
    )
    assert plasmid.sequence not in composed.text
    assert composed.metadata["document_version"] == DOCUMENT_VERSION
    assert composed.metadata["vector_profile"] == "mammalian_reporter_vector"


def test_document_composer_handles_missing_annotations_and_unknown_profile() -> None:
    plasmid = Plasmid(
        id="addgene:1001",
        source="addgene",
        name="Minimal GFP reporter",
        sequence="ACGT" * 20,
        length=80,
        organism=None,
        vector_type="Lentiviral",
        markers=[],
        promoters=[],
        use_cases=["vector", "bacterial_cloning"],
        annotation_complete=False,
        raw_ref="raw/addgene/1001.json",
    )

    composed = compose_plasmid_document(plasmid, None)

    assert composed.text == (
        "Unclassified plasmid Minimal GFP reporter. "
        "Used for: bacterial cloning. "
        "80 bp circular plasmid. Source: addgene."
    )


def test_curated_unknown_profile_uses_controlled_seed_profile() -> None:
    plasmid = Plasmid(
        id="curated:pACYC184",
        source="curated",
        name="pACYC184",
        sequence="ACGT" * 100,
        length=400,
        organism="synthetic construct",
        vector_type="plasmid",
        markers=["chloramphenicol resistance gene", "tetracycline resistance gene"],
        promoters=[],
        use_cases=[
            "bacterial_cloning",
            "Low-copy p15A-origin vector with chloramphenicol and tetracycline resistance.",
        ],
        annotation_complete=False,
        raw_ref="raw/curated/pACYC184.gb",
    )
    annotated = AnnotatedSequence(
        sequence=plasmid.sequence,
        topology="circular",
        vector_profile="unknown",
        annotation_complete=False,
        features=[
            AnnotatedFeature(type="ORI", start=1, end=20, strand=1, name="p15A origin", confidence=0.95),
            AnnotatedFeature(type="marker", start=21, end=40, strand=1, name="chloramphenicol resistance", confidence=0.95),
        ],
    )

    composed = compose_plasmid_document(plasmid, annotated)

    assert composed.text.startswith("Curated bacterial cloning vector pACYC184. ")
    assert composed.metadata["vector_profile"] == "bacterial_cloning_vector"
