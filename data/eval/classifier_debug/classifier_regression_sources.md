# Classifier Regression Fixture Sources

This sidecar documents the provenance of the labeled classifier regression cases in
`tests/data_pipeline/parse/test_classifier_regression.py`. The tests intentionally use
small synthetic `AnnotatedSequence` objects rather than copied full vector sequences.
They exercise classification boundaries only; they are not sequence-reference records.

## Published Vector Labels

| Fixture key | Classification evidence | Source |
| --- | --- | --- |
| `pUC19` | Bacterial cloning vector with pMB1/pUC origin, ampicillin resistance, and an MCS in lacZ alpha. | Yanisch-Perron C, Vieira J, Messing J. *Gene*. 1985;33:103-119. [doi:10.1016/0378-1119(85)90120-9](https://doi.org/10.1016/0378-1119(85)90120-9) |
| `pBR322` | Bacterial cloning plasmid with replication origin and antibiotic resistance determinants. | Sutcliffe JG. *Cold Spring Harb Symp Quant Biol*. 1979;43:77-90. [doi:10.1101/SQB.1979.043.01.012](https://doi.org/10.1101/SQB.1979.043.01.012) |
| `pBluescript` | Cloning backbone with MCS flanked by T3 and T7 promoter sites. The promoter sites alone do not make it an in-vivo expression vector. | Agilent, *pBluescript II Phagemid Vectors Instruction Manual*. [PDF](https://www.agilent.com/cs/library/usermanuals/public/212205.pdf) |
| `pGEX` | Bacterial GST fusion expression-vector family. | Cytiva, *GST Gene Fusion System*. [Product documentation](https://www.cytivalifesciences.com/en/us/shop/protein-analysis/protein-sample-preparation/purification/gst-tagged-protein-purification) |
| `pBAD` | Arabinose-regulated bacterial expression architecture. | Guzman LM et al. *J Bacteriol*. 1995;177:4121-4130. [doi:10.1128/jb.177.14.4121-4130.1995](https://doi.org/10.1128/jb.177.14.4121-4130.1995) |
| `pET` | T7 RNA polymerase bacterial expression architecture. | Studier FW, Moffatt BA. *J Mol Biol*. 1986;189:113-130. [doi:10.1016/0022-2836(86)90385-2](https://doi.org/10.1016/0022-2836(86)90385-2) |
| `pcDNA3.1` | Mammalian expression vector with CMV promoter, MCS, polyadenylation signal, bacterial origin, and selection markers. | Thermo Fisher Scientific, pcDNA3.1 product documentation. [Catalog V79020](https://www.thermofisher.com/order/catalog/product/V79020) |
| `pCAGGS` | Mammalian expression vector driven by the CAG promoter. | Niwa H, Yamamura K, Miyazaki J. *Gene*. 1991;108:193-199. [doi:10.1016/0378-1119(91)90434-D](https://doi.org/10.1016/0378-1119(91)90434-D) |
| `pEGFP-N1` | Mammalian EGFP reporter/fusion-vector family. | Takara Bio, fluorescent protein vector documentation. [Product page](https://www.takarabio.com/products/gene-function/fluorescent-proteins/fluorescent-protein-vectors) |
| `pGL3` | Luciferase reporter-vector family, including promoterless basic backbones. | Promega, *pGL3 Luciferase Reporter Vectors Technical Manual*. [Protocol page](https://www.promega.com/resources/protocols/technical-manuals/0/pgl3-luciferase-reporter-vectors-protocol/) |
| `pGL4` | Luciferase reporter-vector family, including promoterless basic backbones. | Promega, pGL4 luciferase reporter-vector documentation. [Product page](https://www.promega.com/products/reporter-assays-and-transfection/reporter-vectors-and-cell-lines/pgl4-luciferase-reporter-vectors/) |
| `pLKO.1` | Lentiviral transfer plasmid architecture with LTR and packaging elements. | Addgene, pLKO.1 - TRC cloning vector plasmid page. [Plasmid #10878](https://www.addgene.org/10878/) |
| `lentiviral` | Lentiviral transfer vectors contain transfer elements such as LTRs and packaging signal; packaging functions are supplied separately. | Addgene, Viral Vector Guide. [Guide](https://www.addgene.org/viral-vectors/) |
| `retroviral` | Retroviral transfer-vector design convention. | Miller AD, Rosman GJ. *Biotechniques*. 1989;7:980-990. [PubMed](https://pubmed.ncbi.nlm.nih.gov/2631796/) |
| `pX330` | CRISPR plasmid carrying Cas9 and guide-expression functions. | Cong L et al. *Science*. 2013;339:819-823. [doi:10.1126/science.1231143](https://doi.org/10.1126/science.1231143) |
| `lentiCRISPR` | Lentiviral CRISPR-vector architecture; CRISPR profile takes precedence over delivery modifier in the classifier. | Sanjana NE, Shalem O, Zhang F. *Nat Methods*. 2014;11:783-784. [doi:10.1038/nmeth.3047](https://doi.org/10.1038/nmeth.3047) |
| `pX458` | CRISPR plasmid with reporter function; the synthetic fixture tests CRISPR precedence over reporter classification. | Addgene, pSpCas9(BB)-2A-GFP (PX458) plasmid page. [Plasmid #48138](https://www.addgene.org/48138/) |
| `pRS416` | Yeast shuttle-vector architecture with bacterial propagation and yeast maintenance/selection elements. | Sikorski RS, Hieter P. *Genetics*. 1989;122:19-27. [doi:10.1093/genetics/122.1.19](https://doi.org/10.1093/genetics/122.1.19) |
| `pYES2` | Yeast expression/shuttle vector with 2-micron origin, URA3 selection, and GAL1 promoter. | Thermo Fisher Scientific, pYES2 product documentation. [Catalog V82520](https://www.thermofisher.com/order/catalog/product/V82520) |

## Synthetic Boundary Fixtures

The following fixtures are intentionally synthetic and are not claims about complete
published vector maps:

- `synthetic_pUCP26_like` exercises the explicit rule that an SP6 sequencing promoter
  plus generic CDS annotation is insufficient evidence for bacterial expression.
- `synthetic_sequencing_promoters` exercises the same boundary for T7/T3 sites on a
  cloning backbone.
- `synthetic_pDL278_like` prevents `ltr` inside `adenyltransferase` from firing a viral
  signal.
- `synthetic_substring_boundary` fixtures prevent short-token matches inside unrelated
  words: `ars` inside `arsenate`, `cen` inside `central`, and `tre` inside
  `streptomycin`.
- `synthetic_single_ltr` and `synthetic_single_viral_element` require corroborating
  viral-transfer evidence rather than one isolated element.
- `synthetic_ambiguous` fixtures verify conservative `unknown` fallback behavior.
- `synthetic_reporter_fragment` and `synthetic_crispr_fragment` document current
  profile-signal behavior for partial annotations; they do not imply completeness.
- `synthetic_dual_host_expression` verifies that an explicit mammalian expression
  cassette takes precedence over the generic shuttle-vector fallback.
- `synthetic_general_shuttle` verifies the generic multi-origin shuttle profile when
  no more specific host profile is present.

## Interpretation

Classification and annotation completeness are separate decisions. Some synthetic
fragment fixtures classify into a profile while remaining incomplete. The suite asserts
the selected profile and a minimum expected reasoning trace; profile-specific
completeness is covered by parser and schema tests.

