# Synthetic Augmentation POC

## Summary

This POC generated 24 research-only synthetic `(context, template, target)` drafts from the curated seed plasmid patterns in `research/findings/synthetic_augmentation.md`. The drafts are intentionally structured edit specs, not nucleotide targets, and were not added to the training set.

Outcome: proceed only after a dedicated synthetic-target schema and validator exist. The current sequence-triplet loader correctly rejects these drafts because they omit `target.sequence`.

## Validator Check

Existing validator entrypoint used: `packages.generation.finetune.require_triplet_fields`.

Command run:

```powershell
python -c "from pathlib import Path; from packages.generation.finetune import require_triplet_fields; row={'context': {'text': 'Design a pUC-family cloning vector with chloramphenicol selection.'}, 'template': {'plasmid_id': 'pUC19', 'sequence': 'ATGC'}, 'target': {'target_type': 'synthetic_component_substitution', 'base_template_id': 'pUC19'}};
try:
    require_triplet_fields(row, path=Path('synthetic_poc.jsonl'), line_number=1)
except ValueError as exc:
    print(f'validator_rejected_structured_synthetic_target: {exc}')
else:
    raise SystemExit('validator unexpectedly accepted structured synthetic target')"
```

Result:

```text
validator_rejected_structured_synthetic_target: synthetic_poc.jsonl:1 is missing target.sequence
```

Interpretation: this is the desired behavior for the existing sequence-training path. Synthetic structured targets need a separate schema before they can be persisted or mixed into fine-tuning data.

## Generated Drafts

All drafts carry these common flags: `synthetic_target`, `unvalidated_design_spec`, `requires_coordinate_validation`, `requires_license_review`, `requires_human_biology_review`.

| ID | Template | Context Intent | Target Edit Spec | Hard Gates |
| --- | --- | --- | --- | --- |
| SYN-001 | pGEX-4T-1 | pGEX-style E. coli GST fusion with kanamycin selection | Replace bacterial AmpR cassette with KanR cassette while preserving tac/lac GST fusion, origin, MCS, thrombin-cleavage logic | marker cassette source, coordinates, promoter/terminator orientation |
| SYN-002 | pGEX-4T-1 | pGEX-style fusion with added C-terminal His tag | Add reviewed in-frame His tag strategy without breaking GST/MCS reading frame | tag position, linker, stop codon, frame |
| SYN-003 | pGEX-4T-1 | pGEX-style vector using chloramphenicol selection | Replace AmpR with CmR while preserving bacterial expression cassette | marker source, cassette boundaries, backbone disruption check |
| SYN-004 | pGEX-4T-1 | pGEX-style vector with alternate protease-cleavage site | Swap cleavage-site annotation only after frame and linker review | cleavage sequence source, frame, fusion semantics |
| SYN-005 | pUC19 | pUC-family high-copy cloning vector with chloramphenicol selection | Replace AmpR with CmR while preserving pUC/pMB1 origin and lacZ alpha/MCS | marker source, lacZ/MCS preservation, origin preservation |
| SYN-006 | pUC19 | pUC19-like cloning vector with pUC18 MCS orientation | Change MCS orientation to pUC18-style semantics while preserving origin and AmpR | circular coordinate handling, unique-site validation |
| SYN-007 | pUC18 | pUC18-like cloning vector with kanamycin selection | Replace AmpR with KanR while preserving pUC origin and blue-white screening | marker source, promoter orientation, lacZ alpha integrity |
| SYN-008 | pUC18 | pUC-family cloning vector with expanded MCS | Replace MCS with reviewed expanded cloning site set | restriction-site uniqueness, lacZ alpha frame/context |
| SYN-009 | pBR322 | pBR322 derivative retaining TetR but removing AmpR | Remove or disable AmpR while preserving pMB1/rop and TetR | marker-disruption cloning-site review, backbone function |
| SYN-010 | pBR322 | pBR322 dual-selection vector with CmR instead of TetR | Replace TetR with CmR while retaining AmpR and pMB1-derived replication | marker source, origin/rop non-disruption, selection semantics |
| SYN-011 | pBR322 | pBR322-like vector retaining AmpR with KanR second marker | Replace TetR with KanR while preserving pBR322-family identity | compatibility, marker expression, known site behavior |
| SYN-012 | pBR322 | pBR322 reduced-marker cloning backbone | Disable one marker only if unique cloning strategy remains coherent | historical marker-site review, feature annotation |
| SYN-013 | pBluescript-II-SK-plus | Opposite single-stranded rescue orientation | Convert f1 origin orientation to SK(-)-style semantics | f1 orientation, T7/T3 layout, coordinate review |
| SYN-014 | pBluescript-II-SK-minus | Opposite single-stranded rescue orientation | Convert f1 origin orientation to SK(+)-style semantics | f1 orientation, sequencing-primer layout |
| SYN-015 | pBluescript-II-SK-plus | pBluescript-style cloning phagemid with KanR | Replace bla/AmpR with KanR while preserving f1, pUC origin, lacZ alpha/MCS, T7/T3 flanks | marker source, phagemid rescue preservation |
| SYN-016 | pBluescript-II-SK-minus | pBluescript-style phagemid with CmR | Replace bla/AmpR with CmR while preserving SK(-) rescue orientation | marker source, f1 and MCS non-disruption |
| SYN-017 | pACYC184 | Low-copy p15A-compatible vector with KanR | Replace one selectable marker with KanR while preserving p15A compatibility | marker-region cloning behavior, copy-number claims |
| SYN-018 | pACYC184 | pACYC-style vector retaining CmR but removing TetR | Disable/remove TetR only if cloning-site behavior remains reviewed | marker-region function, feature coordinates |
| SYN-019 | pACYC184 | Low-copy vector for co-maintenance with AmpR pUC plasmid | Preserve p15A origin and choose non-AmpR selection | co-maintenance assumptions, marker source |
| SYN-020 | pEGFP-N1 | Mammalian C-terminal fusion vector using mCherry instead of EGFP | Replace EGFP payload with reviewed fluorescent-protein payload while preserving CMV, C-terminal fusion, NeoR/G418, bacterial propagation | fluorescent-protein license/source, frame, linker, stop logic |
| SYN-021 | pEGFP-N1 | Mammalian expression vector with HygR instead of NeoR/G418 | Replace mammalian selection cassette with HygR cassette while retaining bacterial KanR and CMV-EGFP fusion | full mammalian cassette source, promoter/polyA, marker distinction |
| SYN-022 | pGL3-Basic | Promoterless reporter with stable HygR support | Add or swap mammalian HygR selection support while keeping reporter promoterless | stable-selection cassette review, promoterless assay preservation |
| SYN-023 | pGL4-10-luc2 | pGL4-like promoterless reporter with firefly luciferase family payload | Substitute reporter payload family while preserving promoter-insertion design | payload source/license, assay comparability, cryptic site review |
| SYN-024 | pRS415 | Yeast shuttle vector using URA3 instead of LEU2 | Replace LEU2 with URA3 while preserving CEN/ARS and bacterial propagation | strain auxotrophy, yeast marker source, bacterial module preservation |

## Aggregate Checks

| Check | Result |
| --- | --- |
| Draft count in requested 20-50 range | Pass, 24 drafts |
| Emits full synthetic nucleotide targets | Pass, none emitted |
| Uses current training-set directory | Pass, no `data/training/` changes |
| Uses only curated seed templates | Pass, all templates from curated seed manifest/spec |
| Existing sequence-triplet validator outcome | Expected reject, missing `target.sequence` |
| Human biology review requirement | Blocking |
| Donor component license/source approval | Blocking |
| Coordinate and orientation validation | Blocking |

## Recommendation

Do not promote these drafts into `data/training/phase2` yet. The next implementation should add a separate synthetic structured-target schema with fields for `target_type`, `base_template_id`, substitutions, preserve-list, validation requirements, quality flags, source/license status, and human-review status. Only after that schema passes deterministic validation should any example be considered for train-only ablations.
