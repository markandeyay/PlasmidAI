# Known-Good Validation Candidates

Generated for `validation-deepening` audit. Current gold set remains unchanged at 31 known-good and 52 known-bad records. This file is an audit artifact only; it does not promote records into `curated_known_good.jsonl`.

## Curated-Quality Policy Applied

Candidate bar used here:

- Public or curated source provenance must be explicit: GenBank accession, curated seed manifest entry, or prior local corpus verification.
- Biology must match an engineered vector profile, not merely a natural plasmid with resistance, replication, or mobility genes.
- Component rationale must include enough designed architecture for the claimed use: origin/replicon, selectable marker, MCS/polylinker or expression/reporter cassette, and host/use metadata where relevant.
- Expected validation outcome should be `PASS` or only justified `WARN`; parser/classifier gaps alone are not biology defects, but any record needing sequence rehydration is not directly inserted here.
- Natural isolate, unnamed RefSeq, partial, unverified, AMR/mobile, and sparse records are rejected unless explicit engineered-vector metadata overrides the natural context.

## Clean Candidates

These records have source-backed engineered-vector metadata and enough component rationale to be defensible known-good candidates after raw-record rehydration and validation dry-run.

| Candidate | Profile coverage | Source provenance / citation | Biology rationale | Notes before insertion |
| --- | --- | --- | --- | --- |
| `genbank:AF013597.1` pATCH1 | bacterial cloning / phagemid | GenBank accession/title in `classifier_unknown_audit_2026-06-02-102348.md`: "Phagemid cloning vector pATCH1, complete sequence". | Explicit phagemid cloning vector with f1 origin, pMB1 origin, bla marker, lacZ' and T3/lac promoter evidence. Designed cloning/phagemid architecture, not natural plasmid biology. | Add only if raw parsed record validates with no blocking restriction/repeat/regulatory defects. |
| `genbank:AF403427.1` pRL1342 | bacterial cloning | GenBank accession/title in `classifier_unknown_audit_2026-06-02-102348.md`: "Cloning vector pRL1342, complete sequence". | Explicit cloning-vector title with polylinker/MCS, chloramphenicol marker, T7/SP6/cat promoters, and rrn/trpA terminators. Missing ORI parsing appears to be a parser evidence gap, not a biological defect. | Requires raw record check for the underlying replicon/origin annotation before JSONL insertion. |
| `genbank:AF519766.1` pMAK705 | bacterial cloning | GenBank accession/title in `classifier_unknown_audit_2026-06-02-102348.md` and retrieval diagnostics: "Cloning vector pMAK705, complete sequence". | Explicit cloning vector with cat marker, lac promoter region, pUC19 MCS, and rep feature. The rep feature should be reviewed as engineered replicon support in this vector context. | Validate sequence and origin interpretation; do not generalize `rep` to natural plasmids. |
| `genbank:AY219701.1` pAZ1 | bacterial cloning | GenBank accession/title in `classifier_unknown_audit_2026-06-02-102348.md`: "Cloning vector pAZ1, complete sequence". | Explicit cloning vector with pMB1/pUC origin, pUC19 MCS, lacZ-alpha, rrnB terminators, lac promoter, and apparent kanamycin cassette (`KAN`). | Marker alias should be resolved from source metadata before insertion. |
| `genbank:U26464.1` pZC320 | bacterial cloning | GenBank accession/title in `classifier_unknown_audit_2026-06-02-102348.md` and retrieval baselines: "Cloning vector pZC320, complete sequence". | Explicit cloning vector with two markers (bla and aadA'), MCS, lacZ-alpha, and F/plasmid maintenance features (`repE`, `sopA`, `sopB`). Strong designed-vector architecture. | Review F/replicon support from raw feature table; do not admit marker-only records. |
| `genbank:AF050464.1` pKIL-HIS3 | bacterial expression | GenBank accession/title in `classifier_unknown_audit_phase2_real_2026-06-05-001224.md`: "Expression vector pKIL-HIS3, complete sequence". | Explicit expression-vector title with ampR marker, ORI, lac promoter region, lacIq regulator, and ccdB/lacIq architecture. Fits designed bacterial expression/control vector context. | Good candidate if validation accepts the cassette as source-vector architecture rather than de novo GOI optimization. |
| `genbank:U07168.1` pUCP26 | broad-host-range shuttle | Retrieval baseline source: live local Postgres verification on 2026-05-31 and GenBank U07168.1 indexed metadata. | Explicit Escherichia-Pseudomonas shuttle vector with tetracycline efflux marker, lacZ alpha, MCS, and broad-host shuttle use. Provides non-pUC bacterial/shuttle coverage. | Confirm host/vector profile mapping before insertion because broad-host origins are policy-sensitive. |
| `genbank:AF216802.1` pDL278 | shuttle vector | Retrieval baseline source: GenBank AF216802.1 indexed metadata for "Shuttle vector pDL278, complete sequence". | Explicit shuttle vector with spectinomycin adenyltransferase marker; useful for non-AmpR shuttle-marker coverage. | Needs raw component review for shuttle-host origin evidence before insertion. |
| `genbank:U47121.2` pSI | mammalian expression | Retrieval baseline source: live local Postgres verification on 2026-05-31 and GenBank U47121.2 indexed metadata. | Explicit mammalian expression vector with ampR and SV40 enhancer/early promoter. Complements existing mammalian pCI-like coverage. | Validate under mammalian context, not bacterial expression default. |
| `genbank:AF058756.1` pFR-Luc | mammalian reporter | Retrieval baseline source: live local Postgres verification on 2026-05-31 and GenBank AF058756.1 indexed metadata. | Mammalian firefly-luciferase reporter backbone with ampicillin selection, upstream cloning-site evidence, luciferase reporter payload, and SV40 late polyA. Strong reporter-vector rationale. | Check whether current parser annotates luciferase as GOI/reporter and polyA as terminator. |
| `genbank:AF041805.1` yGALset983 | yeast shuttle / expression | Retrieval baseline source: GenBank AF041805.1 indexed metadata and GOLD-1 review on 2026-06-02. | S. cerevisiae shuttle/expression vector with yeast maintenance region, LEU2 selection, and bacterial AmpR maintenance. | Confirm yeast maintenance feature classification before validation insertion. |
| `genbank:AF041806.1` yGALset984 | yeast shuttle / expression | Retrieval baseline source: GenBank AF041806.1 indexed metadata and GOLD-1 review on 2026-06-02. | Same yGALset family rationale: yeast shuttle/expression architecture with yeast maintenance, LEU2 selection, and bacterial AmpR maintenance. | Consider adding at most one or two yGALset siblings if avoiding near-duplicate family inflation. |
| `genbank:AF041807.1` yGALset985 | yeast shuttle / expression | Retrieval baseline source: GenBank AF041807.1 indexed metadata and GOLD-1 review on 2026-06-02. | Same yGALset family rationale; useful if the goal is yeast shuttle/expression profile coverage rather than unique family count. | Same near-duplicate consideration as AF041806.1. |

Clean candidate count: 13 records.

## Rejected Or Insufficient Candidates

These were reviewed but should not be promoted under the existing bar without more evidence or human decision.

| Record | Disposition | Reason |
| --- | --- | --- |
| `genbank:AF097552.1` unc-68:GFP(1-8) | Insufficient for known-good now | Prior audit flags explicit expression-vector/GFP title, but parser lacks GFP/reporter feature and lacks promoter/terminator annotations. Needs human review or stronger source feature evidence before reporter promotion. |
| `genbank:AF147464.1` pViet | Insufficient for known-good now | Explicit T7 expression-vector title with bla, T7 terminator, his6, and lacI, but ORI and T7 promoter are not parsed. Needs raw source feature review before it clears the bar. |
| `genbank:AY236524.1` pLZ42 | Insufficient for known-good now | Explicit cloning-vector title and two markers, but no ORI/MCS/backbone signal parsed. Marker-only engineered-vector admission would weaken the bar. |
| `genbank:U09128.1` pSacBII P1 cloning vector | Insufficient for known-good now | Explicit P1 cloning-vector title with sacB/kilA/repL/kanamycin and promoters, but no P1/replicon ORI or MCS detected. Needs P1 biology review and parser support. |
| `genbank:U36452.1` pCALc | Insufficient for known-good now | pCAL-family expression-vector title plus ORI/marker/T7 terminator/lacI, but no promoter or MCS/payload parsed. Existing curated set already covers related pCALn records; do not add sparse siblings without source feature confirmation. |
| `genbank:U36453.1` pCALkc | Insufficient for known-good now | Same pCAL-family issue as U36452.1. Good family signal, but not clean enough under the current bar. |
| `genbank:U47670.1` pJDC406 | Insufficient for known-good now | Cloning/antisense expression-vector metadata, but only ORI and beta-lactamase marker are detected. No MCS or expression slot evidence in current findings. |
| `genbank:U65078.1` pNF2214 | Insufficient for known-good now | Explicit cloning shuttle vector with kanamycin in title and MCS, but marker alias and ORI/host evidence are missing. Needs raw source review before shuttle promotion. |
| `genbank:PX275371.1` pZB1 | Rejected | Natural Zygosaccharomyces plasmid/episome with FLP only; prior audit explicitly says not yeast shuttle without engineered marker plus shuttle-vector metadata. |
| `genbank:NZ_CP071514.1` | Rejected | Natural isolate title with vector-like signals; prior audit treats this as human-review contamination/artifact candidate, not engineered-vector evidence. |
| `genbank:NZ_OZ477361.1` | Rejected | Natural isolate plasmid with pMB1/pUC-like signal but no vector metadata. Origin-like signal alone is not sufficient. |
| Current broad natural RefSeq/AMR/mobile plasmid cohort | Rejected | Prior audits identify these as natural strain/isolate, unnamed, sparse, AMR/mobile, partial, or unverified records; do not use natural resistance or mobility loci as engineered selectable-marker/vector evidence. |

## Profile Coverage Notes

- Bacterial cloning: clean candidates include phagemid and non-pUC cloning vectors (`AF013597.1`, `AF403427.1`, `AF519766.1`, `AY219701.1`, `U26464.1`).
- Bacterial expression: one clean candidate (`AF050464.1`) and several insufficient pCAL/T7-family records pending parser/source feature review.
- Mammalian expression/reporter: clean candidates `U47121.2` pSI and `AF058756.1` pFR-Luc.
- Shuttle: clean candidates `U07168.1` pUCP26 and `AF216802.1` pDL278, with host-origin verification required before insertion.
- Yeast shuttle/expression: clean candidates `AF041805.1`, `AF041806.1`, and `AF041807.1`, but near-duplicate family inflation should be considered.
- Lentiviral and CRISPR: no defensible known-good candidates found in the read findings. Retrieval findings state the current corpus has no indexed lentiviral or CRISPR profile records.

## Human-Review Questions

1. Should broad-host-range shuttle records be allowed as known-good validation cases before the validation engine has calibrated host/origin logic for those origins?
2. For yGALset records, should all three siblings be added for yeast shuttle coverage, or only one representative to avoid family inflation?
3. Should pCAL/T7-family expression records with sparse parsed features be accepted based on complete GenBank source metadata, or held until parser rehydration exposes promoter/MCS/tag evidence?
