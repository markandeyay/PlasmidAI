from __future__ import annotations

import json
from pathlib import Path

from packages.generation.finetune import (
    FinetuneConfig,
    load_triplets,
    render_training_text,
    resolve_split_paths,
    run_smoke,
)


def test_render_training_text_wraps_context_template_and_target_dna() -> None:
    example = {
        "context": {"text": "Design a bacterial cloning vector."},
        "template": {"plasmid_id": "template-1", "sequence": "atgc"},
        "target": {"plasmid_id": "target-1", "sequence": "ggcc"},
    }

    text = render_training_text(example)

    assert "<context>\nDesign a bacterial cloning vector.\n</context>" in text
    assert '<template id="template-1">' in text
    assert "<dna>ATGC</dna>" in text
    assert "<target>\n<dna>GGCC</dna>\n</target>" in text


def test_load_triplets_enforces_required_shape(tmp_path: Path) -> None:
    path = tmp_path / "triplets.train.jsonl"
    path.write_text(
        json.dumps(
            {
                "context": {"text": "context"},
                "template": {"plasmid_id": "template", "sequence": "ATGC"},
                "target": {"plasmid_id": "target", "sequence": "ATGC"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = load_triplets(path)

    assert rows[0]["target"]["sequence"] == "ATGC"


def test_resolve_split_paths_from_snapshot_path() -> None:
    train_path, validation_path = resolve_split_paths(Path("snapshot"), None, None)

    assert train_path == Path("snapshot") / "triplets.train.jsonl"
    assert validation_path == Path("snapshot") / "triplets.validation.jsonl"


def test_run_smoke_trains_tiny_cpu_model_and_writes_report(tmp_path: Path) -> None:
    report = run_smoke(
        FinetuneConfig(
            output_dir=tmp_path,
            smoke=True,
            max_train_examples=5,
            max_eval_examples=2,
            max_steps=1,
            max_length=96,
        )
    )

    assert report["mode"] == "smoke"
    assert report["gpu_used"] is False
    assert report["steps"] == 1
    assert report["train_examples"] == 5
    assert (tmp_path / "smoke_report.json").exists()
    assert (tmp_path / "smoke_config.json").exists()
    assert (tmp_path / "tiny_checkpoint.pt").exists()
