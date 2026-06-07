from __future__ import annotations

import argparse
import inspect
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import torch
from torch import nn

from packages.core.schemas.models import normalize_dna


CARBON_3B_MODEL = "HuggingFaceBio/Carbon-3B"
DEFAULT_SMOKE_OUTPUT_DIR = Path("packages/generation/models/finetune-smoke")
DEFAULT_MAX_LENGTH = 256


@dataclass(frozen=True)
class FinetuneConfig:
    output_dir: Path
    base_model: str = CARBON_3B_MODEL
    base_model_revision: str | None = None
    method: str = "lora"
    learning_rate: float = 2.0e-4
    per_device_train_batch_size: int = 1
    per_device_eval_batch_size: int = 1
    gradient_accumulation_steps: int = 16
    num_train_epochs: float = 3.0
    max_steps: int | None = None
    eval_steps: int = 100
    save_steps: int = 100
    warmup_ratio: float = 0.03
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    max_length: int = DEFAULT_MAX_LENGTH
    seed: int = 20260606
    max_train_examples: int | None = None
    max_eval_examples: int | None = None
    local_files_only: bool = False
    smoke: bool = False


def load_triplets(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        require_triplet_fields(row, path=path, line_number=line_number)
        rows.append(row)
        if limit is not None and len(rows) >= limit:
            break
    if not rows:
        raise ValueError(f"no training triplets found in {path}")
    return rows


def require_triplet_fields(row: dict[str, Any], *, path: Path, line_number: int) -> None:
    for field in ("context", "template", "target"):
        if field not in row or not isinstance(row[field], dict):
            raise ValueError(f"{path}:{line_number} is missing object field {field!r}")
    if not row["target"].get("sequence"):
        raise ValueError(f"{path}:{line_number} is missing target.sequence")


def render_training_text(example: dict[str, Any]) -> str:
    context_text = str(example.get("context", {}).get("text") or "").strip()
    template = example.get("template", {})
    target = example.get("target", {})
    template_id = str(template.get("plasmid_id") or "template")
    template_sequence = normalize_dna(str(template.get("sequence") or target.get("sequence") or ""))
    target_sequence = normalize_dna(str(target.get("sequence") or ""))
    return "\n".join(
        [
            "<context>",
            context_text,
            "</context>",
            f'<template id="{template_id}">',
            f"<dna>{template_sequence}</dna>",
            "</template>",
            "<target>",
            f"<dna>{target_sequence}</dna>",
            "</target>",
        ]
    )


def resolve_split_paths(snapshot_path: Path | None, train_path: Path | None, validation_path: Path | None) -> tuple[Path, Path]:
    if snapshot_path is not None:
        train_path = train_path or snapshot_path / "triplets.train.jsonl"
        validation_path = validation_path or snapshot_path / "triplets.validation.jsonl"
    if train_path is None or validation_path is None:
        raise ValueError("provide --snapshot-path or both --train-path and --validation-path")
    return train_path, validation_path


def run_smoke(config: FinetuneConfig) -> dict[str, Any]:
    torch.manual_seed(config.seed)
    train_examples = smoke_triplets()[: config.max_train_examples or 5]
    eval_examples = smoke_triplets()[config.max_train_examples or 5 :]
    if config.max_eval_examples is not None:
        eval_examples = eval_examples[: config.max_eval_examples]
    if not eval_examples:
        eval_examples = train_examples[:1]
    train_texts = [render_training_text(example) for example in train_examples]
    eval_texts = [render_training_text(example) for example in eval_examples]
    model = TinyCausalLanguageModel(vocab_size=257, hidden_size=24)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    train_features = [encode_text(text, max_length=config.max_length) for text in train_texts]
    eval_features = [encode_text(text, max_length=config.max_length) for text in eval_texts]
    steps = max(1, config.max_steps or 1)
    losses: list[float] = []
    model.train()
    for step in range(steps):
        batch = train_features[step % len(train_features)]
        optimizer.zero_grad(set_to_none=True)
        output = model(batch["input_ids"].unsqueeze(0), labels=batch["labels"].unsqueeze(0))
        output["loss"].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
        optimizer.step()
        losses.append(float(output["loss"].detach().cpu()))
    eval_loss = evaluate_tiny_model(model, eval_features)
    report = {
        "mode": "smoke",
        "base_model": config.base_model,
        "method": config.method,
        "train_examples": len(train_examples),
        "eval_examples": len(eval_examples),
        "steps": steps,
        "train_loss_final": losses[-1],
        "eval_loss": eval_loss,
        "output_dir": str(config.output_dir),
        "gpu_used": False,
    }
    config.output_dir.mkdir(parents=True, exist_ok=True)
    (config.output_dir / "smoke_config.json").write_text(json.dumps(config_as_json(config), indent=2) + "\n", encoding="utf-8")
    (config.output_dir / "smoke_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    torch.save(model.state_dict(), config.output_dir / "tiny_checkpoint.pt")
    return report


def run_huggingface_training(
    config: FinetuneConfig,
    *,
    train_path: Path,
    validation_path: Path,
) -> dict[str, Any]:
    train_rows = load_triplets(train_path, limit=config.max_train_examples)
    eval_rows = load_triplets(validation_path, limit=config.max_eval_examples)
    train_texts = [render_training_text(row) for row in train_rows]
    eval_texts = [render_training_text(row) for row in eval_rows]

    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, set_seed

    set_seed(config.seed)
    tokenizer_kwargs: dict[str, Any] = {
        "trust_remote_code": True,
        "local_files_only": config.local_files_only,
    }
    if config.base_model_revision:
        tokenizer_kwargs["revision"] = config.base_model_revision
    tokenizer = AutoTokenizer.from_pretrained(config.base_model, **tokenizer_kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs: dict[str, Any] = {
        "trust_remote_code": True,
        "local_files_only": config.local_files_only,
        "torch_dtype": torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    }
    if config.base_model_revision:
        model_kwargs["revision"] = config.base_model_revision
    model = AutoModelForCausalLM.from_pretrained(config.base_model, **model_kwargs)
    if config.method == "lora":
        model = apply_lora(model)
    elif config.method != "full":
        raise ValueError(f"unsupported fine-tuning method: {config.method}")

    train_dataset = TokenizedTextDataset(train_texts, tokenizer=tokenizer, max_length=config.max_length)
    eval_dataset = TokenizedTextDataset(eval_texts, tokenizer=tokenizer, max_length=config.max_length)
    training_kwargs: dict[str, Any] = {
        "output_dir": str(config.output_dir),
        "per_device_train_batch_size": config.per_device_train_batch_size,
        "per_device_eval_batch_size": config.per_device_eval_batch_size,
        "gradient_accumulation_steps": config.gradient_accumulation_steps,
        "num_train_epochs": config.num_train_epochs,
        "learning_rate": config.learning_rate,
        "warmup_ratio": config.warmup_ratio,
        "weight_decay": config.weight_decay,
        "max_grad_norm": config.max_grad_norm,
        "eval_steps": config.eval_steps,
        "save_steps": config.save_steps,
        "save_total_limit": 3,
        "logging_steps": 10,
        "load_best_model_at_end": True,
        "metric_for_best_model": "eval_loss",
        "greater_is_better": False,
        "report_to": [],
        "seed": config.seed,
    }
    strategy_key = "eval_strategy" if "eval_strategy" in inspect.signature(TrainingArguments.__init__).parameters else "evaluation_strategy"
    training_kwargs[strategy_key] = "steps"
    training_kwargs["save_strategy"] = "steps"
    if config.max_steps is not None:
        training_kwargs["max_steps"] = config.max_steps
    trainer = Trainer(
        model=model,
        args=TrainingArguments(**training_kwargs),
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
    )
    train_result = trainer.train()
    eval_metrics = trainer.evaluate()
    trainer.save_model(str(config.output_dir / "final"))
    manifest = {
        "mode": "huggingface",
        "base_model": config.base_model,
        "base_model_revision": config.base_model_revision,
        "method": config.method,
        "train_path": str(train_path),
        "validation_path": str(validation_path),
        "train_examples": len(train_rows),
        "eval_examples": len(eval_rows),
        "train_metrics": train_result.metrics,
        "eval_metrics": eval_metrics,
    }
    config.output_dir.mkdir(parents=True, exist_ok=True)
    (config.output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    return manifest


def apply_lora(model: Any) -> Any:
    try:
        from peft import LoraConfig, TaskType, get_peft_model
    except ImportError as exc:
        raise RuntimeError("LoRA fine-tuning requires installing the optional 'peft' package in the GPU environment") from exc
    config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules="all-linear",
    )
    return get_peft_model(model, config)


class TokenizedTextDataset(torch.utils.data.Dataset[dict[str, torch.Tensor]]):
    def __init__(self, texts: Iterable[str], *, tokenizer: Any, max_length: int) -> None:
        self.features = [
            tokenizer(text, max_length=max_length, truncation=True, padding="max_length", return_tensors="pt")
            for text in texts
        ]
        if not self.features:
            raise ValueError("dataset requires at least one rendered training example")

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        feature = {key: value.squeeze(0) for key, value in self.features[index].items()}
        labels = feature["input_ids"].clone()
        if "attention_mask" in feature:
            labels = labels.masked_fill(feature["attention_mask"] == 0, -100)
        feature["labels"] = labels
        return feature


class TinyCausalLanguageModel(nn.Module):
    def __init__(self, *, vocab_size: int, hidden_size: int) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size)
        self.output = nn.Linear(hidden_size, vocab_size)

    def forward(self, input_ids: torch.Tensor, labels: torch.Tensor | None = None) -> dict[str, torch.Tensor]:
        logits = self.output(self.embedding(input_ids))
        if labels is None:
            return {"logits": logits}
        loss = nn.functional.cross_entropy(
            logits[:, :-1, :].contiguous().view(-1, logits.shape[-1]),
            labels[:, 1:].contiguous().view(-1),
            ignore_index=-100,
        )
        return {"loss": loss, "logits": logits}


def encode_text(text: str, *, max_length: int) -> dict[str, torch.Tensor]:
    token_ids = [min(ord(char), 255) + 1 for char in text][:max_length]
    if not token_ids:
        raise ValueError("cannot encode empty text")
    padded = token_ids + [0] * (max_length - len(token_ids))
    labels = [token if token != 0 else -100 for token in padded]
    return {
        "input_ids": torch.tensor(padded, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def evaluate_tiny_model(model: TinyCausalLanguageModel, features: list[dict[str, torch.Tensor]]) -> float:
    model.eval()
    losses: list[float] = []
    with torch.no_grad():
        for feature in features:
            output = model(feature["input_ids"].unsqueeze(0), labels=feature["labels"].unsqueeze(0))
            losses.append(float(output["loss"].cpu()))
    model.train()
    return sum(losses) / len(losses)


def smoke_triplets() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(8):
        sequence = ("ATGCGT" * (12 + index))[:120]
        rows.append(
            {
                "context": {"text": f"Design a small bacterial cloning vector smoke case {index}."},
                "template": {"plasmid_id": f"template-{index}", "sequence": sequence[::-1].replace("T", "A", 1)},
                "target": {"plasmid_id": f"target-{index}", "sequence": sequence},
            }
        )
    return rows


def config_as_json(config: FinetuneConfig) -> dict[str, Any]:
    payload = asdict(config)
    payload["output_dir"] = str(config.output_dir)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and run Phase 2 fine-tuning or a local smoke test.")
    parser.add_argument("--snapshot-path", type=Path, default=None)
    parser.add_argument("--train-path", type=Path, default=None)
    parser.add_argument("--validation-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SMOKE_OUTPUT_DIR)
    parser.add_argument("--base-model", default=CARBON_3B_MODEL)
    parser.add_argument("--base-model-revision", default=None)
    parser.add_argument("--method", choices=["lora", "full"], default="lora")
    parser.add_argument("--learning-rate", type=float, default=2.0e-4)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--per-device-eval-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=16)
    parser.add_argument("--num-train-epochs", type=float, default=3.0)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--eval-steps", type=int, default=100)
    parser.add_argument("--save-steps", type=int, default=100)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    parser.add_argument("--seed", type=int, default=20260606)
    parser.add_argument("--max-train-examples", type=int, default=None)
    parser.add_argument("--max-eval-examples", type=int, default=None)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    return parser


def config_from_args(args: argparse.Namespace) -> FinetuneConfig:
    return FinetuneConfig(
        output_dir=args.output_dir,
        base_model=args.base_model,
        base_model_revision=args.base_model_revision,
        method=args.method,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_train_epochs=args.num_train_epochs,
        max_steps=args.max_steps,
        eval_steps=args.eval_steps,
        save_steps=args.save_steps,
        warmup_ratio=args.warmup_ratio,
        weight_decay=args.weight_decay,
        max_grad_norm=args.max_grad_norm,
        max_length=args.max_length,
        seed=args.seed,
        max_train_examples=args.max_train_examples,
        max_eval_examples=args.max_eval_examples,
        local_files_only=args.local_files_only,
        smoke=args.smoke,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = config_from_args(args)
    if config.smoke:
        report = run_smoke(config)
    else:
        train_path, validation_path = resolve_split_paths(args.snapshot_path, args.train_path, args.validation_path)
        report = run_huggingface_training(config, train_path=train_path, validation_path=validation_path)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
