# Unknown Corpus Quality Audit

- Generated at: `2026-06-07T13:26:30-04:00`
- Branch context requested: `phase0-corpus-quality`
- Scope: corpus quality refinement only; no code, corpus, generation, API outcome, or Phase 5 changes
- Audit artifact only: this Markdown file
- Current quality snapshot: `data/eval/quality/2026-06-05-232255-quality-report.{md,json}`
- Current classifier snapshot: `data/eval/reprocess/2026-06-05-232247-reprocess-all.json`
- Prior unknown audit compared: `data/eval/classifier_unknown_audit_phase2_real_2026-06-05-001224.md`

## Summary Counts

| Category | Current unknown records | Recommendation |
| --- | ---: | --- |
| 1. Legitimately unusual plasmids worth keeping | 14 | Keep as `unknown` natural/reference/comparative records; do not promote into engineered-vector profiles. |
| 2. Annotation/parser-refinement candidates among current unknowns | 0 | The 5 engineered-vector rule-gap records from the prior 104-record audit are no longer unknown in the current 99-record snapshot. |
| 3. Should not have been ingested into the engineered-vector corpus lane | 85 | Do not delete existing rows from this audit; route/filter/separate from engineered-vector generation/template corpora in future ingestion or manifest construction. |
| Total current unknown records audited | 99 | Matches the latest quality report and reprocess output. |

## Methodology

1. Confirmed the latest quality report has `256` total records, `99` unknown-classified records, `0` parse errors, and `3` duplicate clusters.
2. Extracted current unknown IDs from `data/eval/reprocess/2026-06-05-232247-reprocess-all.json`.
3. Compared current unknown IDs to the prior 104-record unknown audit. The current set is a strict subset: the 5 prior engineered-vector parser/classifier-gap records are no longer unknown; no new unknown IDs were added.
4. Reused prior cached-blob/parser evidence where applicable because the local configured Postgres database was reachable but contained no application tables during this audit session.
5. Categorized current unknown records conservatively. Natural plasmid resistance genes, mobility genes, replication genes, or sparse RefSeq annotations were not treated as engineered selectable-marker, ORI, shuttle, cloning, or expression-vector evidence without explicit engineered-vector metadata.

## Current Delta From Prior 104-Record Audit

The latest current unknown set is `99`, down from `104`. These 5 prior category-2 records are no longer unknown in the latest reprocess output:

| ID | Prior interpretation | Current audit disposition |
| --- | --- | --- |
| `genbank:AF050464.1` | Expression vector pKIL-HIS3; narrow bacterial-expression parser/classifier gap. | Not in current unknown set; no current unknown action. |
| `genbank:AF097552.1` | Expression vector unc-68:GFP(1-8); GFP/reporter evidence gap. | Not in current unknown set; no current unknown action. |
| `genbank:AF147464.1` | T7 expression vector pViet; missing ORI/promoter/tag evidence. | Not in current unknown set; no current unknown action. |
| `genbank:AY236524.1` | Cloning vector pLZ42; explicit vector title but missing ORI/MCS/backbone signal. | Not in current unknown set; no current unknown action. |
| `genbank:U09128.1` | pSacBII P1 cloning vector; P1/repL support gap. | Not in current unknown set; no current unknown action. |

## Category 1: Legitimately Unusual, Keep Unknown

These records are real plasmids or episomes that can be useful for comparative retrieval, provenance calibration, natural-replicon background, or biological reference context. They should remain `unknown` because they do not represent engineered cloning/expression/shuttle vector architecture.

| ID | Representative evidence | Recommendation |
| --- | --- | --- |
| `genbank:CP121282.1` | Halobacterium plasmid pCBA1161-02; archaeal natural plasmid with hypothetical proteins, HNH endonuclease, recombinase/integrase, IS element. | Keep `unknown`; unusual natural archaeal plasmid. |
| `genbank:NC_002059.1` | Butyrivibrio fibrisolvens plasmid pOM1; mobV and RepL-like maintenance protein. | Keep `unknown`; natural anaerobe reference. |
| `genbank:NC_002139.1` | Pseudoselenomonas ruminantium plasmid pSR1; natural rumen plasmid with metabolic/sensor CDS. | Keep `unknown`; natural reference. |
| `genbank:NC_004962.1` | pJW1; small sparse natural plasmid. | Keep `unknown`; minimal natural replicon. |
| `genbank:NC_004977.1` | pONE430; RepL-like maintenance protein only. | Keep `unknown`; minimal natural replicon. |
| `genbank:NC_004986.1` | pONE429; hypothetical protein and RepL-like maintenance protein. | Keep `unknown`; minimal natural replicon. |
| `genbank:NC_006857.1` | pSRD191; RepL-like maintenance protein only. | Keep `unknown`; minimal natural replicon. |
| `genbank:NC_013776.1` | pSRD192; sparse hypothetical protein annotation. | Keep `unknown`; sparse natural plasmid. |
| `genbank:NC_015313.1` | Pseudonocardia pPSED03; primase, ParA, FtsK/SpoIIIE-like proteins. | Keep `unknown`; natural actinobacterial plasmid reference. |
| `genbank:NC_016045.1` | pSRD77; RepL-like maintenance protein only. | Keep `unknown`; minimal natural replicon. |
| `genbank:NC_016600.1` | Pseudonocardia pPSED02; VirB/TrbL, transporter, transposase/metabolic CDS. | Keep `unknown`; natural mobile/reference plasmid. |
| `genbank:NC_017772.1` | Alternate Pseudonocardia pPSED02-like record; relaxase/mobilization/helicase/TraM evidence. | Keep `unknown`; natural mobile/reference plasmid. |
| `genbank:NZ_M60875.1` | Mycolicibacterium fortuitum pAL5000; natural mycobacterial replicon. | Keep `unknown`; natural replicon background only. |
| `genbank:PX275371.1` | Zygosaccharomyces bailii pZB1; natural yeast plasmid/episome with FLP but no engineered shuttle-vector marker/MCS context. | Keep `unknown`; do not classify as yeast shuttle vector without engineered shuttle evidence. |

## Category 2: Parser-Refinement Candidates

There are no current unknown records that I would promote as parser-refinement candidates for an existing engineered-vector profile based on the available current snapshot.

The useful parser/classifier lesson from the delta is still important: previous gap records were explicit engineered vectors, and future refinements should remain metadata-backed and narrow. Do not broaden rules in ways that would admit natural plasmids from category 3.

Parser-refinement guardrails to preserve:

1. Do not globally convert `rep`, `RepA`, `RepB`, or `RepL` into engineered ORI evidence.
2. Do not globally treat natural AMR or metal-resistance genes as engineered selectable-marker evidence.
3. Require explicit engineered-vector title/metadata before using weak vector-like signals such as `pMB1`, `f1`, `lacI`, `T7 terminator`, or `aph(3')-Ia` in natural isolate records.
4. Keep title-backed expression/cloning/shuttle rules narrow and regression-test them against Staphylococcus, Enterobacter, Aeromonas, Shigella, and RefSeq unnamed natural plasmids.

## Category 3: Should Not Have Been Ingested Into This Corpus Lane

These records are mostly real public plasmid records, but they are poor matches for the engineered-vector corpus lane. The recommendation is not deletion of existing rows. The recommendation is future filtering, routing to a separate natural-plasmid lane, or exclusion from engineered-vector generation/training manifests.

Representative groups:

| Group | Count in current unknowns | Representative IDs | Reason |
| --- | ---: | --- | --- |
| Natural strain/isolate plasmids dominated by maintenance, mobility, transporter, toxin-antitoxin, or resistance payloads | 45 | `CP190835.1`, `CP190854.1`, `CP191060.1`, `CP191068.1`, `NZ_CP071509.1`, `NZ_CP187932.1` | Natural plasmid biology, not engineered vector architecture. |
| Sparse/minimal natural replicons | 20 | `CP190836.1`, `CP190851.1`, `CP190873.1`, `CP191051.1`, `NZ_CP073311.1`, `NZ_OZ477360.1` | Too little informative engineered-vector annotation; often only Rep-like or hypothetical proteins. |
| Unnamed RefSeq/environmental plasmids | 14 | `NZ_CP054601.1`, `NZ_CP054605.1`, `NZ_CP121831.1`, `NZ_CP121852.1`, `NZ_CP125988.1`, `NZ_CP192524.1` | Unnamed natural plasmids inflate unknown count and are weak engineered-template candidates. |
| Natural AMR/mobile plasmids | 4 | `NZ_CP073313.1`, `NZ_CP073314.1`, `PZ138287.1`, `PZ407647.1` | Resistance genes are public-health/natural payloads, not sufficient engineered selection-cassette evidence. |
| Natural isolate records with vector-like artifact/contamination signals | 2 | `NZ_CP071514.1`, `NZ_OZ477361.1` | Have pMB1/f1/lac/T7-like signals but natural-isolate metadata; should require human review or artifact policy, not automatic promotion. |

The category-3 count is `85`. The group counts above are coarse operational buckets and intentionally not deletion labels.

## Recommended Ingest Filters

Highest-priority filters for future engineered-vector corpus ingestion or training-manifest construction:

1. Exclude or route aside records whose title matches natural context patterns such as `strain ... plasmid`, `isolate ... plasmid`, `unnamed`, `complete sequence`, or `complete genome` unless the title also contains trusted engineered-vector terms such as `cloning vector`, `expression vector`, `shuttle vector`, `phagemid`, `reporter vector`, or a curated known vector family.
2. Exclude `UNVERIFIED`, `partial sequence`, short resistance loci, and ambiguous resistance-locus records from engineered-vector ingestion. `genbank:PZ407647.1` is the representative current unknown example.
3. Route broad RefSeq natural-plasmid records (`NC_`, `NZ_`) into a separate natural/reference lane unless they pass an explicit engineered-vector metadata gate.
4. Add a sparse-annotation filter: no engineered-vector title, no parsed promoter/MCS/terminator/tag/shuttle evidence, and fewer than a small threshold of informative non-hypothetical features should not enter the engineered-vector lane.
5. Add a natural mobility/AMR route-aside heuristic for records dominated by `mob`, `relaxase`, `tra`, `virB`, `virD`, `integrase`, `transposase`, `IS`, `toxin-antitoxin`, `partition`, `ParA/ParB`, `blaZ`, `blaR1`, `blaI`, `GES`, `aadA`, `qnr`, `sul1`, `tetA`, `tetR`, `dfrA16`, `aacA`, `aphD`, `cadD`, `fexB`, `msr(A)`, or `Mph(C)` in natural-isolate titles.
6. Treat vector-like signals inside natural-isolate records as human-review flags, not automatic classifier evidence. `NZ_CP071514.1` and `NZ_OZ477361.1` are the current examples.

## Full Current Unknown ID Roster

Category 1 keep-unknown IDs:

`genbank:CP121282.1`, `genbank:NC_002059.1`, `genbank:NC_002139.1`, `genbank:NC_004962.1`, `genbank:NC_004977.1`, `genbank:NC_004986.1`, `genbank:NC_006857.1`, `genbank:NC_013776.1`, `genbank:NC_015313.1`, `genbank:NC_016045.1`, `genbank:NC_016600.1`, `genbank:NC_017772.1`, `genbank:NZ_M60875.1`, `genbank:PX275371.1`.

Category 3 filter/separate IDs:

`genbank:CP190835.1`, `genbank:CP190836.1`, `genbank:CP190842.1`, `genbank:CP190845.1`, `genbank:CP190847.1`, `genbank:CP190849.1`, `genbank:CP190850.1`, `genbank:CP190851.1`, `genbank:CP190852.1`, `genbank:CP190854.1`, `genbank:CP190855.1`, `genbank:CP190857.1`, `genbank:CP190859.1`, `genbank:CP190864.1`, `genbank:CP190865.1`, `genbank:CP190867.1`, `genbank:CP190868.1`, `genbank:CP190870.1`, `genbank:CP190872.1`, `genbank:CP190873.1`, `genbank:CP190874.1`, `genbank:CP190875.1`, `genbank:CP190876.1`, `genbank:CP190878.1`, `genbank:CP190879.1`, `genbank:CP191035.1`, `genbank:CP191036.1`, `genbank:CP191037.1`, `genbank:CP191042.1`, `genbank:CP191051.1`, `genbank:CP191052.1`, `genbank:CP191053.1`, `genbank:CP191054.1`, `genbank:CP191060.1`, `genbank:CP191063.1`, `genbank:CP191068.1`, `genbank:CP191069.1`, `genbank:CP191070.1`, `genbank:CP191071.1`, `genbank:CP191072.1`, `genbank:CP191074.1`, `genbank:CP191075.1`, `genbank:CP191076.1`, `genbank:CP191078.1`, `genbank:CP196381.1`, `genbank:NZ_CP054601.1`, `genbank:NZ_CP054605.1`, `genbank:NZ_CP054607.1`, `genbank:NZ_CP071509.1`, `genbank:NZ_CP071510.1`, `genbank:NZ_CP071511.1`, `genbank:NZ_CP071513.1`, `genbank:NZ_CP071514.1`, `genbank:NZ_CP071515.1`, `genbank:NZ_CP073311.1`, `genbank:NZ_CP073312.1`, `genbank:NZ_CP073313.1`, `genbank:NZ_CP073314.1`, `genbank:NZ_CP086918.1`, `genbank:NZ_CP086920.1`, `genbank:NZ_CP086929.1`, `genbank:NZ_CP086935.1`, `genbank:NZ_CP086937.1`, `genbank:NZ_CP086939.1`, `genbank:NZ_CP086940.1`, `genbank:NZ_CP087040.1`, `genbank:NZ_CP087081.1`, `genbank:NZ_CP087393.1`, `genbank:NZ_CP087394.1`, `genbank:NZ_CP091883.1`, `genbank:NZ_CP121831.1`, `genbank:NZ_CP121838.1`, `genbank:NZ_CP121852.1`, `genbank:NZ_CP121858.1`, `genbank:NZ_CP121860.1`, `genbank:NZ_CP125988.1`, `genbank:NZ_CP145480.1`, `genbank:NZ_CP187932.1`, `genbank:NZ_CP192524.1`, `genbank:NZ_OZ477358.1`, `genbank:NZ_OZ477359.1`, `genbank:NZ_OZ477360.1`, `genbank:NZ_OZ477361.1`, `genbank:PZ138287.1`, `genbank:PZ407647.1`.

## Uncertainty And Blockers

1. The configured local Postgres connection from `.env` was reachable but had no application tables (`information_schema.tables` returned no non-system tables). I could not directly query current persisted rows in this session.
2. Because live DB rows were unavailable, this audit uses the latest committed/cached evaluation artifacts as the source of truth for current classifications. The latest quality and reprocess artifacts are internally consistent on the `99` unknown count.
3. I did not recommend deleting existing rows. Category 3 is a future ingestion/routing/training-lane recommendation requiring owner policy.
4. I did not inspect or change cached blobs directly after the live DB blocker; record-level evidence is inherited from the prior cached-blob audit and current reprocess delta.
