# Phase 2 Fine-Tuning Runbook

## Scope

This runbook describes the first authorized Phase 2 fine-tuning run for the sequence generator. It is a research prototype run, not a production model release.

Approved policy for the first run:

- Budget: one-time GPU spend up to USD 300.
- Providers: Lambda Labs or RunPod, selected by availability and price at run time.
- Preferred GPU: A100 80GB or H100. Use the cheapest available option that can run Carbon-3B with the configured adapter/training settings.
- Base model: standard `HuggingFaceBio/Carbon-3B`.
- FNS variants: skip for the first run. Establish a clean Carbon-3B baseline before adding FNS variables.
- Training data: existing public NCBI-derived Phase 2 triplets, 117 train / 15 validation / 8 test.
- Addgene: do not block the first run on Addgene access.
- Inference: remains CPU-only unless separately authorized.

## Preflight

1. Confirm `master` is current and tests pass:

   ```powershell
   git checkout master
   git pull
   $env:COMPOSE_PROJECT_NAME='pmr'
   & 'C:\Program Files (x86)\GnuWin32\bin\make.exe' test
   ```

2. Confirm the Phase 2 training snapshot exists:

   ```powershell
   Get-ChildItem data\training\phase2
   ```

   Expected baseline snapshot: `data/training/phase2/2026-06-04-010952-phase2-triplets/`.

3. Confirm the generation gold set and deterministic validation engine are present:

   ```powershell
   Get-ChildItem data\eval\generation_gold.jsonl
   python -m packages.validation.eval --curated
   ```

4. Confirm Carbon-3B licensing and revision pin before launching the run. The current policy authorizes standard Carbon-3B, but the exact revision should be recorded in the model registry entry.

## Provider Selection

1. Check Lambda Labs and RunPod for A100 80GB or H100 availability.
2. Prefer the lower total estimated cost if both providers have suitable hardware.
3. Record provider, GPU type, hourly price, region, image, and start time in the run notes.
4. Stop before provisioning if estimated total cost exceeds USD 300.

## Dataset Upload

Upload only the Phase 2 snapshot files needed for training and evaluation:

```text
data/training/phase2/2026-06-04-010952-phase2-triplets/train.jsonl
data/training/phase2/2026-06-04-010952-phase2-triplets/validation.jsonl
data/training/phase2/2026-06-04-010952-phase2-triplets/test.jsonl
data/training/phase2/2026-06-04-010952-phase2-triplets/manifest.json
data/eval/generation_gold.jsonl
```

Do not upload `.env`, database dumps, MinIO buckets, private user data, or Addgene-derived gated content.

## Training Invocation

Start from the existing smoke-training entry point, but replace smoke settings with the Carbon-3B configuration from `research/findings/finetune_config.md`.

Expected command shape on the GPU host:

```bash
python -m packages.generation.finetune \
  --base-model HuggingFaceBio/Carbon-3B \
  --training-snapshot data/training/phase2/2026-06-04-010952-phase2-triplets \
  --output-dir runs/phase2-carbon3b-<timestamp> \
  --max-length <approved_length> \
  --max-steps <approved_steps>
```

Before running, capture:

- Git commit hash.
- Carbon-3B model revision.
- Training-data snapshot ID.
- Hyperparameters.
- Provider and GPU metadata.
- Expected cost ceiling.

## Checkpoint Download

After training:

1. Export the adapter/checkpoint directory.
2. Generate a SHA256 manifest for all checkpoint files.
3. Download the checkpoint to controlled storage.
4. Record artifact URI and hashes.
5. Shut down the GPU instance immediately after artifacts and logs are verified.

## Evaluation

Run the existing generation evaluation on the fine-tuned candidate:

```powershell
$env:GENERATION_GENERATOR='carbon'
& 'C:\Program Files (x86)\GnuWin32\bin\make.exe' eval-generation
```

The report must clearly state:

- The model is trained on only 117 public NCBI-derived training triplets.
- The run is research-prototype quality, not production-grade.
- No Addgene-gated data was used.
- No claim is made about wet-lab performance.

## Registry Registration

Register the checkpoint only after evaluation artifacts exist:

```powershell
& 'C:\Program Files (x86)\GnuWin32\bin\make.exe' register-model `
  VERSION=carbon3b-phase2-<timestamp> `
  MODEL_BASE_MODEL=HuggingFaceBio/Carbon-3B `
  MODEL_TRAINING_SNAPSHOT=2026-06-04-010952-phase2-triplets `
  MODEL_LICENSE_STATUS=research-prototype-pending-legal-review `
  MODEL_ROLLOUT_STATE=shadow `
  MODEL_ARTIFACT_URI=<checkpoint-uri> `
  MODEL_TRAINING_COST=<actual-cost>
```

Include metadata for:

- Provider.
- GPU type.
- Carbon-3B revision.
- Training command.
- Generation eval report paths.
- Any Phase 5 outcome-derived snapshot IDs, if the run uses them in the future.

## Stop Conditions

Stop and request review if:

- Provider cost would exceed USD 300.
- Carbon-3B revision or license status is unclear.
- Training data path includes non-NCBI or gated data unexpectedly.
- Training fails in a way that could corrupt the checkpoint.
- Generation evaluation regresses catastrophically or produces invalid DNA.
