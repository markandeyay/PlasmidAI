from __future__ import annotations

from datetime import UTC, datetime

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, Plasmid
from packages.generation.training_data import (
    FORMATTER_VERSION,
    build_training_dataset,
    candidate_from_records,
    select_template,
)


def make_record(
    plasmid_id: str,
    *,
    name: str,
    profile: str = "bacterial_cloning_vector",
    marker: str = "bla",
    promoter: str | None = None,
    doi: str | None = None,
    sequence: str | None = None,
) -> tuple[Plasmid, AnnotatedSequence]:
    dna = sequence or ("ACGT" * 300)
    features = [
        AnnotatedFeature(type="ORI", start=0, end=40, strand=1, name="pMB1 origin", confidence=0.95),
        AnnotatedFeature(type="marker", start=50, end=100, strand=1, name=marker, confidence=0.95),
        AnnotatedFeature(type="MCS", start=120, end=150, strand=1, name="multiple cloning site", confidence=0.95),
    ]
    promoters = []
    if promoter:
        features.append(AnnotatedFeature(type="promoter", start=180, end=210, strand=1, name=promoter, confidence=0.95))
        promoters.append(promoter)
    plasmid = Plasmid(
        id=plasmid_id,
        source="genbank",
        name=name,
        sequence=dna,
        length=len(dna),
        organism="synthetic construct",
        vector_type="plasmid",
        markers=[marker],
        promoters=promoters,
        publication_doi=doi,
        use_cases=["routine cloning"],
        annotation_complete=True,
        raw_ref=f"raw/genbank/{plasmid_id.replace(':', '_')}.gb",
    )
    annotated = AnnotatedSequence(
        sequence=dna,
        topology="circular",
        features=features,
        vector_profile=profile,
        annotation_complete=True,
    )
    return plasmid, annotated


def make_candidate(*args, **kwargs):  # type: ignore[no-untyped-def]
    plasmid, annotated = make_record(*args, **kwargs)
    candidate, reason = candidate_from_records(plasmid, annotated)
    assert reason is None
    assert candidate is not None
    return candidate


def test_training_dataset_builds_triplets_and_scrubs_target_identity() -> None:
    target = make_candidate("genbank:TARGET.1", name="pTarget", sequence="ACGT" * 300)
    template = make_candidate("genbank:TEMPLATE.1", name="pTemplate", sequence="TGCA" * 300)

    dataset = build_training_dataset(
        [target, template],
        snapshot_id="test-snapshot",
        generated_at=datetime(2026, 6, 3, tzinfo=UTC),
        split_for_group=lambda group: "train",
    )

    assert dataset.triplet_count == 2
    example = dataset.examples_by_split["train"][0]
    assert example["formatter_version"] == FORMATTER_VERSION
    assert example["split"] == "train"
    assert example["target"]["plasmid_id"] == "genbank:TARGET.1"
    assert example["template"]["plasmid_id"] == "genbank:TEMPLATE.1"
    assert "pTarget" not in example["context"]["text"]
    assert "genbank:TARGET.1" not in example["context"]["text"]
    assert target.plasmid.sequence not in example["context"]["text"]


def test_training_dataset_excludes_same_leakage_group_templates() -> None:
    first = make_candidate("genbank:FIRST.1", name="pFirst", doi="10.1000/shared", sequence="ACGT" * 300)
    second = make_candidate("genbank:SECOND.1", name="pSecond", doi="10.1000/shared", sequence="TGCA" * 300)

    dataset = build_training_dataset(
        [first, second],
        snapshot_id="test-snapshot",
        split_for_group=lambda group: "train",
    )

    assert dataset.triplet_count == 0
    assert dataset.stats["skipped_counts"] == {"no_valid_template": 2}


def test_template_selection_prefers_same_vector_profile() -> None:
    target = make_candidate("genbank:TARGET.1", name="pTarget", sequence="ACGT" * 300)
    same_profile = make_candidate("genbank:SAME.1", name="pSame", sequence="TGCA" * 300)
    other_profile = make_candidate(
        "genbank:OTHER.1",
        name="pOther",
        profile="mammalian_reporter_vector",
        sequence="GATC" * 300,
    )

    assert select_template(target, [target, other_profile, same_profile]) == same_profile


def test_candidate_requires_complete_known_profile() -> None:
    plasmid, annotated = make_record("genbank:UNKNOWN.1", name="pUnknown", profile="unknown")

    candidate, reason = candidate_from_records(plasmid, annotated)

    assert candidate is None
    assert reason == "unknown_profile"
