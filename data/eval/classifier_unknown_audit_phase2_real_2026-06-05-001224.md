# Classifier Unknown Audit: Phase 2 Real Corpus

- Generated at: `2026-06-05T00:12:24Z`
- Branch context requested: `phase2-real-generation`
- Scope: 104 records currently classified as `unknown` after RefSeq expansion
- Source snapshot: local Postgres `plasmids`, cached GenBank/RefSeq objects in the configured object store, parser/classifier code, `data/eval/quality/2026-06-03-034726-quality-report.json`, and `data/eval/reprocess/2026-06-03-034719-reprocess-all.json`
- Code edits: none
- Validation/constraint-engine surface: not inspected or changed
- Commits: none

## Summary Counts

| Category | Count | Interpretation |
| --- | ---: | --- |
| a: legitimately unusual, keep `unknown` | 14 | Real complete public plasmids/episomes that are biologically useful as natural/reference plasmid examples, but do not fit engineered vector profiles. |
| b: existing profile, classifier/parser rule gap | 5 | Engineered vector records whose title and component evidence fit existing profiles, but current rules still lack narrow evidence paths. |
| c: may not belong in this corpus lane | 85 | Natural isolate, AMR/mobile, unnamed RefSeq, sparse/partial, or irrelevant plasmid records that are poor engineered-vector generation templates and should be filtered or separated in future ingestion. |
| Total unknown records audited | 104 | Matches the latest quality report unknown count. |

## Methodology

1. Used the latest quality report to confirm the current corpus has 256 records, 104 unknown profiles, 0 parse errors, and 50 records from the RefSeq expansion lane.
2. Used the latest reprocess report to identify current classifier outputs without modifying persisted data.
3. Re-ran read-only parsing of cached raw GenBank/RefSeq records through `parse_genbank_text` to extract feature type counts and representative feature names for the records still classified as `unknown`.
4. Categorized records by public annotation vocabulary: engineered vector titles, cloning/expression/shuttle terms, ORI/marker/promoter/MCS/tag/terminator evidence, natural isolate wording, mobility/conjugation terms, AMR/metal-resistance payload terms, sparse hypothetical-protein records, RefSeq `NC_`/`NZ_` provenance, and partial/unverified wording.
5. Treated category b as classifier/parser refinement candidates only when the record has explicit engineered-vector metadata and corroborating component evidence. Natural plasmid resistance genes were not treated as engineered selectable-marker evidence.

## Category A: Legitimately Unusual Records To Keep Unknown

These should remain `unknown`; they are not misclassified engineered vectors. They are defensible as public reference/natural plasmid records for comparative retrieval, provenance calibration, or natural replicon background, but not as generation templates.

| ID | Name | Evidence | Profile disposition |
| --- | --- | --- | --- |
| `genbank:CP121282.1` | Halobacterium sp. CBA1161 plasmid pCBA1161-02 | Archaeal natural plasmid; 16,486 bp; GOI-only features including hypothetical proteins, HNH endonuclease, recombinase/integrase, IS element. | Keep `unknown`; unusual archaeal natural plasmid, not shuttle/vector architecture. |
| `genbank:NC_002059.1` | Butyrivibrio fibrisolvens plasmid pOM1 | RefSeq complete natural plasmid; mobV and RepL-like maintenance protein; no engineered marker/MCS/promoter cassette. | Keep `unknown`; natural anaerobe plasmid reference. |
| `genbank:NC_002139.1` | Pseudoselenomonas ruminantium plasmid pSR1 | RefSeq complete natural plasmid; radical SAM, mnmL, sensor/HAMP-domain proteins. | Keep `unknown`; natural rumen plasmid reference. |
| `genbank:NC_004962.1` | Pseudoselenomonas ruminantium plasmid pJW1 | Small RefSeq plasmid; MarR regulator and hypothetical protein only. | Keep `unknown`; sparse natural plasmid. |
| `genbank:NC_004977.1` | Pseudoselenomonas ruminantium plasmid pONE430 | Small RefSeq plasmid; RepL-like maintenance protein only. | Keep `unknown`; minimal natural replicon. |
| `genbank:NC_004986.1` | Pseudoselenomonas ruminantium plasmid pONE429 | Small RefSeq plasmid; hypothetical protein and RepL-like maintenance protein. | Keep `unknown`; minimal natural replicon. |
| `genbank:NC_006857.1` | Pseudoselenomonas ruminantium plasmid pSRD191 | Small RefSeq plasmid; RepL-like maintenance protein only. | Keep `unknown`; minimal natural replicon. |
| `genbank:NC_013776.1` | Pseudoselenomonas ruminantium plasmid pSRD192 | Small RefSeq plasmid; hypothetical protein only. | Keep `unknown`; sparse natural plasmid. |
| `genbank:NC_015313.1` | Pseudonocardia benzenivorans CB1190 plasmid pPSED03 | Complete natural plasmid; primase, ParA, FtsK/SpoIIIE-like proteins; no engineered vector metadata. | Keep `unknown`; natural actinobacterial plasmid reference. |
| `genbank:NC_016045.1` | Pseudoselenomonas ruminantium plasmid pSRD77 | Small RefSeq plasmid; RepL-like maintenance protein only. | Keep `unknown`; minimal natural replicon. |
| `genbank:NC_016600.1` | Pseudonocardia benzenivorans CB1190 plasmid pPSED02 | Complete natural plasmid; VirB6/TrbL, transporter, transposase/metabolic CDS. | Keep `unknown`; natural mobile/reference plasmid, not engineered. |
| `genbank:NC_017772.1` | Pseudonocardia benzenivorans CB1190 plasmid pPSED02 | Complete natural plasmid; relaxase/mobilization, helicase, TraM-like features. | Keep `unknown`; alternate natural plasmid/reference record. |
| `genbank:NZ_M60875.1` | Mycolicibacterium fortuitum plasmid pAL5000 | Natural mycobacterial plasmid; replication initiation protein; no engineered vector cassette in this record. | Keep `unknown`; natural replicon background only. |
| `genbank:PX275371.1` | Zygosaccharomyces bailii plasmid pZB1 | Natural yeast plasmid; FLP only; no engineered yeast marker, bacterial marker, MCS, ARS/CEN shuttle context. | Keep `unknown`; natural episome, not yeast shuttle vector. |

## Category B: Existing Profile But Rule/Parser Gap

These are the records most suitable for QUALITY-2/CLASSIFY-2 implementation. Fixes should be narrow and regression-tested against category c natural plasmids.

| ID | Name | Existing profile fit | Evidence | Current gap |
| --- | --- | --- | --- | --- |
| `genbank:AF050464.1` | Expression vector pKIL-HIS3 | `bacterial_expression_vector` candidate | Engineered expression-vector title; 4,806 bp; ampR marker; ORI; lac promoter region; lacIq; ccdB. | Current bacterial-expression evidence requires stronger promoter/tag/payload cassette support. Add narrow pKIL/ccdB-lacIq vector-title support only with ORI+marker+promoter. |
| `genbank:AF097552.1` | Expression vector unc-68:GFP(1-8) | `mammalian_reporter_vector` or expression/reporter-family candidate | Engineered expression-vector title; GFP in title; AmpR/bla and pMB1/pUC origin; ryanodine receptor payload. | Parser does not expose GFP/reporter evidence from title and lacks promoter/terminator annotations. Any rule should require explicit GFP title plus vector metadata, not generic GOI. |
| `genbank:AF147464.1` | T7 expression vector pViet | `bacterial_expression_vector` candidate | Explicit T7 expression-vector title; bla; T7 terminator; his6; lacI. | ORI and T7 promoter are not parsed, leaving marker/terminator/tag evidence insufficient. Prefer parser evidence for ORI/promoter/tag rather than broad title-only admission. |
| `genbank:AY236524.1` | Cloning vector pLZ42 | `bacterial_cloning_vector` candidate | Explicit cloning-vector title; two marker features Bla and Cat; lac UV5 promoter; 3,890 bp. | No ORI/MCS/backbone signal parsed. Could classify only if trusted vector metadata plus two engineered markers plus lac/backbone evidence is accepted. |
| `genbank:U09128.1` | pSacBII P1 cloning vector with sacB, kilA, repL and kanamycin resistance genes | `bacterial_cloning_vector` candidate | Explicit P1 cloning-vector title; aminoglycoside marker; SP6/T7/E. coli promoter evidence; sacB, repL, kilA. | `repL` remains GOI, no P1/replicon ORI or MCS detected. Add P1/repL replicon support only in trusted engineered cloning-vector metadata contexts. |

## Category C: May Not Belong In This Corpus Lane

These records are real public plasmid records in many cases, but they are poor matches for an engineered-vector generation corpus lane. Recommended action is not immediate deletion without owner policy; it is to filter, separate, or downweight these during future ingestion/training manifest construction.

| ID | Name | Evidence | Recommended disposition |
| --- | --- | --- | --- |
| `genbank:CP190835.1` | Staphylococcus hominis strain LaCa_103 plasmid pLaCa_103a | Natural strain plasmid; repA, MobA/MobL, MobC, MFS transporter, toxin-antitoxin, IS6, msr(A), Mph(C). | Filter/separate as natural clinical mobile/resistance plasmid. |
| `genbank:CP190836.1` | Staphylococcus hominis strain LaCa_103 plasmid pLaCa_103b | Natural strain plasmid; protein rep only. | Filter/separate as sparse natural isolate plasmid. |
| `genbank:CP190842.1` | Staphylococcus haemolyticus strain LaCa_147 plasmid pLaCa_147a | Natural strain plasmid; repA, cadA/cadC, IS257, metabolic genes. | Filter/separate as natural isolate plasmid. |
| `genbank:CP190845.1` | Corynebacterium accolens strain LaCa_114 plasmid pLaCa_114a | Natural strain plasmid; only hypothetical proteins; duplicate-cluster member. | Filter/separate as sparse natural plasmid. |
| `genbank:CP190847.1` | Corynebacterium accolens strain LaCa_113 plasmid pLaCa_113a | Natural strain plasmid; only hypothetical proteins; duplicate-cluster member. | Filter/separate as sparse natural plasmid. |
| `genbank:CP190849.1` | Staphylococcus epidermidis strain LaCa_111 plasmid pLaCa_111a | Natural strain plasmid; repA, toxin-antitoxin, IS6/IS257, hxl genes, metabolic CDS. | Filter/separate as natural mobile plasmid. |
| `genbank:CP190850.1` | Staphylococcus epidermidis strain LaCa_111 plasmid pLaCa_111b | Natural strain plasmid; RepB, TetR/AcrR-like marker, transporters, toxin-antitoxin. | Filter/separate; resistance regulator is payload/noise, not vector marker. |
| `genbank:CP190851.1` | Staphylococcus epidermidis strain LaCa_111 plasmid pLaCa_111c | Natural strain plasmid; RepB only; duplicate-cluster member. | Filter/separate as minimal natural replicon. |
| `genbank:CP190852.1` | Staphylococcus epidermidis strain LaCa_111 plasmid pLaCa_111d | Natural strain plasmid; replication initiation factor only. | Filter/separate as minimal natural replicon. |
| `genbank:CP190854.1` | Staphylococcus epidermidis strain LaCa_110 plasmid pLaCa_110a | Large natural mobile plasmid; VirD4/VirB4, sortase, CHAP, lysostaphin resistance. | Filter/separate as large natural mobile/resistance plasmid. |
| `genbank:CP190855.1` | Staphylococcus epidermidis strain LaCa_110 plasmid pLaCa_110b | Natural strain plasmid; RepB only; duplicate-cluster member. | Filter/separate as minimal natural replicon. |
| `genbank:CP190857.1` | Staphylococcus epidermidis strain LaCa_109 plasmid pLaCa_109a | Natural strain plasmid; cadD, qac/qacR-like, metal transport, IS6, msr/Mph-like context. | Filter/separate as natural resistance/mobile plasmid. |
| `genbank:CP190859.1` | Corynebacterium accolens strain LaCa_108 plasmid pLaCa_108a | Natural strain plasmid; hypothetical proteins only. | Filter/separate as sparse natural plasmid. |
| `genbank:CP190864.1` | Corynebacterium sp. LaCa_102 plasmid pLaCa_102a | Natural strain plasmid; replication initiation, AAA ATPase, recombinase, ABC-domain proteins. | Filter/separate as natural plasmid. |
| `genbank:CP190865.1` | Corynebacterium sp. LaCa_102 plasmid pLaCa_102b | Natural strain plasmid; RepA, transposase, recombinase. | Filter/separate as natural mobile plasmid. |
| `genbank:CP190867.1` | Corynebacterium sp. LaCa_100 plasmid pLaCa_100a | Natural strain plasmid; replication initiation, MarR regulator, AAA ATPase. | Filter/separate as natural plasmid. |
| `genbank:CP190868.1` | Corynebacterium sp. LaCa_100 plasmid pLaCa_100b | Natural strain plasmid; RepA, transposase, recombinase. | Filter/separate as natural mobile plasmid. |
| `genbank:CP190870.1` | Corynebacterium accolens strain LaCa_98 plasmid pLaCa_98a | Natural strain plasmid; hypothetical proteins only. | Filter/separate as sparse natural plasmid. |
| `genbank:CP190872.1` | Staphylococcus capitis strain LaCa_96 plasmid pLaCa_96a | Natural strain plasmid; repA, toxin-antitoxin, transporters, IS6. | Filter/separate as natural mobile plasmid. |
| `genbank:CP190873.1` | Staphylococcus capitis strain LaCa_96 plasmid pLaCa_96b | Natural strain plasmid; RepB only. | Filter/separate as minimal natural replicon. |
| `genbank:CP190874.1` | Staphylococcus capitis strain LaCa_96 plasmid pLaCa_96c | Natural strain plasmid; replication initiation factor only. | Filter/separate as minimal natural replicon. |
| `genbank:CP190875.1` | Staphylococcus capitis strain LaCa_96 plasmid pLaCa_96d | Natural strain plasmid; replication initiation factor only. | Filter/separate as minimal natural replicon. |
| `genbank:CP190876.1` | Staphylococcus capitis strain LaCa_96 plasmid pLaCa_96e | Natural strain plasmid; rep and hypothetical protein. | Filter/separate as sparse natural replicon. |
| `genbank:CP190878.1` | Staphylococcus capitis strain LaCa_95 plasmid pLaCa_95a | Natural strain plasmid; LaCa_96a-like rep/toxin/transport/IS features. | Filter/separate as natural mobile plasmid. |
| `genbank:CP190879.1` | Staphylococcus capitis strain LaCa_95 plasmid pLaCa_95b | Natural strain plasmid; RepB only. | Filter/separate as minimal natural replicon. |
| `genbank:CP191035.1` | Corynebacterium sp. LaCa_204 plasmid pLaCa_204a | Natural strain plasmid; replication, recombinase, IS1249 transposase, mobF. | Filter/separate as natural mobile plasmid. |
| `genbank:CP191036.1` | Corynebacterium sp. LaCa_204 plasmid pLaCa_204b | Natural strain plasmid; RepA, transposase, recombinase. | Filter/separate as natural mobile plasmid. |
| `genbank:CP191037.1` | Corynebacterium sp. LaCa_204 plasmid pLaCa_204c | Natural strain plasmid; rep and hypothetical proteins. | Filter/separate as sparse natural replicon. |
| `genbank:CP191042.1` | Staphylococcus epidermidis strain LaCa_201 plasmid pLaCa_201a | Natural strain plasmid; RepB and cadmium resistance transporter. | Filter/separate; resistance payload is not vector selection evidence. |
| `genbank:CP191051.1` | Staphylococcus epidermidis strain LaCa_194 plasmid pLaCa_194b | Natural strain plasmid; RepB only. | Filter/separate as minimal natural replicon. |
| `genbank:CP191052.1` | Staphylococcus epidermidis strain LaCa_194 plasmid pLaCa_194c | Natural strain plasmid; replication initiation factor only. | Filter/separate as minimal natural replicon. |
| `genbank:CP191053.1` | Staphylococcus epidermidis strain LaCa_194 plasmid pLaCa_194d | Natural strain plasmid; replication initiation factor only. | Filter/separate as minimal natural replicon. |
| `genbank:CP191054.1` | Staphylococcus epidermidis strain LaCa_194 plasmid pLaCa_194e | Natural strain plasmid; protein rep only. | Filter/separate as minimal natural replicon. |
| `genbank:CP191060.1` | Staphylococcus aureus strain LaCa_187 plasmid pLaCa_187a | Natural resistance/mobile plasmid; blaZ/blaR1/blaI/cadD, mobV, recombinase, bacteriocin. | Filter/separate as natural clinical AMR plasmid. |
| `genbank:CP191063.1` | Staphylococcus aureus strain LaCa_185 plasmid pLaCa_185a | Natural resistance/mobile plasmid; cadD, blaI, blaR1, blaZ, repA, recombinase. | Filter/separate as natural clinical AMR plasmid. |
| `genbank:CP191068.1` | Staphylococcus epidermidis strain LaCa_160 plasmid pLaCa_160a | Large natural mobile plasmid; VirD4/VirB4, CHAP, topoisomerase, mobP2. | Filter/separate as large natural mobile plasmid. |
| `genbank:CP191069.1` | Staphylococcus epidermidis strain LaCa_160 plasmid pLaCa_160b | Natural mobile plasmid; IS3/ISL3/IS6, transporter, toxin-antitoxin. | Filter/separate as natural mobile plasmid. |
| `genbank:CP191070.1` | Staphylococcus epidermidis strain LaCa_160 plasmid pLaCa_160c | Natural strain plasmid; RepB only. | Filter/separate as minimal natural replicon. |
| `genbank:CP191071.1` | Staphylococcus epidermidis strain LaCa_160 plasmid pLaCa_160d | Natural plasmid; ArdC-like ssDNA-binding protein and lysostaphin resistance. | Filter/separate as natural resistance-like plasmid. |
| `genbank:CP191072.1` | Staphylococcus epidermidis strain LaCa_160 plasmid pLaCa_160e | Natural strain plasmid; replication initiation factor only. | Filter/separate as minimal natural replicon. |
| `genbank:CP191074.1` | Staphylococcus epidermidis strain LaCa_159 plasmid pLaCa_159a | Natural strain plasmid; repA, replication proteins, toxin-antitoxin, recombinase. | Filter/separate as natural mobile plasmid. |
| `genbank:CP191075.1` | Staphylococcus epidermidis strain LaCa_159 plasmid pLaCa_159b | Natural strain plasmid; RepB only. | Filter/separate as minimal natural replicon. |
| `genbank:CP191076.1` | Staphylococcus epidermidis strain LaCa_159 plasmid pLaCa_159c | Natural strain plasmid; replication initiation factor only. | Filter/separate as minimal natural replicon. |
| `genbank:CP191078.1` | Staphylococcus epidermidis strain LaCa_158 plasmid pLaCa_158a | Natural strain plasmid; RepB only. | Filter/separate as minimal natural replicon. |
| `genbank:CP196381.1` | Herbiconiux sp. J20-18 plasmid unnamed1 | Environmental/natural unnamed plasmid; 38,545 bp; one hypothetical protein spanning sparse annotation. | Filter/separate as unnamed sparse environmental plasmid. |
| `genbank:NZ_CP054601.1` | Pseudosulfitobacter pseudonitzschiae strain H46 plasmid unnamed2 | RefSeq natural strain plasmid; metabolic/regulatory CDS; unnamed. | Filter/separate as natural unnamed RefSeq plasmid. |
| `genbank:NZ_CP054605.1` | Pseudosulfitobacter pseudonitzschiae strain H46 plasmid unnamed6 | RefSeq natural strain plasmid; 23,927 bp; hypothetical protein only; unnamed. | Filter/separate as sparse unnamed RefSeq plasmid. |
| `genbank:NZ_CP054607.1` | Pseudosulfitobacter pseudonitzschiae strain H46 plasmid unnamed8 | RefSeq natural strain plasmid; 49,860 bp; one DUF protein; unnamed. | Filter/separate as large sparse unnamed RefSeq plasmid. |
| `genbank:NZ_CP071509.1` | Staphylococcus haemolyticus strain 7b plasmid pSH_7b_1 | Natural strain plasmid; 39 CDS, serine hydrolase marker-like call, metal transport, toxin-antitoxin. | Filter/separate as natural clinical plasmid. |
| `genbank:NZ_CP071510.1` | Staphylococcus haemolyticus strain 7b plasmid pSH_7b_2 | Natural strain plasmid; VraH peptide resistance, IS257, stress/transport genes. | Filter/separate as natural resistance-like plasmid. |
| `genbank:NZ_CP071511.1` | Staphylococcus haemolyticus strain 7b plasmid pSH_7b_3 | Natural strain plasmid; mobV only. | Filter/separate as sparse mobile plasmid. |
| `genbank:NZ_CP071513.1` | Staphylococcus haemolyticus strain 1b plasmid pSH_1b_1 | Natural strain plasmid; 41,143 bp; metal transport, toxin-antitoxin, marker-like hydrolase. | Filter/separate as natural clinical plasmid. |
| `genbank:NZ_CP071514.1` | Staphylococcus haemolyticus strain 1b plasmid pSH_1b_2 | Natural strain plasmid with vector-like contaminants/signals; lacI, T7 terminator, f1 origin, pMB1/pUC origin, aph(3')-Ia. | Human-review filter candidate; possible assembly/vector artifact or contaminant rather than product-useful plasmid. |
| `genbank:NZ_CP071515.1` | Staphylococcus haemolyticus strain 1b plasmid pSH_1b_3 | Natural strain plasmid; replication protein and mobV. | Filter/separate as sparse mobile plasmid. |
| `genbank:NZ_CP073311.1` | Enterobacter cloacae strain CZ862 plasmid pCZ862_1 | RefSeq natural strain plasmid; RepL only; 1,334 bp. | Filter/separate as tiny natural replicon. |
| `genbank:NZ_CP073312.1` | Enterobacter cloacae strain CZ862 plasmid pCZ862_ColRNAI | RefSeq natural strain plasmid; hypothetical protein only. | Filter/separate as sparse natural plasmid. |
| `genbank:NZ_CP073313.1` | Enterobacter cloacae strain CZ862 plasmid pCZ862_GES1_GES5 | Natural AMR plasmid; GES-5, GES-1, AadA; relaxase. | Filter/separate as AMR/mobile plasmid outside engineered-vector lane. |
| `genbank:NZ_CP073314.1` | Enterobacter cloacae strain CZ862 plasmid pCZ862_IncFIB | Natural AMR plasmid; AadA2, sul1, QnrB2, par/tra/tnp genes. | Filter/separate as AMR/mobile plasmid outside engineered-vector lane. |
| `genbank:NZ_CP086918.1` | Pseudosulfitobacter pseudonitzschiae strain SC1-34 plasmid P9 | RefSeq natural strain plasmid; lipid-transfer protein only. | Filter/separate as sparse natural RefSeq plasmid. |
| `genbank:NZ_CP086920.1` | Pseudosulfitobacter pseudonitzschiae strain SC1-32 plasmid P1 | RefSeq natural strain plasmid; LysR regulator and putative quinol monooxygenase marker-like call. | Filter/separate as natural metabolic plasmid. |
| `genbank:NZ_CP086929.1` | Pseudosulfitobacter pseudonitzschiae strain SC1-32 plasmid P10 | RefSeq natural strain plasmid; Tn3 family transposase only. | Filter/separate as mobile-element-heavy plasmid. |
| `genbank:NZ_CP086935.1` | Pseudosulfitobacter pseudonitzschiae strain SC1-30 plasmid P5 | RefSeq natural strain plasmid; thiolase family protein only. | Filter/separate as sparse natural plasmid. |
| `genbank:NZ_CP086937.1` | Pseudosulfitobacter pseudonitzschiae strain SC1-30 plasmid P7 | RefSeq natural strain plasmid; mobQ and putative quinol monooxygenase. | Filter/separate as natural mobile/metabolic plasmid. |
| `genbank:NZ_CP086939.1` | Pseudosulfitobacter pseudonitzschiae strain SC1-29 plasmid P1 | RefSeq natural strain plasmid; adenylate-forming enzyme only. | Filter/separate as sparse natural plasmid. |
| `genbank:NZ_CP086940.1` | Pseudosulfitobacter pseudonitzschiae strain SC1-29 plasmid P2 | Natural strain plasmid; mobQ, transporters, oxidoreductases, transposase/recombinase. | Filter/separate as natural mobile/metabolic plasmid. |
| `genbank:NZ_CP087040.1` | Pseudosulfitobacter pseudonitzschiae strain MC52-67 plasmid P8 | RefSeq natural strain plasmid; LysR regulator only. | Filter/separate as sparse natural plasmid. |
| `genbank:NZ_CP087081.1` | Pseudosulfitobacter pseudonitzschiae strain MC36-14 plasmid P9 | RefSeq natural strain plasmid; ABC transporter ATP-binding protein only. | Filter/separate as sparse natural plasmid. |
| `genbank:NZ_CP087393.1` | Pectobacterium parvum strain FN20211 plasmid unnamed1 | RefSeq natural unnamed plasmid; toxin-antitoxin, integrase, hypothetical proteins. | Filter/separate as unnamed natural mobile plasmid. |
| `genbank:NZ_CP087394.1` | Pectobacterium parvum strain FN20211 plasmid unnamed2 | RefSeq natural unnamed plasmid; replication initiation, toxin-antitoxin, mobilization proteins, reverse transcriptase. | Filter/separate as unnamed natural mobile plasmid. |
| `genbank:NZ_CP091883.1` | Peribacillus frigoritolerans strain JHS1 plasmid p16118 | RefSeq natural strain plasmid; glycosyltransferase only. | Filter/separate as sparse natural plasmid. |
| `genbank:NZ_CP121831.1` | Aeromonas veronii strain ANYA 18661 plasmid unnamed2 | Natural unnamed plasmid; toxin-antitoxin, parA/ParG, RepB, integrase, transposase. | Filter/separate as unnamed natural mobile plasmid. |
| `genbank:NZ_CP121838.1` | Aeromonas veronii strain ANYA 18263 plasmid unnamed | Natural unnamed plasmid; hypothetical protein only. | Filter/separate as sparse unnamed plasmid. |
| `genbank:NZ_CP121852.1` | Aeromonas veronii strain ANYA 14022 plasmid unnamed1 | Natural unnamed plasmid; no parsed features. | Filter/separate as annotation-sparse unnamed plasmid. |
| `genbank:NZ_CP121858.1` | Aeromonas veronii strain LOID 15995 plasmid unnamed1 | Natural unnamed plasmid; parA/ParG, MobA/MobL, hypothetical proteins. | Filter/separate as unnamed mobile plasmid. |
| `genbank:NZ_CP121860.1` | Aeromonas veronii strain LOID 15995 plasmid unnamed2 | Natural unnamed plasmid; hypothetical protein only. | Filter/separate as sparse unnamed plasmid. |
| `genbank:NZ_CP125988.1` | Myroides odoratimimus strain 31 plasmid unnamed | Natural unnamed plasmid; 43,223 bp; one hypothetical protein. | Filter/separate as large sparse unnamed plasmid. |
| `genbank:NZ_CP145480.1` | Proteus mirabilis strain pmi68 plasmid pWF3430 | Natural strain plasmid; replication protein, MobA/MobL, TraD. | Filter/separate as natural mobile plasmid. |
| `genbank:NZ_CP187932.1` | Weissella paramesenteroides strain A47_1 plasmid p1 | Natural plasmid; fexB, transposase, recombinase, type IV secretion/conjugation, relaxase. | Filter/separate as natural resistance/mobile plasmid. |
| `genbank:NZ_CP192524.1` | Xanthomonas oryzae pv. oryzae strain GXB1-2 plasmid unnamed2 | Natural unnamed plasmid; tssI only. | Filter/separate as sparse unnamed plasmid. |
| `genbank:NZ_OZ477358.1` | Shigella sonnei isolate B31 plasmid 2 | Natural isolate plasmid; hypothetical protein only. | Filter/separate as sparse isolate plasmid. |
| `genbank:NZ_OZ477359.1` | Shigella sonnei isolate B31 plasmid 3 | Natural isolate plasmid; MobA/MobL, colicin-like bacteriocin, replication protein. | Filter/separate as natural mobile/bacteriocin plasmid. |
| `genbank:NZ_OZ477360.1` | Shigella sonnei isolate B31 plasmid 4 | Natural isolate plasmid; protein rep only. | Filter/separate as minimal natural replicon. |
| `genbank:NZ_OZ477361.1` | Shigella sonnei isolate B31 plasmid 5 | Natural isolate plasmid with pMB1/pUC origin-like signal and adhesin; no vector metadata. | Filter/separate; do not promote on origin-only signal. |
| `genbank:PZ138287.1` | Aeromonas salmonicida strain 2402/89 plasmid pRAS1_2402_89 | Natural resistance/mobile plasmid; tetA/tetR/sul1/dfrA16, mobC, virD2, tra/virB transfer genes. | Keep only if comparative retrieval is explicitly desired; exclude from engineered-vector generation templates. |
| `genbank:PZ407647.1` | UNVERIFIED Staphylococcus aureus aminoglycoside resistance locus | Partial/unverified resistance-gene record; 1,046 bp; aacA and aphD markers. | Filter out as partial/unverified AMR locus, not useful plasmid template. |

## Top Recurring Rule-Gap Patterns

| Pattern | Records | Recommendation |
| --- | --- | --- |
| Engineered expression-vector titles with incomplete cassette evidence | `AF050464.1`, `AF097552.1`, `AF147464.1` | Add narrow metadata-backed expression/reporter rules only when title terms are explicit and at least two component classes corroborate the title. Avoid generic `expression vector` admission. |
| Engineered cloning-vector records missing ORI/MCS parsing | `AY236524.1`, `U09128.1` | Improve parser support for P1/repL or trusted engineered-vector replicon terms only in vector-title contexts. Do not map natural `rep`, `RepA`, or `RepB` to engineered ORI support globally. |
| Resistance genes in natural plasmids look like selectable markers | Many Staphylococcus, Enterobacter, Aeromonas, Weissella records | Keep natural resistance genes as payload/noise unless engineered vector metadata and selection-cassette context are present. |
| RefSeq expansion admits many natural complete plasmids | Most `NC_`/`NZ_` records | Separate broad RefSeq natural plasmids from engineered-vector ingestion; use stricter title/component gates for generation corpora. |
| Sparse unnamed plasmids inflate unknown count | `NZ_CP054605.1`, `NZ_CP054607.1`, `NZ_CP121852.1`, `NZ_CP125988.1`, and similar | Filter records with `unnamed` plus no engineered metadata and fewer than a small number of informative non-hypothetical features. |
| Natural plasmids with vector-like contamination/artifact signals | `NZ_CP071514.1`, `NZ_OZ477361.1` | Require explicit engineered-vector metadata before classification; consider human review or contamination/artifact flag if pMB1/f1/lac/T7 signals occur in natural isolate titles. |

## Recommended Classifier Refinements For Category B

1. Add a narrow pKIL/ccdB-lacIq bacterial-expression path for explicit engineered expression-vector titles with ORI, marker, promoter/regulator, and ccdB/lacIq evidence.
2. Add a narrow GFP-title reporter/expression path only when the record title explicitly contains GFP/EGFP and stored metadata clearly says expression vector; do not classify arbitrary GOI records as reporter vectors.
3. Improve T7 expression-vector parsing for pViet-like records by detecting missing ORI/promoter/tag evidence from trusted annotations before relaxing classification.
4. Add P1/repL replicon support only when metadata contains `P1 cloning vector` or equivalent engineered cloning-vector wording plus marker/promoter/MCS or sacB/kilA cassette evidence.
5. Consider a cautious two-marker cloning-vector fallback for explicit engineered cloning-vector titles such as pLZ42, but require trusted vector metadata and at least one backbone/promoter/MCS-like corroborating signal.

## Recommended Future Ingestion Filters For Category C

1. For engineered-vector generation corpora, exclude titles matching natural isolate patterns such as `strain ... plasmid`, `isolate ... plasmid`, `unnamed`, or `complete sequence` unless they also contain trusted engineered-vector terms such as `cloning vector`, `expression vector`, `shuttle vector`, `phagemid cloning vector`, or a known curated vector family.
2. Exclude or route to a separate natural-plasmid lane records dominated by mobility and conjugation vocabulary: `mob`, `relaxase`, `tra`, `virB`, `virD`, `type IV secretion`, `integrase`, `transposase`, `IS`, `toxin-antitoxin`, `partition`, `ParA/ParB`, and sparse `RepA/RepB/RepL` annotations.
3. Exclude or downweight natural AMR/metal-resistance plasmids for generation templates when marker-like calls are public-health payloads rather than engineered selection cassettes: `blaZ`, `blaR1`, `blaI`, `GES`, `aadA`, `qnr`, `sul1`, `tetA`, `tetR`, `dfrA16`, `aacA`, `aphD`, `cadD`, `fexB`, `msr(A)`, `Mph(C)`, `VraH`.
4. Exclude partial/unverified records and short resistance loci, especially titles containing `UNVERIFIED` or `partial sequence`.
5. Add a sparse-annotation filter for records with no engineered title, no parsed promoter/MCS/terminator, and only hypothetical/replication/maintenance CDS.
6. Keep broad RefSeq natural plasmid ingestion as a separate retrieval/comparative lane only if product policy explicitly wants natural-plasmid context; do not mix these records into phase-2 generation training targets by default.

## Explicit Non-Action Items That Should Stay Unknown

1. Do not add a new engineered profile for natural plasmids, natural mobile plasmids, AMR plasmids, or environmental plasmids from this cohort.
2. Do not globally classify `rep`, `RepA`, `RepB`, or `RepL` as engineered ORI evidence; natural plasmids would be false positives.
3. Do not globally treat resistance genes in natural isolate records as engineered selectable-marker evidence.
4. Do not classify natural yeast plasmids such as `PX275371.1` pZB1 as `yeast_shuttle_vector` without engineered marker plus shuttle/vector metadata.
5. Do not classify `NZ_CP071514.1` or `NZ_OZ477361.1` from vector-like signals alone; natural isolate title context should remain a guardrail unless human review identifies an artifact/contaminant policy.
6. Do not use category c as automatic deletion approval. It is a future ingestion/training-lane policy recommendation requiring owner decision.

## Human-Decision Items Before QUALITY-2 Implementation

1. Decide whether broad natural RefSeq plasmids remain in the main corpus for comparative retrieval or move to a separate non-template lane.
2. Decide whether natural AMR/mobile plasmids such as `PZ138287.1` should remain accessible for retrieval/evaluation examples or be excluded from product-facing corpora.
3. Decide the threshold for sparse natural RefSeq filtering, such as fewer than 2 informative non-hypothetical features or no engineered-vector title plus no parsed promoter/MCS/terminator.
4. Decide whether vector-like signals inside natural isolate records trigger human curation, contamination/artifact labeling, or simple exclusion from engineered-vector lanes.
