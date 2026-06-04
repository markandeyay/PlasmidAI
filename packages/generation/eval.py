from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import psycopg

from packages.core.schemas import AnnotatedSequence, DesignSpec, GeneratedSequence, RetrievedPlasmid
from packages.core.schemas.models import normalize_dna
from packages.core.vocabularies import MARKER_TERMS, PROMOTER_TYPE_TERMS, TAG_TERMS, contains_term, normalize_text, normalize_to_controlled
from packages.data_pipeline.ingest.genbank import env, load_dotenv
from packages.generation.generator import FakeGenerator, SequenceGenerator, ensure_generated_sequence_count
from packages.generation.spike import (
    ConstraintEngine,
    S3TemplateReannotator,
    S3TextObjectStore,
    StubConstraintEngine,
    requested_component_checks,
)
from packages.retrieval.embed_corpus import EmbedCorpusConfig, build_embedder, build_vector_store
from packages.retrieval.retriever import HybridRetriever, PostgresRetrievalRepository, Retriever


EVAL_VERSION = "phase2-generation-eval-v1"
DEFAULT_GOLD_PATH = Path("data/eval/generation_gold.jsonl")
DEFAULT_OUTPUT_DIR = Path("data/eval/generation")
DEFAULT_MIN_LENGTH = 1000
DEFAULT_MAX_LENGTH = 20000


class Reannotator(Protocol):
    def reannotate(self, generated: GeneratedSequence, template: RetrievedPlasmid) -> AnnotatedSequence: ...


@dataclass(frozen=True)
class GenerationEvalConfig:
    gold_path: Path = DEFAULT_GOLD_PATH
    output_dir: Path = DEFAULT_OUTPUT_DIR
    top_k: int = 1
    n: int = 1
    local_files_only: bool = False
    fake_embedder: bool = False
    database_url: str = "postgresql://plasmid:plasmid@localhost:5432/plasmid_design"

    @classmethod
    def from_env(
        cls,
        *,
        gold_path: Path,
        output_dir: Path,
        top_k: int,
        n: int,
        local_files_only: bool,
        fake_embedder: bool,
    ) -> GenerationEvalConfig:
        dotenv = load_dotenv(Path(".env"))
        return cls(
            gold_path=gold_path,
            output_dir=output_dir,
            top_k=top_k,
            n=n,
            local_files_only=local_files_only,
            fake_embedder=fake_embedder,
            database_url=env("DATABASE_URL", cls.database_url, dotenv),
        )


@dataclass(frozen=True)
class GenerationGoldCase:
    id: str
    query: str
    spec: DesignSpec
    expected_components: dict[str, Any]
    acceptable_template_ids: list[str]
    unsupported: bool = False
    notes: str = ""


@dataclass(frozen=True)
class GenerationEvalHarness:
    retriever: Retriever
    generator: SequenceGenerator
    reannotator: Reannotator
    constraint_engine: ConstraintEngine
    novelty_sequences: dict[str, str]
    top_k: int = 1
    n: int = 1
    min_length: int = DEFAULT_MIN_LENGTH
    max_length: int = DEFAULT_MAX_LENGTH
    version: str = EVAL_VERSION

    def evaluate_case(self, case: GenerationGoldCase) -> dict[str, Any]:
        if case.unsupported:
            return {"id": case.id, "query": case.query, "unsupported": True, "candidates": [], "case_passed": None}
        templates = self.retriever.retrieve(case.spec, k=self.top_k)
        if not templates:
            return {
                "id": case.id,
                "query": case.query,
                "unsupported": False,
                "error": "retrieval_returned_no_templates",
                "candidates": [],
                "case_passed": False,
            }
        generated = self.generator.generate(case.spec, templates, n=self.n)
        try:
            ensure_generated_sequence_count(generated, minimum=1)
        except ValueError as exc:
            return {
                "id": case.id,
                "query": case.query,
                "unsupported": False,
                "error": str(exc),
                "templates": template_summary(templates),
                "candidates": [],
                "case_passed": False,
            }

        candidates: list[dict[str, Any]] = []
        for index, candidate in enumerate(generated, start=1):
            template = template_by_parent(candidate, templates) or templates[0]
            candidates.append(self.evaluate_candidate(case, candidate, template, index=index))
        return {
            "id": case.id,
            "query": case.query,
            "unsupported": False,
            "spec": case.spec.model_dump(mode="json"),
            "templates": template_summary(templates),
            "acceptable_template_ids": case.acceptable_template_ids,
            "candidates": candidates,
            "case_passed": any(candidate["phase2_gate_proxy_passed"] for candidate in candidates),
            "strict_case_passed": any(candidate["strict_generation_success"] for candidate in candidates),
            "notes": case.notes,
        }

    def evaluate_candidate(
        self,
        case: GenerationGoldCase,
        generated: GeneratedSequence,
        template: RetrievedPlasmid,
        *,
        index: int,
    ) -> dict[str, Any]:
        raw_sequence = generated.annotated_sequence.sequence
        syntactic_valid = True
        normalized_sequence = ""
        syntax_error = None
        try:
            normalized_sequence = normalize_dna(raw_sequence)
        except Exception as exc:
            syntactic_valid = False
            syntax_error = str(exc)
        sane_length = syntactic_valid and self.min_length <= len(normalized_sequence) <= self.max_length
        reannotated = self.reannotator.reannotate(generated, template) if syntactic_valid else None
        validation_report = self.constraint_engine.validate(reannotated, case.spec) if reannotated is not None else None
        component_checks = component_checks_for_case(case, reannotated) if reannotated is not None else []
        component_complete = bool(component_checks) and all(check["matched"] for check in component_checks)
        constraint_passed = validation_report is not None and validation_report.overall == "PASS"
        novelty = novelty_report(normalized_sequence, self.novelty_sequences, parent_template=template) if syntactic_valid else {
            "novel": False,
            "copy_matches": [],
            "parent_template_copy": False,
        }
        proxy_passed = syntactic_valid and sane_length and component_complete and constraint_passed
        strict_success = proxy_passed and novelty["novel"]
        return {
            "candidate_index": index,
            "model_version": generated.model_version,
            "parent_template_ids": generated.parent_template_ids,
            "template_id": template.plasmid.id,
            "length_bp": len(normalized_sequence) if syntactic_valid else len(raw_sequence),
            "syntactic_valid": syntactic_valid,
            "syntax_error": syntax_error,
            "sane_length": sane_length,
            "reannotated_profile": reannotated.vector_profile if reannotated is not None else None,
            "reannotated_feature_count": len(reannotated.features) if reannotated is not None else 0,
            "component_checks": component_checks,
            "component_complete": component_complete,
            "validation_report": validation_report.model_dump(mode="json") if validation_report is not None else None,
            "constraint_passed": constraint_passed,
            "novelty": novelty,
            "phase2_gate_proxy_passed": proxy_passed,
            "strict_generation_success": strict_success,
        }


def run_generation_eval(config: GenerationEvalConfig) -> dict[str, Any]:
    cases = load_gold_cases(config.gold_path)
    harness = build_default_harness(config)
    results = [harness.evaluate_case(case) for case in cases]
    metrics = compute_metrics(results)
    report = {
        "eval_version": EVAL_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "gold_path": str(config.gold_path),
        "generator_version": harness.generator.model_version,
        "constraint_engine_mode": "stub",
        "constraint_engine_version": "stub-constraint-engine-v0",
        "gate_eligible": False,
        "metrics": metrics,
        "cases": results,
    }
    write_reports(report, config.output_dir)
    return report


def build_default_harness(config: GenerationEvalConfig) -> GenerationEvalHarness:
    embed_config = EmbedCorpusConfig.from_env(
        batch_size=1,
        limit=None,
        use_fake=config.fake_embedder,
        local_files_only=config.local_files_only,
        hf_cache_dir=None,
    )
    embedder = build_embedder(embed_config)
    vector_index = build_vector_store(embed_config, embedder)
    vector_index.ensure_schema()
    repository = PostgresRetrievalRepository(config.database_url)
    return GenerationEvalHarness(
        retriever=HybridRetriever(vector_index=vector_index, embedder=embedder, repository=repository),
        generator=FakeGenerator(),
        reannotator=S3TemplateReannotator(S3TextObjectStore.from_env()),
        constraint_engine=StubConstraintEngine(),
        novelty_sequences=load_corpus_sequences(config.database_url),
        top_k=config.top_k,
        n=config.n,
    )


def load_gold_cases(path: Path) -> list[GenerationGoldCase]:
    cases: list[GenerationGoldCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "spec" not in row:
            raise ValueError(f"gold case {line_number} is missing explicit spec")
        cases.append(
            GenerationGoldCase(
                id=row["id"],
                query=row["query"],
                spec=DesignSpec.model_validate(row["spec"]),
                expected_components=row.get("expected_components", {}),
                acceptable_template_ids=list(row.get("acceptable_template_ids", [])),
                unsupported=bool(row.get("unsupported", False)),
                notes=row.get("notes", ""),
            )
        )
    return cases


def component_checks_for_case(case: GenerationGoldCase, annotated: AnnotatedSequence) -> list[dict[str, Any]]:
    checks = [check.__dict__ for check in requested_component_checks(case.spec, annotated)]
    evidence = annotation_evidence_text(annotated)
    expected = case.expected_components
    expected_vector = expected.get("vector_type")
    if expected_vector:
        checks.append(
            {
                "kind": "expected_vector_type",
                "requested": expected_vector,
                "matched": normalize_text(expected_vector) == normalize_text(annotated.vector_profile),
                "evidence": annotated.vector_profile,
            }
        )
    for marker in expected.get("markers", []):
        canonical = normalize_to_controlled(marker, MARKER_TERMS) or marker
        matched = controlled_or_plain_match(evidence, canonical, MARKER_TERMS)
        checks.append({"kind": "expected_marker", "requested": marker, "matched": matched, "evidence": canonical if matched else None})
    for promoter in expected.get("promoters", []):
        canonical = normalize_to_controlled(promoter, PROMOTER_TYPE_TERMS) or promoter
        matched = controlled_or_plain_match(evidence, canonical, PROMOTER_TYPE_TERMS)
        checks.append({"kind": "expected_promoter", "requested": promoter, "matched": matched, "evidence": canonical if matched else None})
    for tag in expected.get("tags", []):
        canonical = normalize_to_controlled(tag, TAG_TERMS) or tag
        matched = controlled_or_plain_match(evidence, canonical, TAG_TERMS)
        checks.append({"kind": "expected_tag", "requested": tag, "matched": matched, "evidence": canonical if matched else None})
    feature_types = {feature_type_value(feature.type) for feature in annotated.features}
    for feature_type in expected.get("feature_types", []):
        checks.append(
            {
                "kind": "expected_feature_type",
                "requested": feature_type,
                "matched": feature_type in feature_types,
                "evidence": feature_type if feature_type in feature_types else None,
            }
        )
    return checks


def controlled_or_plain_match(text: str, value: str, terms: tuple[Any, ...]) -> bool:
    if contains_term(text, value):
        return True
    for term in terms:
        if normalize_text(term.canonical) == normalize_text(value):
            return any(contains_term(text, synonym) for synonym in (term.canonical, *term.synonyms))
    return False


def novelty_report(sequence: str, comparison_sequences: dict[str, str], *, parent_template: RetrievedPlasmid) -> dict[str, Any]:
    matches = [seq_id for seq_id, existing in comparison_sequences.items() if circular_exact_copy(sequence, existing)]
    parent_copy = circular_exact_copy(sequence, parent_template.plasmid.sequence)
    if parent_copy and parent_template.plasmid.id not in matches:
        matches.append(parent_template.plasmid.id)
    return {
        "novel": not matches,
        "copy_matches": sorted(matches),
        "parent_template_copy": parent_copy,
    }


def circular_exact_copy(candidate: str, existing: str) -> bool:
    try:
        candidate_norm = normalize_dna(candidate)
        existing_norm = normalize_dna(existing)
    except Exception:
        return False
    if len(candidate_norm) != len(existing_norm):
        return False
    doubled = existing_norm + existing_norm
    if candidate_norm in doubled:
        return True
    return reverse_complement(candidate_norm) in doubled


def reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [candidate for result in results if not result.get("unsupported") for candidate in result.get("candidates", [])]
    cases = [result for result in results if not result.get("unsupported")]
    return {
        "gold_cases": len(results),
        "unsupported_cases": sum(1 for result in results if result.get("unsupported")),
        "scored_cases": len(cases),
        "candidates": len(candidates),
        "syntactic_valid_rate": rate(sum(1 for item in candidates if item["syntactic_valid"]), len(candidates)),
        "sane_length_rate": rate(sum(1 for item in candidates if item["sane_length"]), len(candidates)),
        "component_complete_rate": rate(sum(1 for item in candidates if item["component_complete"]), len(candidates)),
        "stub_constraint_pass_rate": rate(sum(1 for item in candidates if item["constraint_passed"]), len(candidates)),
        "novel_rate": rate(sum(1 for item in candidates if item["novelty"]["novel"]), len(candidates)),
        "phase2_gate_proxy_rate": rate(sum(1 for item in candidates if item["phase2_gate_proxy_passed"]), len(candidates)),
        "strict_generation_success_rate": rate(sum(1 for item in candidates if item["strict_generation_success"]), len(candidates)),
        "case_phase2_gate_proxy_rate": rate(sum(1 for item in cases if item.get("case_passed")), len(cases)),
        "case_strict_success_rate": rate(sum(1 for item in cases if item.get("strict_case_passed")), len(cases)),
    }


def write_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
    json_path = output_dir / f"{timestamp}-generation-eval.json"
    md_path = output_dir / f"{timestamp}-generation-eval.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Phase 2 Generation Evaluation",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Eval version: `{report['eval_version']}`",
        f"- Generator: `{report['generator_version']}`",
        f"- Constraint engine mode: `{report['constraint_engine_mode']}`",
        f"- Gate eligible: `{report['gate_eligible']}`",
        f"- Gold cases: `{metrics['gold_cases']}`",
        f"- Scored cases: `{metrics['scored_cases']}`",
        f"- Candidates: `{metrics['candidates']}`",
        f"- Syntactic valid rate: `{metrics['syntactic_valid_rate']:.3f}`",
        f"- Sane length rate: `{metrics['sane_length_rate']:.3f}`",
        f"- Component complete rate: `{metrics['component_complete_rate']:.3f}`",
        f"- Stub constraint pass rate: `{metrics['stub_constraint_pass_rate']:.3f}`",
        f"- Novel rate: `{metrics['novel_rate']:.3f}`",
        f"- Phase 2 gate proxy rate: `{metrics['phase2_gate_proxy_rate']:.3f}`",
        f"- Strict generation success rate: `{metrics['strict_generation_success_rate']:.3f}`",
        "",
        "FakeGenerator returns retrieved templates verbatim. This report verifies evaluation wiring; novelty failure is expected and this run is not Phase 2 gate-eligible.",
        "",
        "## Cases",
    ]
    for result in report["cases"]:
        lines.extend(render_case_markdown(result))
    return "\n".join(lines).rstrip() + "\n"


def render_case_markdown(result: dict[str, Any]) -> list[str]:
    lines = ["", f"### {result['id']}", "", f"- Query: {result['query']}"]
    if result.get("unsupported"):
        lines.append("- Unsupported: `true`")
        return lines
    if result.get("error"):
        lines.append(f"- Error: `{result['error']}`")
        return lines
    lines.append(f"- Case proxy passed: `{result['case_passed']}`")
    lines.append(f"- Strict case passed: `{result['strict_case_passed']}`")
    for candidate in result.get("candidates", []):
        lines.append(
            f"- Candidate {candidate['candidate_index']}: template `{candidate['template_id']}`, "
            f"profile `{candidate['reannotated_profile']}`, component_complete=`{candidate['component_complete']}`, "
            f"novel=`{candidate['novelty']['novel']}`, proxy_passed=`{candidate['phase2_gate_proxy_passed']}`"
        )
    return lines


def template_summary(templates: list[RetrievedPlasmid]) -> list[dict[str, Any]]:
    return [
        {
            "id": template.plasmid.id,
            "name": template.plasmid.name,
            "score": template.score,
            "matched_fields": template.matched_fields,
        }
        for template in templates
    ]


def template_by_parent(generated: GeneratedSequence, templates: list[RetrievedPlasmid]) -> RetrievedPlasmid | None:
    parent_ids = set(generated.parent_template_ids)
    for template in templates:
        if template.plasmid.id in parent_ids:
            return template
    return None


def annotation_evidence_text(annotated: AnnotatedSequence) -> str:
    return " ".join([annotated.vector_profile, *(feature.name for feature in annotated.features)])


def feature_type_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def load_corpus_sequences(database_url: str) -> dict[str, str]:
    with psycopg.connect(database_url) as connection:
        rows = connection.execute("SELECT id, sequence FROM plasmids ORDER BY id").fetchall()
    return {row[0]: row[1] for row in rows}


def rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the fake-backed Phase 2 generation evaluation harness.")
    parser.add_argument("--gold-path", type=Path, default=DEFAULT_GOLD_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--fake-embedder", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = GenerationEvalConfig.from_env(
        gold_path=args.gold_path,
        output_dir=args.output_dir,
        top_k=args.top_k,
        n=args.n,
        local_files_only=args.local_files_only,
        fake_embedder=args.fake_embedder,
    )
    report = run_generation_eval(config)
    print(json.dumps({"metrics": report["metrics"], "output_dir": str(config.output_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
