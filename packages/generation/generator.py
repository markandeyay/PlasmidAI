from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Protocol, Sequence

from packages.core.schemas import AnnotatedSequence, DesignSpec, GeneratedSequence, RetrievedPlasmid
from packages.core.schemas.models import normalize_dna


FAKE_GENERATOR_VERSION = "fake-template-generator-v1"
CARBON_500M_MODEL = "HuggingFaceBio/Carbon-500M"
CARBON_GENERATOR_VERSION = "carbon-500m-cpu-spike-v1"
DEFAULT_CARBON_MODEL_CACHE = Path(__file__).resolve().parent / "models" / "carbon-500m"


class SequenceGenerator(Protocol):
    @property
    def model_version(self) -> str: ...

    def generate(
        self,
        spec: DesignSpec,
        templates: list[RetrievedPlasmid],
        n: int = 1,
    ) -> list[GeneratedSequence]: ...


@dataclass(frozen=True)
class MarkerSwap:
    """Explicit deterministic DNA replacement used only by the fake generator."""

    original_sequence: str
    replacement_sequence: str

    def apply(self, sequence: str) -> str:
        original = normalize_dna(self.original_sequence)
        replacement = normalize_dna(self.replacement_sequence)
        if sequence.count(original) != 1:
            raise ValueError("marker swap requires exactly one original-sequence match")
        return sequence.replace(original, replacement, 1)


@dataclass(frozen=True)
class FakeGenerator:
    marker_swap: MarkerSwap | None = None
    version: str = FAKE_GENERATOR_VERSION

    @property
    def model_version(self) -> str:
        return self.version

    def generate(
        self,
        spec: DesignSpec,
        templates: list[RetrievedPlasmid],
        n: int = 1,
    ) -> list[GeneratedSequence]:
        del spec
        if n <= 0:
            raise ValueError("n must be positive")
        if not templates:
            return []
        template = templates[0].plasmid
        sequence = template.sequence
        if self.marker_swap is not None:
            sequence = self.marker_swap.apply(sequence)

        # Spike code must re-annotate the generated candidate with the Phase 0
        # parser. Do not carry trusted-template completeness across generation.
        annotated = AnnotatedSequence(
            sequence=sequence,
            topology="circular",
            features=[],
            vector_profile=template.vector_type or "unknown",
            annotation_complete=False,
        )
        generated = GeneratedSequence(
            annotated_sequence=annotated,
            model_version=self.model_version,
            parent_template_ids=[template.id],
        )
        return [generated.model_copy(deep=True) for _ in range(n)]


@dataclass
class CarbonGenerator:
    """CPU-only pretrained Carbon-500M spike generator.

    This generator is intentionally narrow: it uses a short template prefix as a
    DNA prompt, asks Carbon for a small continuation, and splices that generated
    segment into the end of the template. It exercises real model inference
    without fine-tuning or claiming design quality.
    """

    model_name: str = CARBON_500M_MODEL
    cache_dir: Path = DEFAULT_CARBON_MODEL_CACHE
    max_new_tokens: int = 4
    prompt_bases: int = 48
    local_files_only: bool = False
    version: str = CARBON_GENERATOR_VERSION
    tokenizer: Any | None = None
    model: Any | None = None

    @property
    def model_version(self) -> str:
        return self.version

    def generate(
        self,
        spec: DesignSpec,
        templates: list[RetrievedPlasmid],
        n: int = 1,
    ) -> list[GeneratedSequence]:
        del spec
        if n <= 0:
            raise ValueError("n must be positive")
        if self.max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")
        if not templates:
            return []
        tokenizer, model = self._load()
        template = templates[0].plasmid
        template_sequence = normalize_dna(template.sequence)
        prompt = carbon_dna_prompt(template_sequence, prompt_bases=self.prompt_bases)
        segment = self._generate_segment(tokenizer, model, prompt)
        candidate_sequence = splice_generated_segment(template_sequence, segment)
        annotated = AnnotatedSequence(
            sequence=candidate_sequence,
            topology="circular",
            features=[],
            vector_profile=template.vector_type or "unknown",
            annotation_complete=False,
        )
        generated = GeneratedSequence(
            annotated_sequence=annotated,
            model_version=self.model_version,
            parent_template_ids=[template.id],
        )
        return [generated.model_copy(deep=True) for _ in range(n)]

    def _load(self) -> tuple[Any, Any]:
        if self.tokenizer is not None and self.model is not None:
            return self.tokenizer, self.model
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            cache_dir=str(self.cache_dir),
            local_files_only=self.local_files_only,
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            dtype=torch.float32,
            device_map=None,
            cache_dir=str(self.cache_dir),
            local_files_only=self.local_files_only,
        ).to("cpu").eval()
        return self.tokenizer, self.model

    def _generate_segment(self, tokenizer: Any, model: Any, prompt: str) -> str:
        import torch

        inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        new_tokens = output[0][inputs["input_ids"].shape[-1] :]
        decoded = tokenizer.decode(new_tokens, skip_special_tokens=True)
        return normalize_dna(decoded)


def ensure_generated_sequence_count(generated: Sequence[GeneratedSequence], *, minimum: int = 1) -> None:
    if len(generated) < minimum:
        raise ValueError(f"expected at least {minimum} generated sequence(s), got {len(generated)}")


def carbon_dna_prompt(sequence: str, *, prompt_bases: int) -> str:
    normalized = normalize_dna(sequence)
    usable = max(6, min(len(normalized), prompt_bases))
    usable -= usable % 6
    if usable <= 0:
        usable = min(len(normalized), 6)
    return f"<dna>{normalized[:usable]}"


def splice_generated_segment(template_sequence: str, generated_segment: str) -> str:
    template = normalize_dna(template_sequence)
    segment = normalize_dna(generated_segment)
    if len(segment) >= len(template):
        return segment[: len(template)]
    return template[: -len(segment)] + segment
