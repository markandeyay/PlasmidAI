from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from packages.application import InMemoryJobQueue, InMemoryOutcomeStore, InMemorySessionStore, SessionJobResult
from packages.core.schemas import (
    AnnotatedFeature,
    AnnotatedSequence,
    DesignSpec,
    Plasmid,
    PlasmidRecommendation,
    RetrievedPlasmid,
    ValidationCheck,
    ValidationReport,
)
from packages.application.designs import InMemoryDesignStore
from packages.application.exports import read_annotated_sequence
from services.api import create_app


def example_plasmid() -> Plasmid:
    return Plasmid(
        id="curated:pEGFP-N1",
        source="curated",
        name="pEGFP-N1",
        sequence="ACGT" * 50,
        length=200,
        organism="Homo sapiens",
        vector_type="mammalian reporter vector",
        markers=["neomycin"],
        promoters=["CMV"],
        use_cases=["fluorescent reporting"],
        annotation_complete=True,
        raw_ref="raw/curated/pEGFP-N1.gb",
    )


def example_result() -> SessionJobResult:
    plasmid = example_plasmid()
    return SessionJobResult(
        design_spec=DesignSpec(organism="Homo sapiens", genes=["GFP"]),
        annotated_sequence=AnnotatedSequence(
            sequence="ACGT" * 20,
            topology="circular",
            annotation_complete=True,
            features=[
                AnnotatedFeature(type="promoter", start=0, end=8, strand=1, name="CMV", confidence=0.99),
                AnnotatedFeature(type="GOI", start=8, end=40, strand=1, name="GFP", confidence=0.95),
            ],
        ),
        validation_report=ValidationReport(
            overall="PASS",
            checks=[ValidationCheck(name="basic", status="PASS", message="ok")],
            generated_by_model_version="fake-validator-0",
        ),
        retrieved_templates=[RetrievedPlasmid(plasmid=plasmid, score=0.97, matched_fields=["semantic"])],
        recommendations=[
            PlasmidRecommendation(
                plasmid_id=plasmid.id,
                rank=1,
                score=0.97,
                why_relevant="pEGFP-N1 is relevant because it matches the requested reporter context.",
            )
        ],
        recommendation_text="Use pEGFP-N1 as the starting reporter backbone.",
    )


def test_create_session_and_enqueue_design_turn() -> None:
    store = InMemorySessionStore()
    queue = InMemoryJobQueue()
    client = TestClient(create_app(session_store=store, job_queue=queue))

    session_response = client.post("/v1/sessions")
    assert session_response.status_code == 201
    session_id = session_response.json()["session_id"]

    design_response = client.post(f"/v1/sessions/{session_id}/design", json={"goal": "Build a GFP reporter"})
    assert design_response.status_code == 202
    job_id = design_response.json()["job_id"]

    session = store.get_session(session_id)
    assert session is not None
    assert [turn.turn_type for turn in session.turns] == ["design"]
    assert session.turns[0].user_text == "Build a GFP reporter"
    assert session.turns[0].job_id == job_id

    job_response = client.get(f"/v1/jobs/{job_id}")
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "queued"


def test_refine_persists_second_turn_and_exposes_completed_job_result() -> None:
    store = InMemorySessionStore()
    queue = InMemoryJobQueue()
    client = TestClient(create_app(session_store=store, job_queue=queue))

    session_id = client.post("/v1/sessions").json()["session_id"]
    initial_job_id = client.post(
        f"/v1/sessions/{session_id}/design",
        json={"goal": "Build a GFP reporter"},
    ).json()["job_id"]
    queue.complete(initial_job_id, result=example_result())

    refine_response = client.post(
        f"/v1/sessions/{session_id}/refine",
        json={"instruction": "Switch the marker to puromycin"},
    )
    assert refine_response.status_code == 202
    refine_job_id = refine_response.json()["job_id"]

    session = store.get_session(session_id)
    assert session is not None
    assert [turn.turn_type for turn in session.turns] == ["design", "refine"]
    assert session.turns[1].user_text == "Switch the marker to puromycin"

    queue.complete(refine_job_id, result=example_result())
    job_response = client.get(f"/v1/jobs/{refine_job_id}")

    assert job_response.status_code == 200
    payload = job_response.json()
    assert payload["status"] == "succeeded"
    assert payload["result"]["design_spec"]["organism"] == "Homo sapiens"
    assert payload["result"]["annotated_sequence"]["topology"] == "circular"
    assert payload["result"]["validation_report"]["overall"] == "PASS"


def test_missing_session_and_job_return_not_found() -> None:
    client = TestClient(create_app(session_store=InMemorySessionStore(), job_queue=InMemoryJobQueue()))

    missing_session_response = client.post("/v1/sessions/missing/design", json={"goal": "Build a GFP reporter"})
    assert missing_session_response.status_code == 404

    missing_job_response = client.get("/v1/jobs/missing")
    assert missing_job_response.status_code == 404


def test_export_endpoint_returns_round_trip_genbank_design() -> None:
    designs = InMemoryDesignStore()
    annotated = example_result().annotated_sequence
    assert annotated is not None
    designs.create(
        session_id="session-export",
        job_id="job-export",
        design_id="design-export",
        annotated_sequence=annotated,
    )
    client = TestClient(
        create_app(
            session_store=InMemorySessionStore(),
            job_queue=InMemoryJobQueue(),
            design_store=designs,
        )
    )

    response = client.get("/v1/designs/design-export/export", params={"format": "genbank"})

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="design-export.gb"'
    round_tripped = read_annotated_sequence(response.text, format="genbank")
    assert round_tripped == annotated


def test_outcome_endpoint_requires_owner_and_returns_latest_outcome() -> None:
    store = InMemorySessionStore()
    designs = InMemoryDesignStore()
    outcomes = InMemoryOutcomeStore()
    session_id = store.create_session(user_id="user-1").session_id
    annotated = example_result().annotated_sequence
    assert annotated is not None
    designs.create(
        session_id=session_id,
        job_id="job-outcome",
        design_id="design-outcome",
        annotated_sequence=annotated,
    )
    client = TestClient(
        create_app(
            session_store=store,
            job_queue=InMemoryJobQueue(),
            design_store=designs,
            outcome_store=outcomes,
        )
    )
    payload = {
        "design_id": "design-outcome",
        "model_version": "fake-generator-0",
        "construct_validated": True,
        "sequencing_result": "Sanger sequencing matched the insert junctions.",
        "expression_result": "GFP signal was observed.",
        "training_consent": True,
        "outcome_label": "positive",
        "provenance": {"source": "unit-test"},
    }

    forbidden = client.post("/v1/designs/design-outcome/outcome", json=payload, headers={"X-User-ID": "user-2"})
    assert forbidden.status_code == 403

    response = client.post("/v1/designs/design-outcome/outcome", json=payload, headers={"X-User-ID": "user-1"})
    assert response.status_code == 201
    body = response.json()
    assert body["report"]["training_consent"] is True

    latest = client.get("/v1/designs/design-outcome/outcome", headers={"X-User-ID": "user-1"})
    assert latest.status_code == 200
    assert latest.json()["outcome_id"] == body["outcome_id"]


def test_pending_outcome_prompt_endpoint_returns_aged_designs_without_outcomes() -> None:
    outcomes = InMemoryOutcomeStore()
    outcomes.design_index = {
        "design-old": ("session-1", datetime.now(UTC) - timedelta(days=21)),
        "design-recent": ("session-1", datetime.now(UTC) - timedelta(days=3)),
    }
    client = TestClient(create_app(outcome_store=outcomes))

    response = client.get("/v1/users/me/pending-outcome-prompts", headers={"X-User-ID": "user-1"})

    assert response.status_code == 200
    assert [prompt["design_id"] for prompt in response.json()["prompts"]] == ["design-old"]
