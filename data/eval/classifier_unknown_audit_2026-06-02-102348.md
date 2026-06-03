# Classifier Unknown Audit

- Generated at: `2026-06-02T10:23:48Z`
- Branch: `phase0-retrieval-robustness`
- Scope: 65 records with `vector_profile = unknown` in `data/eval/reprocess/2026-06-02-033519-reprocess-all.json`
- Sources used: latest quality report, latest reprocess report, local Postgres `plasmids` rows, and cached raw GenBank/curated blobs re-parsed with `parse_genbank_text`
- API/worker code touched: none
- Commits: none

## Summary

| Category | Count | Finding |
| --- | ---: | --- |
| a: stay unknown | 49 | Natural strain/environmental/clinical plasmids, partial/unverified natural plasmid fragments, or non-engineered episomes dominated by CDS-like `GOI`, `rep`, `mob/tra/vir`, transposase, transporter, toxin-antitoxin, and resistance genes. These should not become engineered vector templates. |
| b: existing profile rule/parser gap | 16 | Engineered records with vector-title metadata and components consistent with existing bacterial cloning, bacterial expression, general shuttle, or reporter/expression profiles, but missing one conservative rule input such as parsed ORI, MCS, marker alias, or expression-cassette evidence. |
| c: propose new profile | 0 | No defensible new engineered-vector profile is warranted from this cohort. Phagemid/antisense/conditional vectors are better handled as narrow evidence under existing profiles, not broad new categories. |

## Per-Record Findings

| ID | Name | Key metadata/components | Category | Reason |
| --- | --- | --- | --- | --- |
| `curated:pACYC184` | pACYC184 | synthetic construct; plasmid; markers indexed: chloramphenicol resistance gene, tetracycline resistance gene; parsed: marker:1, ORI:1; features: chloramphenicol resistance gene, p15A origin | b | Curated bacterial cloning vector. Existing `bacterial_cloning_vector` fit, but parser only emits one marker feature despite two indexed markers, so two-marker cloning fallback is not satisfied. |
| `genbank:AF013597.1` | Phagemid cloning vector pATCH1, complete sequence | phagemid cloning vector; bla; lac/T3 promoters; parsed: terminator:1, ORI:2, marker:1, GOI:2, promoter:2; features include f1 origin, pMB1 origin, bla, lacZ', T3 promoter | b | Existing bacterial cloning/phagemid cloning case. It has pMB1 + f1 origins and bla, but lacks parsed MCS or two marker classes; metadata is narrow enough for a cloning-vector rule if corroborated by pMB1/f1 + marker/lacZ. |
| `genbank:AF050464.1` | Expression vector pKIL-HIS3, complete sequence | expression vector; ampR; parsed: promoter:2, GOI:2, terminator:1, marker:1, ORI:1; features include ccdB, lac promoter, ampR, ORI, lacIq | b | Existing bacterial expression/vector backbone candidate. Expression title plus ORI/marker/lac promoter/ccdB-lacIq architecture is currently not enough for conservative bacterial expression evidence. |
| `genbank:AF097552.1` | Expression vector unc-68:GFP(1-8), complete sequence | expression vector; parsed: GOI:1, marker:1, ORI:1; features: ryanodine receptor, AmpR/bla, pMB1/pUC origin | b | Existing reporter/expression-like record by title/name, but cached annotations do not expose GFP as a parsed feature and provide no promoter/terminator. Keep any fix narrow to explicit `GFP` title plus vector metadata, not generic GOI. |
| `genbank:AF147464.1` | T7 expression vector pViet, complete sequence | T7 expression vector; bla; parsed: marker:1, terminator:1, GOI:2; features: bla, T7 terminator, his6, lacI | b | Existing bacterial expression vector by title and His/T7 architecture, but parser misses ORI and qualifying T7 promoter/corroboration. Needs parser evidence, not a broad title-only expression rule. |
| `genbank:AF403427.1` | Cloning vector pRL1342, complete sequence | cloning vector; cat; T7/SP6/cat promoters; parsed: terminator:2, promoter:3, MCS:1, marker:1; features include polylinker, cat, T7/SP6 promoters, rrn/trpA terminators | b | Existing bacterial cloning vector. It has MCS + marker + cloning-vector metadata, but no parsed ORI; likely missing BAC/cosmid/replicon origin evidence. |
| `genbank:AF519766.1` | Cloning vector pMAK705, complete sequence | cloning vector; cat; parsed: GOI:1, marker:1, promoter:1, MCS:1; features: rep, cat, lac promoter region, pUC19 MCS | b | Existing bacterial cloning vector. Parsed `rep` is left as GOI rather than ORI, preventing ORI+marker+MCS classification. |
| `genbank:AY219701.1` | Cloning vector pAZ1, complete sequence | cloning vector; lac promoter; parsed: terminator:2, promoter:2, GOI:2, MCS:1, ORI:1; features: rrnB terminators, lacZ-alpha, pUC19 MCS, KAN, pMB1/pUC origin | b | Existing bacterial cloning vector. The apparent kanamycin cassette is parsed as `GOI` (`KAN`) rather than marker, so ORI+marker+MCS is not met. |
| `genbank:AY236524.1` | Cloning vector pLZ42, complete sequence | cloning vector; indexed markers: Bla, Cat; lac UV5 promoter; parsed: promoter:1, marker:2 | b | Existing bacterial cloning vector. Two distinct markers are present, but no ORI/MCS is parsed; rule should not classify on markers alone, but parser may be missing backbone/MCS annotations. |
| `genbank:U09128.1` | pSacBII P1 cloning vector with sacB, kilA, repL and kanamycin resistance genes, complete sequence | P1 cloning vector; kan marker; SP6/E. coli/T7 promoters; parsed: promoter:3, GOI:3, marker:1; features: sacB, aph, repL, kilA, SP6/T7 promoters | b | Existing bacterial cloning vector. `repL` remains GOI and no P1/replicon ORI or MCS is detected, despite explicit P1 cloning-vector metadata. |
| `genbank:U26464.1` | Cloning vector pZC320, complete sequence | cloning vector; bla, aadA'; parsed: GOI:4, terminator:2, marker:2, promoter:1, MCS:1; features: repE, sopA/sopB, bla, aadA', lacZa, MCS | b | Existing bacterial cloning vector. Marker+MCS+cloning metadata are strong, but F/plasmid maintenance genes (`repE`, `sopA`, `sopB`) are not treated as ORI/replicon evidence. |
| `genbank:U36452.1` | Expression vector pCALc, complete sequence | expression vector; beta-lactamase; parsed: terminator:1, GOI:1, ORI:1, marker:1; features: T7 terminator, lacI, pMB1/pUC origin, beta-lactamase | b | Existing bacterial expression-family vector by pCAL title, but no promoter or MCS/payload is parsed. Do not classify broadly without adding exact pCAL cassette evidence. |
| `genbank:U36453.1` | Expression vector pCALkc, complete sequence | expression vector; beta-lactamase; parsed: terminator:1, GOI:1, ORI:1, marker:1; features: T7 terminator, lacI, pMB1/pUC origin, beta-lactamase | b | Same pCAL pattern as U36452. Existing bacterial expression-family vector, currently blocked by missing promoter/MCS/payload evidence. |
| `genbank:U39574.1` | Expression cloning vector pBVI02, including bioB and bla genes, complete sequence | expression cloning vector; bla; lac promoter; parsed: marker:1, ORI:1, promoter:1, GOI:1; features: bla, pMB1/pUC origin, lac promoter, bioB | b | Existing bacterial expression vector candidate. ORI+marker+lac promoter+GOI are present, but lac is not a qualifying strong promoter in current bacterial-expression evidence. A narrow `expression cloning vector` + lac promoter + oriented GOI rule may be warranted. |
| `genbank:U47670.1` | Cloning vector pJDC406, antisense expression vector for Escherichia coli, complete sequence | cloning/antisense expression vector; beta-lactamase; parsed: ORI:1, marker:1; features: pMB1/pUC origin, beta-lactamase | b | Existing bacterial cloning/expression vector metadata, but only ORI+marker are detected. Needs additional antisense/promoter/MCS evidence before classification; do not add title-only admission. |
| `genbank:U65078.1` | Cloning shuttle vector pNF2214 with kanamycin resistance gene, complete sequence | cloning shuttle vector; kanamycin in title; parsed: MCS:1, GOI:1; features: multiple cloning site, aminoglycoside phosphotransferase | b | Existing general shuttle/cloning vector. Marker alias and ORI/host evidence are missing; `aminoglycoside phosphotransferase` should be marker when title says kanamycin resistance. |
| `genbank:CP121282.1` | Halobacterium sp. CBA1161 plasmid pCBA1161-02, complete sequence | natural archaeal plasmid; parsed: GOI:20; features mostly hypothetical proteins, HNH endonuclease, recombinase/integrase, IS element | a | Natural organism plasmid with no engineered-vector title or selectable cloning architecture. Stay unknown. |
| `genbank:CP190835.1` | Staphylococcus hominis strain LaCa_103 plasmid pLaCa_103a, complete sequence | natural strain plasmid; parsed: GOI:20; features include repA, MobA/MobL, MobC, MFS transporter, msr(A), Mph(C), metal transport | a | Natural clinical/strain plasmid dominated by replication, mobilization, resistance, and transporter CDS. Stay unknown. |
| `genbank:CP190836.1` | Staphylococcus hominis strain LaCa_103 plasmid pLaCa_103b, complete sequence | natural strain plasmid; parsed: GOI:1; feature: protein rep | a | Minimal natural replicon annotation only; no engineered vector components. Stay unknown. |
| `genbank:CP190842.1` | Staphylococcus haemolyticus strain LaCa_147 plasmid pLaCa_147a, complete sequence | natural strain plasmid; parsed: GOI:11; features include repA, tdc, tyrP, nhaC, cadA/cadC, IS257 | a | Natural plasmid with metabolic/metal-resistance/transposase genes, not a vector template. Stay unknown. |
| `genbank:CP190845.1` | Corynebacterium accolens strain LaCa_114 plasmid pLaCa_114a, complete sequence | natural strain plasmid; parsed: GOI:4; hypothetical proteins | a | Sparse natural plasmid annotations without vector evidence. Stay unknown. |
| `genbank:CP190847.1` | Corynebacterium accolens strain LaCa_113 plasmid pLaCa_113a, complete sequence | natural strain plasmid; parsed: GOI:4; hypothetical proteins | a | Sparse natural plasmid annotations without vector evidence. Stay unknown. |
| `genbank:CP190849.1` | Staphylococcus epidermidis strain LaCa_111 plasmid pLaCa_111a, complete sequence | natural strain plasmid; parsed: GOI:19; features include repA, transposase, hxlA/hxlB, msr(A), Mph(C), cadA/cadC | a | Natural Staphylococcus plasmid with mobile/resistance/metabolic CDS; no synthetic cloning architecture. Stay unknown. |
| `genbank:CP190850.1` | Staphylococcus epidermidis strain LaCa_111 plasmid pLaCa_111b, complete sequence | natural strain plasmid; parsed: GOI:17, marker:1; marker-like TetR/AcrR regulator; features include rep proteins, transporters, MFS, toxin-antitoxin | a | Natural plasmid; single resistance-regulator-like feature is not cloning-vector selectable-marker evidence. Stay unknown. |
| `genbank:CP190851.1` | Staphylococcus epidermidis strain LaCa_111 plasmid pLaCa_111c, complete sequence | natural strain plasmid; parsed: GOI:1; RepB family replication initiator | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP190852.1` | Staphylococcus epidermidis strain LaCa_111 plasmid pLaCa_111d, complete sequence | natural strain plasmid; parsed: GOI:1; replication initiation factor | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP190854.1` | Staphylococcus epidermidis strain LaCa_110 plasmid pLaCa_110a, complete sequence | natural strain plasmid; parsed: GOI:52, marker:1; features include repA, tnpA, VirD4/VirB4, CHAP, sortase, lysostaphin resistance, mobP2 | a | Large natural mobile plasmid with conjugation/mobilization and resistance-like genes. Not an engineered shuttle vector. Stay unknown. |
| `genbank:CP190855.1` | Staphylococcus epidermidis strain LaCa_110 plasmid pLaCa_110b, complete sequence | natural strain plasmid; parsed: GOI:1; RepB family replication initiator | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP190857.1` | Staphylococcus epidermidis strain LaCa_109 plasmid pLaCa_109a, complete sequence | natural strain plasmid; parsed: GOI:26, marker:1; features include cadD, metal transport, msr(A), Mph(C), qac/qacR, IS6 | a | Natural resistance/mobile plasmid; marker-like genes are environmental/clinical payloads, not vector selection cassettes. Stay unknown. |
| `genbank:CP190859.1` | Corynebacterium accolens strain LaCa_108 plasmid pLaCa_108a, complete sequence | natural strain plasmid; parsed: GOI:4; hypothetical proteins | a | Sparse natural plasmid annotations without engineered-vector evidence. Stay unknown. |
| `genbank:CP190864.1` | Corynebacterium sp. LaCa_102 plasmid pLaCa_102a, complete sequence | natural strain plasmid; parsed: GOI:15; features include replication initiation protein, AAA ATPase, recombinase, ABC-domain proteins | a | Natural Corynebacterium plasmid with housekeeping/mobile CDS. Stay unknown. |
| `genbank:CP190865.1` | Corynebacterium sp. LaCa_102 plasmid pLaCa_102b, complete sequence | natural strain plasmid; parsed: GOI:15; features include AAA ATPase, RepA, transposase, hypothetical proteins | a | Natural plasmid with replicon/mobile elements only. Stay unknown. |
| `genbank:CP190867.1` | Corynebacterium sp. LaCa_100 plasmid pLaCa_100a, complete sequence | natural strain plasmid; parsed: GOI:16; features include replication initiation protein, MarR regulator, AAA ATPase | a | Natural Corynebacterium plasmid; no vector components. Stay unknown. |
| `genbank:CP190868.1` | Corynebacterium sp. LaCa_100 plasmid pLaCa_100b, complete sequence | natural strain plasmid; parsed: GOI:15; features include AAA ATPase, RepA, transposase | a | Natural plasmid with replicon/mobile elements only. Stay unknown. |
| `genbank:CP190870.1` | Corynebacterium accolens strain LaCa_98 plasmid pLaCa_98a, complete sequence | natural strain plasmid; parsed: GOI:4; hypothetical proteins | a | Sparse natural plasmid annotations without engineered-vector evidence. Stay unknown. |
| `genbank:CP190872.1` | Staphylococcus capitis strain LaCa_96 plasmid pLaCa_96a, complete sequence | natural strain plasmid; parsed: GOI:33; features include repA, toxin-antitoxin, hxlA, lqo, transport/regulatory genes | a | Natural Staphylococcus plasmid with CDS/mobile modules, not vector architecture. Stay unknown. |
| `genbank:CP190873.1` | Staphylococcus capitis strain LaCa_96 plasmid pLaCa_96b, complete sequence | natural strain plasmid; parsed: GOI:1; RepB family replication initiator | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP190874.1` | Staphylococcus capitis strain LaCa_96 plasmid pLaCa_96c, complete sequence | natural strain plasmid; parsed: GOI:1; replication initiation factor | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP190875.1` | Staphylococcus capitis strain LaCa_96 plasmid pLaCa_96d, complete sequence | natural strain plasmid; parsed: GOI:1; replication initiation factor | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP190876.1` | Staphylococcus capitis strain LaCa_96 plasmid pLaCa_96e, complete sequence | natural strain plasmid; parsed: GOI:2; protein rep, hypothetical protein | a | Natural replicon annotation only. Stay unknown. |
| `genbank:CP190878.1` | Staphylococcus capitis strain LaCa_95 plasmid pLaCa_95a, complete sequence | natural strain plasmid; parsed: GOI:33; features mirror LaCa_96a-like CDS/mobile modules | a | Natural Staphylococcus plasmid with no engineered vector evidence. Stay unknown. |
| `genbank:CP190879.1` | Staphylococcus capitis strain LaCa_95 plasmid pLaCa_95b, complete sequence | natural strain plasmid; parsed: GOI:1; RepB family replication initiator | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP191035.1` | Corynebacterium sp. LaCa_204 plasmid pLaCa_204a, complete sequence | natural strain plasmid; parsed: GOI:13; features include replication initiation protein, recombinase, IS1249 transposase | a | Natural Corynebacterium mobile plasmid; no vector architecture. Stay unknown. |
| `genbank:CP191036.1` | Corynebacterium sp. LaCa_204 plasmid pLaCa_204b, complete sequence | natural strain plasmid; parsed: GOI:14; AAA ATPase, RepA, transposase, hypothetical proteins | a | Natural plasmid with replicon/mobile CDS. Stay unknown. |
| `genbank:CP191037.1` | Corynebacterium sp. LaCa_204 plasmid pLaCa_204c, complete sequence | natural strain plasmid; parsed: GOI:5; protein rep and hypothetical proteins | a | Natural replicon annotation only. Stay unknown. |
| `genbank:CP191042.1` | Staphylococcus epidermidis strain LaCa_201 plasmid pLaCa_201a, complete sequence | natural strain plasmid; parsed: GOI:1, marker:1; RepB and cadmium resistance transporter | a | Natural resistance plasmid; cadmium resistance is payload/noise, not engineered selectable marker evidence. Stay unknown. |
| `genbank:CP191051.1` | Staphylococcus epidermidis strain LaCa_194 plasmid pLaCa_194b, complete sequence | natural strain plasmid; parsed: GOI:1; RepB family replication initiator | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP191052.1` | Staphylococcus epidermidis strain LaCa_194 plasmid pLaCa_194c, complete sequence | natural strain plasmid; parsed: GOI:1; replication initiation factor | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP191053.1` | Staphylococcus epidermidis strain LaCa_194 plasmid pLaCa_194d, complete sequence | natural strain plasmid; parsed: GOI:1; replication initiation factor | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP191054.1` | Staphylococcus epidermidis strain LaCa_194 plasmid pLaCa_194e, complete sequence | natural strain plasmid; parsed: GOI:1; protein rep | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP191060.1` | Staphylococcus aureus strain LaCa_187 plasmid pLaCa_187a, complete sequence | natural strain plasmid; parsed: GOI:20, marker:4; markers: blaZ, blaR1, blaI, cadD; features include rep, recombinase, mobV, bacteriocin | a | Natural S. aureus resistance/mobile plasmid. Multiple resistance genes are clinical payloads, not sufficient engineered-vector evidence. Stay unknown. |
| `genbank:CP191063.1` | Staphylococcus aureus strain LaCa_185 plasmid pLaCa_185a, complete sequence | natural strain plasmid; parsed: GOI:20, marker:4; markers: cadD, blaI, blaR1, blaZ; features include repA, recombinase, bacteriocin, mobV | a | Natural S. aureus resistance/mobile plasmid. Stay unknown. |
| `genbank:CP191068.1` | Staphylococcus epidermidis strain LaCa_160 plasmid pLaCa_160a, complete sequence | natural strain plasmid; parsed: GOI:49; features include repA, tnpA, VirD4/VirB4, CHAP, LPXTG, mobP2 | a | Large natural mobile plasmid with conjugation/mobilization modules; not a shuttle vector. Stay unknown. |
| `genbank:CP191069.1` | Staphylococcus epidermidis strain LaCa_160 plasmid pLaCa_160b, complete sequence | natural strain plasmid; parsed: GOI:32; features include repA, IS/transposases, ABC transporters, RepB | a | Natural mobile/transport plasmid; no vector metadata. Stay unknown. |
| `genbank:CP191070.1` | Staphylococcus epidermidis strain LaCa_160 plasmid pLaCa_160c, complete sequence | natural strain plasmid; parsed: GOI:1; RepB family replication initiator | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP191071.1` | Staphylococcus epidermidis strain LaCa_160 plasmid pLaCa_160d, complete sequence | natural strain plasmid; parsed: GOI:1, marker:1; ArdC-like ssDNA-binding protein, lysostaphin resistance | a | Natural plasmid with resistance-like payload, not engineered selection architecture. Stay unknown. |
| `genbank:CP191072.1` | Staphylococcus epidermidis strain LaCa_160 plasmid pLaCa_160e, complete sequence | natural strain plasmid; parsed: GOI:1; replication initiation factor | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP191074.1` | Staphylococcus epidermidis strain LaCa_159 plasmid pLaCa_159a, complete sequence | natural strain plasmid; parsed: GOI:20; features include repA, replication protein, toxin-antitoxin, recombinase, metal transporter | a | Natural Staphylococcus plasmid with mobile/metabolic CDS. Stay unknown. |
| `genbank:CP191075.1` | Staphylococcus epidermidis strain LaCa_159 plasmid pLaCa_159b, complete sequence | natural strain plasmid; parsed: GOI:1; RepB family replication initiator | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP191076.1` | Staphylococcus epidermidis strain LaCa_159 plasmid pLaCa_159c, complete sequence | natural strain plasmid; parsed: GOI:1; replication initiation factor | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP191078.1` | Staphylococcus epidermidis strain LaCa_158 plasmid pLaCa_158a, complete sequence | natural strain plasmid; parsed: GOI:1; RepB family replication initiator | a | Minimal natural replicon annotation only. Stay unknown. |
| `genbank:CP196381.1` | Herbiconiux sp. J20-18 plasmid unnamed1, complete sequence | environmental/natural plasmid; parsed: GOI:1; hypothetical protein spanning record | a | Natural unnamed plasmid with no engineered vector metadata or components. Stay unknown. |
| `genbank:PX275371.1` | Zygosaccharomyces bailii plasmid pZB1, complete sequence | natural yeast plasmid; parsed: GOI:1; FLP | a | Natural yeast plasmid/episome, not a yeast shuttle vector. No selectable marker or cloning cassette. Stay unknown. |
| `genbank:PZ138287.1` | Aeromonas salmonicida subsp. salmonicida strain 2402/89 plasmid pRAS1_2402_89, complete sequence | natural resistance plasmid; parsed: GOI:42, marker:4; markers: tetA, tetR, sul1, dfrA16; features include mobC, virD2, tra/virB transfer genes, integron genes | a | Natural resistance/mobilizable plasmid already used as comparative retrieval material, not an engineered vector template. Stay unknown. |
| `genbank:PZ407647.1` | UNVERIFIED: Staphylococcus aureus plasmid AAC/APH aminoglycoside resistance locus, partial/complete sequence | unverified natural plasmid fragment; parsed: marker:1; feature: aphD | a | Partial/unverified natural resistance-gene record, not a complete engineered plasmid vector. Stay unknown. |

## Rule-Gap Patterns For CLASSIFY-2

These are deliberately narrow. Avoid title-only classification rules and avoid using natural-plasmid resistance genes as engineered vector evidence.

1. **Marker alias/parser gaps in engineered vector metadata**

Records: `curated:pACYC184`, `genbank:AY219701.1`, `genbank:U65078.1`.

Suggested testable fixes:
- Treat explicit vector-record kanamycin cassette names such as `KAN` and `aminoglycoside phosphotransferase` as marker evidence when supported by title/use-case terms like `kanamycin resistance gene`, `cloning vector`, or `shuttle vector`.
- Preserve pACYC184's tetracycline marker evidence from curated/indexed metadata or parse the second resistance cassette rather than collapsing to one large chloramphenicol marker.
- Regression tests should assert these marker additions do not promote natural strain plasmids that merely contain resistance genes.

1. **Replicon/ORI parser gaps for known engineered cloning backbones**

Records: `genbank:AF403427.1`, `genbank:AF519766.1`, `genbank:U09128.1`, `genbank:U26464.1`, `genbank:AY236524.1`.

Suggested testable fixes:
- Map engineered-record `rep`, `repE`, `repL`, or explicit P1/F/plasmid maintenance regions to ORI/replicon support only when the record also has trusted vector metadata and cloning evidence such as MCS/polylinker or two distinct markers.
- Do not map generic natural-plasmid `rep`, `RepA`, or `RepB` to engineered ORI support outside vector-title records.

1. **Narrow cloning-vector admission when MCS and marker are present but ORI is not parsed**

Records: `genbank:AF403427.1`, `genbank:AF519766.1`, `genbank:U26464.1`.

Suggested testable fixes:
- Consider `cloning vector` metadata plus parsed MCS/polylinker plus marker plus any trusted backbone/replicon term as `bacterial_cloning_vector`.
- Do not classify natural plasmids with marker+rep only, or promoter-only sequencing vectors without MCS/backbone evidence.

1. **Bacterial expression evidence for lac/T7-family vectors remains too sparse for some legacy records**

Records: `genbank:AF050464.1`, `genbank:AF147464.1`, `genbank:U36452.1`, `genbank:U36453.1`, `genbank:U39574.1`.

Suggested testable fixes:
- Add exact, source-backed expression-cassette evidence for pCAL/pKIL/pViet/pBVI-style records only when a vector title is paired with ORI+marker and a payload/tag/promoter/terminator cassette.
- For `U39574.1`, a narrow rule could admit `expression cloning vector` + ORI + marker + lac promoter + oriented GOI.
- Do not relax bacterial expression to any `lac promoter + GOI`; many cloning vectors and natural lac fragments would become false positives.

1. **Phagemid cloning vectors fit existing cloning profile**

Record: `genbank:AF013597.1`.

Suggested testable fixes:
- Treat exact `phagemid cloning vector` metadata plus pMB1/ColE1 ORI + f1 origin + selectable marker + lacZ/polylinker evidence as bacterial cloning-vector evidence.
- Keep f1 alone excluded from shuttle classification, consistent with the existing host-aware shuttle fix.

1. **Natural plasmid guardrails should remain explicit**

Records: the 49 category-a records.

Suggested regression guards:
- Natural titles containing `strain ... plasmid ... complete sequence`, `UNVERIFIED`, `unnamed`, or public isolate organism names should remain `unknown` unless they also have trusted engineered-vector metadata.
- Resistance genes (`blaZ`, `cadD`, `tetA`, `tetR`, `sul1`, `dfrA16`, `aphD`, `msr(A)`, `Mph(C)`, `qac`) and transfer genes (`mob`, `tra`, `virB`, `virD`) should not independently trigger engineered vector profiles.
- Natural yeast plasmids such as `Zygosaccharomyces bailii plasmid pZB1` should not be classified as `yeast_shuttle_vector` without engineered marker plus ARS/CEN/2-micron/shuttle metadata.

## New Profile Review

No category-c profile is recommended for implementation from this audit.

Human-review note: a non-template corpus label such as `natural_mobile_resistance_plasmid` could be useful for retrieval filtering or corpus hygiene, but it should not be treated as an engineered vector profile. The biological rationale is that many category-a records are naturally occurring plasmids carrying replication, mobilization/conjugation, transposase, integron, metal-resistance, or antibiotic-resistance loci. Those loci are biologically meaningful for comparative retrieval, but they do not provide the designed promoter/MCS/selection/backbone architecture expected of vector templates.
