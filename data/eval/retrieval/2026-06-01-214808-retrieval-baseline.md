# Retrieval Evaluation Report

- Generated at: `2026-06-01T21:48:08.292099+00:00`
- Gold file: `data/eval/retrieval_gold.jsonl`
- Queries: `21`
- Retrieval queries scored: `20`
- Clarification queries: `1`
- Top K: `5`
- Top-1 hit rate: `0.850`
- Top-5 hit rate: `1.000`
- Clarification pass rate: `1.000`
- MRR: `0.917`

## Per-Query Results

### 1. I need a simple high-copy cloning vector for routine plasmid cloning in E. coli.

- Acceptable IDs: `pUC19, pUC18, pBluescript-II-SK-plus, pBluescript-II-SK-minus, pBR322, pACYC184`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pUC19` pUC19c score=`0.7671` fields=`semantic, vector_type, organism, application`
- 2. `curated:pUC18` pUC18 score=`0.7599` fields=`semantic, vector_type, organism, application`
- 3. `genbank:AY428809.1` Cloning vector pSUP202, complete sequence score=`0.7283` fields=`semantic, vector_type, organism, application`
- 4. `genbank:U47626.2` Cloning vector PinPoint<TM> Xa-1, complete sequence score=`0.7079` fields=`semantic, vector_type, organism, application`
- 5. `curated:pBR322` pBR322 score=`0.7049` fields=`semantic, vector_type, organism, application`

Rationale: These are curated bacterial cloning backbones with standard cloning-friendly features such as pUC/pMB1 origins, MCSs, and antibiotic selection.
Source: Curated seed manifest entries in packages/data_pipeline/ingest/curated_seed_manifest.yaml

### 2. Which curated plasmid would you use for GST-tagged bacterial protein expression in E. coli?

- Acceptable IDs: `pGEX-4T-1`
- Result: `hit at rank 2`
- Reciprocal rank: `0.500`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pUC18` pUC18 score=`0.6669` fields=`semantic, organism, source, genes`
- 2. `curated:pGEX-4T-1` pGEX-4T-1 score=`0.6055` fields=`semantic, organism, source, genes, tags`
- 3. `curated:pBR322` pBR322 score=`0.5933` fields=`semantic, organism, source, genes`
- 4. `curated:pUC19` pUC19c score=`0.5838` fields=`semantic, organism, source, genes`
- 5. `curated:pEGFP-N1` pEGFP-N1 score=`0.5760` fields=`semantic, organism, source, genes`

Rationale: pGEX-4T-1 is explicitly annotated as a GST fusion bacterial expression backbone with tac/lac regulation.
Source: Curated seed manifest entry for pGEX-4T-1

### 3. I need a mammalian reporter plasmid for GFP-based expression analysis in cultured cells.

- Acceptable IDs: `pEGFP-N1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pEGFP-N1` pEGFP-N1 score=`0.6872` fields=`semantic, vector_type, organism, genes, application`
- 2. `curated:pGL3-Basic` pGL3-Basic score=`0.6368` fields=`semantic, vector_type, organism`
- 3. `curated:pGL4-10-luc2` pGL4.10[luc2] score=`0.6277` fields=`semantic, vector_type, organism`
- 4. `genbank:AF058756.1` Cloning vector pFR-Luc, complete sequence score=`0.6137` fields=`semantic, vector_type, organism`
- 5. `genbank:U47121.2` Cloning vector pSI, mammalian expression vector, complete sequence score=`0.5511` fields=`semantic, vector_type, organism`

Rationale: pEGFP-N1 is curated as a CMV-driven mammalian C-terminal EGFP fusion reporter with a neomycin selectable marker.
Source: Curated seed manifest entry for pEGFP-N1

### 4. Which vector should I use for a luciferase reporter assay in mammalian cells?

- Acceptable IDs: `pGL3-Basic, pGL4-10-luc2`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pGL4-10-luc2` pGL4.10[luc2] score=`0.7294` fields=`semantic, vector_type, organism, genes`
- 2. `curated:pGL3-Basic` pGL3-Basic score=`0.7192` fields=`semantic, vector_type, organism, genes`
- 3. `genbank:AF058756.1` Cloning vector pFR-Luc, complete sequence score=`0.6621` fields=`semantic, vector_type, organism, genes`
- 4. `curated:pEGFP-N1` pEGFP-N1 score=`0.6316` fields=`semantic, vector_type, organism`
- 5. `genbank:U47121.2` Cloning vector pSI, mammalian expression vector, complete sequence score=`0.5588` fields=`semantic, vector_type, organism`

Rationale: Both curated plasmids are promoterless luciferase reporter vectors intended for reporter assays.
Source: Curated seed manifest entries for pGL3-Basic and pGL4.10[luc2]

### 5. I need a yeast shuttle vector with a selectable marker for yeast transformation and maintenance.

- Acceptable IDs: `pRS415, pRS416`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pRS415` pRS415 score=`0.8341` fields=`semantic, vector_type, organism`
- 2. `curated:pRS416` pRS416 score=`0.8327` fields=`semantic, vector_type, organism`
- 3. `genbank:PV135004.1` Zygosaccharomyces rouxii culture ATCC:56076 plasmid pSB3, complete sequence score=`0.6006` fields=`semantic, vector_type, organism`

Rationale: These curated vectors are yeast centromere shuttle plasmids with LEU2 or URA3 selection and CEN/ARS maintenance features.
Source: Curated seed manifest entries for pRS415 and pRS416

### 6. Recommend a low-copy bacterial cloning plasmid with chloramphenicol resistance.

- Acceptable IDs: `pACYC184`
- Result: `hit at rank 3`
- Reciprocal rank: `0.333`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:AY428809.1` Cloning vector pSUP202, complete sequence score=`0.7657` fields=`semantic, vector_type, organism, markers, application`
- 2. `genbank:AF519766.1` Cloning vector pMAK705, complete sequence score=`0.7208` fields=`semantic, vector_type, organism, markers, application`
- 3. `curated:pACYC184` pACYC184 score=`0.7203` fields=`semantic, vector_type, organism, markers, application`

Rationale: pACYC184 is curated as a low-copy p15A-origin cloning vector with chloramphenicol and tetracycline resistance.
Source: Curated seed manifest entry for pACYC184

### 7. I want a bacterial cloning plasmid with lacZ alpha selection and a standard pUC backbone.

- Acceptable IDs: `pUC19, pUC18, pBluescript-II-SK-plus, pBluescript-II-SK-minus`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pUC19` pUC19c score=`0.8092` fields=`semantic, vector_type, organism, application`
- 2. `curated:pUC18` pUC18 score=`0.7978` fields=`semantic, vector_type, organism, application`
- 3. `genbank:AY428809.1` Cloning vector pSUP202, complete sequence score=`0.7489` fields=`semantic, vector_type, organism, application`
- 4. `curated:pBluescript-II-SK-minus` pBluescript II SK(-) score=`0.7359` fields=`semantic, vector_type, organism, application`
- 5. `genbank:U47626.2` Cloning vector PinPoint<TM> Xa-1, complete sequence score=`0.7328` fields=`semantic, vector_type, organism, application`

Rationale: These curated records include pUC-family or lacZ alpha/MCS cloning backbones suitable for blue-white screening workflows.
Source: Curated seed manifest entries for the pUC and pBluescript vectors

### 8. Which curated source cloning vector carries both ampicillin and tetracycline resistance with a pMB1-derived replication region? Exclude GenBank-only matches like pSUP202.

- Acceptable IDs: `pBR322`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pBR322` pBR322 score=`0.7940` fields=`semantic, vector_type, organism, markers, source, application`

Rationale: pBR322 is the curated corpus match for the classic pMB1-derived AmpR/TetR cloning backbone. The provenance constraint excludes GenBank candidates such as pSUP202 even though they share overlapping bacterial-cloning and marker evidence.
Source: Curated seed manifest entry for pBR322 plus live local Postgres corpus verification on 2026-05-31 for the contrasting GenBank pSUP202 record

### 9. I need a phagemid cloning vector with an f1 origin, lacZ alpha MCS, and T7/T3 promoter sites.

- Acceptable IDs: `pBluescript-II-SK-plus, pBluescript-II-SK-minus`
- Result: `hit at rank 2`
- Reciprocal rank: `0.500`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pUC19` pUC19c score=`0.7998` fields=`semantic, vector_type, organism, application`
- 2. `curated:pBluescript-II-SK-minus` pBluescript II SK(-) score=`0.7964` fields=`semantic, vector_type, organism, application`
- 3. `curated:pUC18` pUC18 score=`0.7939` fields=`semantic, vector_type, organism, application`
- 4. `genbank:U47626.2` Cloning vector PinPoint<TM> Xa-1, complete sequence score=`0.7860` fields=`semantic, vector_type, organism, promoters, application`
- 5. `curated:pBluescript-II-SK-plus` pBluescript II SK(+) score=`0.7818` fields=`semantic, vector_type, organism, application`

Rationale: The pBluescript II SK records are curated phagemid cloning vectors; SK(+) explicitly includes f1 plus orientation, lacZ alpha/MCS, T7/T3 promoters, pUC origin, and bla, while SK(-) is the corresponding minus-orientation variant.
Source: Curated seed manifest entries for pBluescript-II-SK-plus and pBluescript-II-SK-minus

### 10. Recommend a high-copy ampicillin-resistant pUC plasmid when either MCS orientation is acceptable.

- Acceptable IDs: `pUC19, pUC18`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pUC19` pUC19c score=`0.8308` fields=`semantic, vector_type, organism, markers, application`
- 2. `curated:pUC18` pUC18 score=`0.8052` fields=`semantic, vector_type, organism, markers, application`
- 3. `genbank:AY428809.1` Cloning vector pSUP202, complete sequence score=`0.7910` fields=`semantic, vector_type, organism, markers, application`
- 4. `curated:pBR322` pBR322 score=`0.7627` fields=`semantic, vector_type, organism, markers, application`
- 5. `curated:pBluescript-II-SK-minus` pBluescript II SK(-) score=`0.7349` fields=`semantic, vector_type, organism, markers, application`

Rationale: pUC19 is curated as a high-copy pUC/pMB1-derived AmpR cloning vector with lacZ alpha/MCS, and pUC18 is curated as its sibling with reversed MCS orientation.
Source: Curated seed manifest entries for pUC19 and pUC18

### 11. Which mammalian EGFP fusion vector also provides G418 selection in cells and kanamycin selection in bacteria?

- Acceptable IDs: `pEGFP-N1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pEGFP-N1` pEGFP-N1 score=`0.6125` fields=`semantic, organism, markers, genes`

Rationale: pEGFP-N1 is curated as a CMV-driven C-terminal EGFP fusion vector with neomycin/G418 mammalian selection and a kanamycin bacterial marker.
Source: Curated seed manifest entry for pEGFP-N1

### 12. I need a yeast centromere shuttle plasmid specifically selected by URA3 rather than LEU2.

- Acceptable IDs: `pRS416`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pRS416` pRS416 score=`0.8545` fields=`semantic, vector_type, organism, markers`

Rationale: pRS416 is curated as a yeast centromere vector with a URA3 marker, whereas pRS415 carries LEU2.
Source: Curated seed manifest entries for pRS416 and pRS415

### 13. E. coli T7 expression vector, AmpR, with an MCS. Keep it simple.

- Acceptable IDs: `genbank:AF147463.1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:AF147463.1` T7 Expression vector pNam, complete sequence score=`0.7669` fields=`semantic, vector_type, organism, markers, promoters, application`
- 2. `curated:pGEX-4T-1` pGEX-4T-1 score=`0.6639` fields=`semantic, vector_type, organism, markers, application`
- 3. `genbank:U40578.1` Cloning vector pOR262, pINIIIompA3-rat P450 reductase expression vector, complete sequence score=`0.5860` fields=`semantic, vector_type, organism, markers, application`

Rationale: The GenBank pNam record is indexed as a bacterial expression vector with a T7 promoter, bla/AmpR selection, and a multiple cloning site. This terse query exercises bacterial-expression, host, and marker filters together.
Source: Live local Postgres corpus verification on 2026-05-31; GenBank AF147463.1 indexed metadata

### 14. For an E. coli cloning workflow, retrieve a backbone carrying ampicillin, tetracycline, and chloramphenicol resistance.

- Acceptable IDs: `genbank:AY428809.1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:AY428809.1` Cloning vector pSUP202, complete sequence score=`0.7263` fields=`semantic, organism, markers, application`

Rationale: The GenBank pSUP202 record is indexed as a bacterial cloning vector with bla/ampicillin, tet, and cat markers. Requiring all three markers distinguishes it from two-marker cloning backbones.
Source: Live local Postgres corpus verification on 2026-05-31; GenBank AY428809.1 indexed metadata

### 15. Need an E. coli-Pseudomonas broad-host-range shuttle vector with tetracycline resistance and lacZ alpha for blue/white screening.

- Acceptable IDs: `genbank:U07168.1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:U07168.1` Cloning vector pUCP26, Escherichia-Pseudomonas shuttle vector with tetracycline efflux protein (tet) and LacZ alpha peptide (lacZ alpha) genes, complete sequence score=`0.7800` fields=`semantic, vector_type, organism, markers`
- 2. `genbank:AY180162.1` Shuttle vector pRHBR17, complete sequence score=`0.7132` fields=`semantic, vector_type, organism, markers`

Rationale: The GenBank pUCP26 record is indexed as a general shuttle vector with broad-host-range use, tet selection, lacZ alpha, and an MCS. The query tests shuttle-host intent and a hard tetracycline marker filter.
Source: Live local Postgres corpus verification on 2026-05-31; GenBank U07168.1 indexed metadata

### 16. E. coli SpecR shuttle vector.

- Acceptable IDs: `genbank:AF216802.1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:AF216802.1` Shuttle vector pDL278, complete sequence score=`0.7527` fields=`semantic, vector_type, organism, markers`

Rationale: The GenBank pDL278 record is indexed as a general shuttle vector with spectinomycin adenyltransferase. The intentionally terse query tests controlled-marker normalization and shuttle-vector filtering.
Source: Live local Postgres corpus verification on 2026-05-31; GenBank AF216802.1 indexed metadata

### 17. For transient mammalian expression, I need an ampicillin-selected pSI-style plasmid with an SV40 enhancer and early promoter.

- Acceptable IDs: `genbank:U47121.2`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:U47121.2` Cloning vector pSI, mammalian expression vector, complete sequence score=`1.0000` fields=`lexical_name, vector_type, organism, markers`
- 2. `curated:pGL3-Basic` pGL3-Basic score=`0.6479` fields=`semantic, vector_type, organism, markers`
- 3. `genbank:AF058756.1` Cloning vector pFR-Luc, complete sequence score=`0.6065` fields=`semantic, vector_type, organism, markers`
- 4. `genbank:U47120.2` Cloning vector pCI-neo, mammalian expression vector, complete sequence score=`0.6019` fields=`semantic, vector_type, organism, markers, promoters, application`
- 5. `curated:pGL4-10-luc2` pGL4.10[luc2] score=`0.5950` fields=`semantic, vector_type, organism, markers`

Rationale: The GenBank pSI record is indexed as the corpus mammalian-expression profile and carries ampR plus the SV40 enhancer/early promoter. This case exercises mammalian host, profile, and bacterial-selection filters.
Source: Live local Postgres corpus verification on 2026-05-31; GenBank U47121.2 indexed metadata

### 18. Can you pull pFR-Luc? I need an AmpR mammalian firefly-luciferase reporter backbone with an upstream cloning site.

- Acceptable IDs: `genbank:AF058756.1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:AF058756.1` Cloning vector pFR-Luc, complete sequence score=`1.0000` fields=`lexical_name, vector_type, organism, markers`
- 2. `curated:pGL4-10-luc2` pGL4.10[luc2] score=`0.7768` fields=`semantic, vector_type, organism, markers, genes`
- 3. `curated:pGL3-Basic` pGL3-Basic score=`0.7538` fields=`semantic, vector_type, organism, markers, genes`
- 4. `genbank:U47121.2` Cloning vector pSI, mammalian expression vector, complete sequence score=`0.5741` fields=`semantic, vector_type, organism, markers`
- 5. `genbank:U47120.2` Cloning vector pCI-neo, mammalian expression vector, complete sequence score=`0.5351` fields=`semantic, vector_type, organism, markers`

Rationale: The GenBank pFR-Luc record is indexed as a mammalian reporter vector with luciferase, ampicillin selection, an MCS candidate, and SV40 late polyA. This researcher-style lookup broadens reporter coverage beyond curated seeds.
Source: Live local Postgres corpus verification on 2026-05-31; GenBank AF058756.1 indexed metadata

### 19. For a yeast shuttle comparison, retrieve the Zygosaccharomyces rouxii pSB3 plasmid with an ARS region.

- Acceptable IDs: `genbank:PV135004.1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:PV135004.1` Zygosaccharomyces rouxii culture ATCC:56076 plasmid pSB3, complete sequence score=`1.0000` fields=`lexical_name, vector_type, organism`
- 2. `curated:pRS415` pRS415 score=`0.8236` fields=`semantic, vector_type, organism`
- 3. `curated:pRS416` pRS416 score=`0.8226` fields=`semantic, vector_type, organism`

Rationale: The GenBank pSB3 record exists as a Zygosaccharomyces rouxii plasmid and is indexed with the yeast-shuttle profile plus an ARS region. It is labeled as a comparison retrieval, not as a fabricated Saccharomyces engineering backbone.
Source: Live local Postgres corpus verification on 2026-05-31; GenBank PV135004.1 indexed metadata

### 20. For a bacterial resistance-plasmid comparison, retrieve the Aeromonas salmonicida pRAS1_2402_89 plasmid carrying tetracycline resistance, sul1, and dfrA16.

- Acceptable IDs: `genbank:PZ138287.1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Expected clarification: `False`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:PZ138287.1` Aeromonas salmonicida subsp. salmonicida strain 2402/89 plasmid pRAS1_2402_89, complete sequence score=`1.0000` fields=`lexical_name, organism, markers`

Rationale: The natural GenBank pRAS1_2402_89 record exists in the broader corpus with tetA, tetR, sul1, and dfrA16 annotations. It remains profile unknown and is intentionally labeled for comparative retrieval rather than as an engineered vector template.
Source: Live local Postgres corpus verification on 2026-05-31; GenBank PZ138287.1 indexed metadata

### 21. I need a viral vector with antibiotic resistance.

- Acceptable IDs: ``
- Result: `miss`
- Reciprocal rank: `0.000`
- Expected clarification: `True`
- Clarification needed: `True`
- Clarification question: Which viral vector type should this use: lentiviral, retroviral, AAV, or another system?

Retrieved:
- <none>

Rationale: The request does not identify the viral system or selectable marker. Retrieval should ask a clarifying question instead of guessing a lentiviral, retroviral, AAV, or marker label; the current corpus has no indexed lentiviral or CRISPR profile records.
Source: Human-authored ambiguity case informed by live local Postgres profile audit on 2026-05-31
