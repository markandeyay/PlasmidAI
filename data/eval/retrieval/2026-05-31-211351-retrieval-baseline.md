# Retrieval Evaluation Report

- Generated at: `2026-05-31T21:13:51.189686+00:00`
- Gold file: `data/eval/retrieval_gold.jsonl`
- Queries: `12`
- Top K: `5`
- Top-1 hit rate: `0.750`
- Top-5 hit rate: `1.000`
- MRR: `0.850`

## Per-Query Results

### 1. I need a simple high-copy cloning vector for routine plasmid cloning in E. coli.

- Acceptable IDs: `pUC19, pUC18, pBluescript-II-SK-plus, pBluescript-II-SK-minus, pBR322, pACYC184`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pUC19` pUC19c score=`0.7683` fields=`semantic, vector_type, organism, application`
- 2. `curated:pUC18` pUC18 score=`0.7536` fields=`semantic, vector_type, organism, application`
- 3. `genbank:AY428809.1` Cloning vector pSUP202, complete sequence score=`0.7271` fields=`semantic, vector_type, organism, application`
- 4. `genbank:U47626.2` Cloning vector PinPoint<TM> Xa-1, complete sequence score=`0.7120` fields=`semantic, vector_type, organism, application`
- 5. `curated:pBR322` pBR322 score=`0.7076` fields=`semantic, vector_type, organism, application`

Rationale: These are curated bacterial cloning backbones with standard cloning-friendly features such as pUC/pMB1 origins, MCSs, and antibiotic selection.
Source: Curated seed manifest entries in packages/data_pipeline/ingest/curated_seed_manifest.yaml

### 2. Which curated plasmid would you use for GST-tagged bacterial protein expression in E. coli?

- Acceptable IDs: `pGEX-4T-1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pGEX-4T-1` pGEX-4T-1 score=`0.6758` fields=`semantic, organism, genes, tags`
- 2. `curated:pUC18` pUC18 score=`0.6512` fields=`semantic, organism, genes`
- 3. `genbank:AF147463.1` T7 Expression vector pNam, complete sequence score=`0.6429` fields=`semantic, organism`
- 4. `genbank:U47626.2` Cloning vector PinPoint<TM> Xa-1, complete sequence score=`0.6323` fields=`semantic, organism`
- 5. `curated:pBR322` pBR322 score=`0.6303` fields=`semantic, organism, genes`

Rationale: pGEX-4T-1 is explicitly annotated as a GST fusion bacterial expression backbone with tac/lac regulation.
Source: Curated seed manifest entry for pGEX-4T-1

### 3. I need a mammalian reporter plasmid for GFP-based expression analysis in cultured cells.

- Acceptable IDs: `pEGFP-N1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
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
- Clarification needed: `False`

Retrieved:
- 1. `curated:pRS415` pRS415 score=`0.8341` fields=`semantic, vector_type, organism`
- 2. `curated:pRS416` pRS416 score=`0.8327` fields=`semantic, vector_type, organism`
- 3. `genbank:PV135004.1` Zygosaccharomyces rouxii culture ATCC:56076 plasmid pSB3, complete sequence score=`0.6006` fields=`semantic, vector_type, organism`

Rationale: These curated vectors are yeast centromere shuttle plasmids with LEU2 or URA3 selection and CEN/ARS maintenance features.
Source: Curated seed manifest entries for pRS415 and pRS416

### 6. Recommend a low-copy bacterial cloning plasmid with chloramphenicol resistance.

- Acceptable IDs: `pACYC184`
- Result: `hit at rank 2`
- Reciprocal rank: `0.500`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:AY428809.1` Cloning vector pSUP202, complete sequence score=`0.7693` fields=`semantic, vector_type, organism, markers, application`
- 2. `curated:pACYC184` pACYC184 score=`0.7328` fields=`semantic, vector_type, organism, markers, application`
- 3. `genbank:AF519766.1` Cloning vector pMAK705, complete sequence score=`0.7249` fields=`semantic, vector_type, organism, markers, application`

Rationale: pACYC184 is curated as a low-copy p15A-origin cloning vector with chloramphenicol and tetracycline resistance.
Source: Curated seed manifest entry for pACYC184

### 7. I want a bacterial cloning plasmid with lacZ alpha selection and a standard pUC backbone.

- Acceptable IDs: `pUC19, pUC18, pBluescript-II-SK-plus, pBluescript-II-SK-minus`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pUC19` pUC19c score=`0.7722` fields=`semantic, vector_type, organism, application`
- 2. `genbank:AY428809.1` Cloning vector pSUP202, complete sequence score=`0.7580` fields=`semantic, vector_type, organism, application`
- 3. `curated:pUC18` pUC18 score=`0.7548` fields=`semantic, vector_type, organism, application`
- 4. `genbank:U47670.1` Cloning vector pJDC406, antisense expression vector for Escherichia coli, complete sequence score=`0.7482` fields=`semantic, vector_type, organism, application`
- 5. `curated:pBR322` pBR322 score=`0.7319` fields=`semantic, vector_type, organism, application`

Rationale: These curated records include pUC-family or lacZ alpha/MCS cloning backbones suitable for blue-white screening workflows.
Source: Curated seed manifest entries for the pUC and pBluescript vectors

### 8. Which curated cloning vector carries both ampicillin and tetracycline resistance with a pMB1-derived replication region?

- Acceptable IDs: `pBR322`
- Result: `hit at rank 2`
- Reciprocal rank: `0.500`
- Clarification needed: `False`

Retrieved:
- 1. `genbank:AY428809.1` Cloning vector pSUP202, complete sequence score=`0.8049` fields=`semantic, vector_type, organism, markers, application`
- 2. `curated:pBR322` pBR322 score=`0.7909` fields=`semantic, vector_type, organism, markers, application`

Rationale: pBR322 is curated as a classic cloning vector with pMB1-derived replication, rop, bla/AmpR, and tetracycline resistance.
Source: Curated seed manifest entry for pBR322

### 9. I need a phagemid cloning vector with an f1 origin, lacZ alpha MCS, and T7/T3 promoter sites.

- Acceptable IDs: `pBluescript-II-SK-plus, pBluescript-II-SK-minus`
- Result: `hit at rank 5`
- Reciprocal rank: `0.200`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pUC18` pUC18 score=`0.7781` fields=`semantic, vector_type, organism, application`
- 2. `curated:pUC19` pUC19c score=`0.7778` fields=`semantic, vector_type, organism, application`
- 3. `genbank:U47626.2` Cloning vector PinPoint<TM> Xa-1, complete sequence score=`0.7647` fields=`semantic, vector_type, organism, promoters, application`
- 4. `curated:pBR322` pBR322 score=`0.7463` fields=`semantic, vector_type, organism, application`
- 5. `curated:pBluescript-II-SK-minus` pBluescript II SK(-) score=`0.7436` fields=`semantic, vector_type, organism, application`

Rationale: The pBluescript II SK records are curated phagemid cloning vectors; SK(+) explicitly includes f1 plus orientation, lacZ alpha/MCS, T7/T3 promoters, pUC origin, and bla, while SK(-) is the corresponding minus-orientation variant.
Source: Curated seed manifest entries for pBluescript-II-SK-plus and pBluescript-II-SK-minus

### 10. Recommend a high-copy ampicillin-resistant pUC plasmid when either MCS orientation is acceptable.

- Acceptable IDs: `pUC19, pUC18`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pUC19` pUC19c score=`0.8040` fields=`semantic, vector_type, organism, markers, application`
- 2. `genbank:AY428809.1` Cloning vector pSUP202, complete sequence score=`0.7770` fields=`semantic, vector_type, organism, markers, application`
- 3. `curated:pUC18` pUC18 score=`0.7727` fields=`semantic, vector_type, organism, markers, application`
- 4. `curated:pBR322` pBR322 score=`0.7549` fields=`semantic, vector_type, organism, markers, application`
- 5. `genbank:U47670.1` Cloning vector pJDC406, antisense expression vector for Escherichia coli, complete sequence score=`0.7325` fields=`semantic, vector_type, organism, markers, application`

Rationale: pUC19 is curated as a high-copy pUC/pMB1-derived AmpR cloning vector with lacZ alpha/MCS, and pUC18 is curated as its sibling with reversed MCS orientation.
Source: Curated seed manifest entries for pUC19 and pUC18

### 11. Which mammalian EGFP fusion vector also provides G418 selection in cells and kanamycin selection in bacteria?

- Acceptable IDs: `pEGFP-N1`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pEGFP-N1` pEGFP-N1 score=`0.6354` fields=`semantic, organism, markers, genes`

Rationale: pEGFP-N1 is curated as a CMV-driven C-terminal EGFP fusion vector with neomycin/G418 mammalian selection and a kanamycin bacterial marker.
Source: Curated seed manifest entry for pEGFP-N1

### 12. I need a yeast centromere shuttle plasmid specifically selected by URA3 rather than LEU2.

- Acceptable IDs: `pRS416`
- Result: `hit at rank 1`
- Reciprocal rank: `1.000`
- Clarification needed: `False`

Retrieved:
- 1. `curated:pRS416` pRS416 score=`0.8670` fields=`semantic, vector_type, organism, markers`

Rationale: pRS416 is curated as a yeast centromere vector with a URA3 marker, whereas pRS415 carries LEU2.
Source: Curated seed manifest entries for pRS416 and pRS415
