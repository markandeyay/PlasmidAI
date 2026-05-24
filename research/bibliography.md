# Annotated Bibliography

This bibliography is organized by Phase R track. Each source listed here was cited in the corresponding findings file and includes the takeaway that affects the build.

## Track A — Plasmid Biology & Structure

1. Addgene. 2025. "Molecular Biology Reference." https://www.addgene.org/mol-bio-reference/ — Practical summary of common plasmid features used to seed canonical component types.
2. Bolivar et al. 1977. "Construction and characterization of new cloning vehicles. II. A multipurpose cloning system." DOI: 10.1016/0378-1119(77)90000-2 — Classic pBR322 example showing unique sites, markers, and backbone design logic.
3. Brown, T. A. 2002. "Studying DNA." NCBI Bookshelf. https://www.ncbi.nlm.nih.gov/books/NBK21129/ — Establishes plasmids as replicating vectors and explains origins and selectable markers.
4. del Solar et al. 1998. "Replication and Control of Circular Bacterial Plasmids." DOI: 10.1128/MMBR.62.2.434-464.1998 — Supports host/ORI/replication-control specificity.
5. Wang et al. 2009. "Classification of plasmid vectors using replication origin, selection marker and promoter as criteria." DOI: 10.1016/j.plasmid.2008.09.003 — Supports treating ORI, marker, and promoter as first-class structured fields.
6. Molloy et al. 2004. "Effective and robust plasmid topology analysis..." DOI: 10.1093/nar/gnh124 — Shows topology and isoforms matter for plasmid QC.
7. Morgan/Addgene. 2014. "Plasmids 101: The Promoter Region - Let's Go!" https://blog.addgene.org/plasmids-101-the-promoter-region — Practical promoter/host/transcript compatibility guidance.
8. Addgene. 2016. "Plasmids 101: Gateway Cloning." https://blog.addgene.org/plasmids-101-gateway-cloning — Reinforces reading-frame and fusion-tag constraints.
9. Addgene. 2023. "Viral Vectors 101: Viral Vector Elements." https://blog.addgene.org/viral-vectors-101-viral-vector-elements — Establishes viral vector designs as vector-type-specific.
10. Higgins and Vologodskii. 2015. "Topological Behavior of Plasmid DNA." DOI: 10.1128/microbiolspec.PLAS-0036-2014 — Supports explicit topology representation.

## Track B — Design & Validity Rules

1. Addgene. 2014. "Plasmids 101: The Promoter Region - Let's Go!" https://blog.addgene.org/plasmids-101-the-promoter-region — Host and transcript class must drive promoter validation.
2. Addgene. 2014. "Plasmids 101: Terminators and PolyA signals." https://blog.addgene.org/plasmids-101-terminators-and-polya-signals — Terminators/polyA elements are required downstream cassette components.
3. Chen et al. 1994. "Determination of the optimal aligned spacing between the Shine-Dalgarno sequence and the translation initiation codon..." https://academic.oup.com/nar/article/22/23/4953/2400328 — Bacterial translation initiation should check RBS/start spacing.
4. Engler et al. 2008. "A one pot, one step, precision cloning method with high throughput capability." https://pubmed.ncbi.nlm.nih.gov/18985154/ — Type IIS assembly requires strategy-specific restriction-site checks.
5. GenScript. 2026. "FLASH Gene & Gene Synthesis." https://www.genscript.com/gene_synthesis.html — Provider-specific synthesis constraints differ from Twist/IDT.
6. GenScript. 2026. "Reasons Cloning Fails - and Solutions." https://www.genscript.com/reasons_cloning_fails_solutions.html — Repeats and cloning design errors are common failure modes.
7. Haellman and Piras. 2023. "The sound of silence: transgene silencing in mammalian cell engineering." https://pmc.ncbi.nlm.nih.gov/articles/PMC9880859/ — Promoter behavior is context-dependent and can warrant WARN rather than PASS/FAIL.
8. Hawley and McClure. 1983. "Compilation and analysis of Escherichia coli promoter DNA sequences." https://pmc.ncbi.nlm.nih.gov/articles/PMC340638/ — E. coli promoter spacing is codifiable.
9. IDT. 2026. "What types of sequence motifs should be avoided when ordering gBlocks Gene Fragments?" https://www3.idtdna.com/pages/support/faqs/what-types-of-sequence-motifs-should-be-avoided-when-ordering-gblocks-gene-fragments- — gBlocks has strict motif/GC/homopolymer constraints.
10. Khan. 2013. "Gene Expression in Mammalian Cells and its Applications." https://pmc.ncbi.nlm.nih.gov/articles/PMC7147855/ — Mammalian expression vectors require coordinated regulatory, translation, propagation, and selection elements.
11. Kozak. 1987. "At least six nucleotides preceding the AUG initiator codon enhance translation in mammalian cells." https://pubmed.ncbi.nlm.nih.gov/3681984/ — Mammalian coding designs should score Kozak/start context.
12. Ling et al. 2024. "Degradation and stable maintenance of adeno-associated virus inverted terminal repeats in E. coli." https://pmc.ncbi.nlm.nih.gov/articles/PMC11754738/ — AAV ITRs require vector-specific instability handling.
13. Mauro and Chappell. 2014. "A critical analysis of codon optimization in human therapeutics." DOI: 10.1016/j.molmed.2014.09.003 — Codon optimization can affect biology and should not be automatic by default.
14. Nakagawa et al. 2008. "Diversity of preferred nucleotide sequences around the translation initiation codon..." https://pmc.ncbi.nlm.nih.gov/articles/PMC2241899/ — Start-context preferences vary across eukaryotes.
15. Nakamura et al. 2000. "Codon usage tabulated from international DNA sequence databases..." https://pmc.ncbi.nlm.nih.gov/articles/PMC102460/ — Kazusa provides codon usage reference data.
16. NEB. 2026. "Restriction Enzyme Digestion." https://www.neb.com/en/applications/cloning-and-synthetic-biology/dna-preparation/restriction-enzyme-digestion — Restriction cloning needs no internal selected enzyme sites and proper flanking bases.
17. Parret et al. 2016. "Codon usage bias." https://pmc.ncbi.nlm.nih.gov/articles/PMC8613526/ — Gene design is multi-constraint, not just CAI maximization.
18. Powell et al. 2015. "Viral Expression Cassette Elements..." https://pmc.ncbi.nlm.nih.gov/articles/PMC4505817/ — Viral vectors have cassette and packaging constraints.
19. Santos-Zavaleta et al. 2024. "RegulonDB v12.0..." https://pmc.ncbi.nlm.nih.gov/articles/PMC10767902/ — Curated E. coli regulatory reference.
20. Sarrion-Perdigones et al. 2011. "GoldenBraid..." https://pmc.ncbi.nlm.nih.gov/articles/PMC3131274/ — Type IIS systems require part domestication.
21. Sharp and Li. 1987. "The codon adaptation index..." DOI: 10.1093/nar/15.3.1281 — CAI is the baseline codon-adaptation scoring method.
22. Twist Bioscience. 2023. "Twist Tips: How to Design Your Gene." https://www.twistbioscience.com/content/dam/twistbioscience/resources/2023-06/DOC-001081_TechNote_TwistTipVectorDesign-REV4-singles.pdf — Provides concrete synthesis-readiness heuristics.
23. Twist Bioscience. 2026. "High Quality Gene Synthesis." https://www.twistbioscience.com/products/genes/gene-synthesis?tab=fragment — Confirms provider scoring factors for gene synthesis.
24. Yau et al. 2013. "Remarkable stability of an instability-prone lentiviral vector plasmid in Escherichia coli Stbl3." https://pmc.ncbi.nlm.nih.gov/articles/PMC3563744/ — Lentiviral plasmids need propagation-instability rules.
25. Zhao et al. 1999. "Formation of mRNA 3' Ends in Eukaryotes..." https://pmc.ncbi.nlm.nih.gov/articles/PMC98971/ — Polyadenylation signals have concrete sequence architecture.

## Track C — DNA Language Models & Generation

1. Ji et al. 2021. "DNABERT..." https://academic.oup.com/bioinformatics/article/37/15/2112/6128680 — Encoder model useful for classification/representation, not full plasmid generation.
2. NVIDIA BioNeMo. "DNABERT." https://docs.nvidia.com/bionemo-framework/1.10/models/dnabert.html — Creates a license-signal conflict for DNABERT commercial use.
3. Zhou et al. 2023/2024. "DNABERT-2..." https://arxiv.org/abs/2306.15006 — Efficient BPE genome encoder, likely useful for embeddings/scoring.
4. MAGICS-LAB. "DNABERT_2." https://github.com/MAGICS-LAB/DNABERT_2 — Repository license appears permissive, but weight license still needs verification.
5. zhihan1996. "DNABERT-2-117M." https://huggingface.co/zhihan1996/DNABERT-2-117M — Model-card behavior focuses on embeddings.
6. Dalla-Torre et al. 2024/2025. "Nucleotide Transformer..." https://www.nature.com/articles/s41592-024-02523-z — Strong encoder family but license constraints limit commercial use.
7. InstaDeepAI. "nucleotide-transformer-2.5b-1000g." https://huggingface.co/InstaDeepAI/nucleotide-transformer-2.5b-1000g — Non-commercial model-card license blocks production without permission.
8. Nguyen et al. 2024. "Sequence modeling and design from molecular to genome scale with Evo." https://github.com/evo-design/evo — Autoregressive DNA generator with long context.
9. Arc Institute. 2024. "Evo: DNA foundation modeling..." https://arcinstitute.org/news/blog/evo — Context for Evo capabilities.
10. togethercomputer. "evo-1-131k-base." https://huggingface.co/togethercomputer/evo-1-131k-base/tree/main — Evo 1 weight availability and license context.
11. ArcInstitute. "evo2." https://github.com/ArcInstitute/evo2 — Strong first candidate for whole-plasmid generation experiments.
12. arcinstitute. "evo2_7b_base." https://huggingface.co/arcinstitute/evo2_7b_base — Candidate open checkpoint.
13. NVIDIA BioNeMo. "Evo2." https://docs.nvidia.com/bionemo-framework/2.6/models/evo2/index.html — Hosted deployment has additional NVIDIA terms.
14. Zvyagin et al. 2022. "GenSLMs..." https://pmc.ncbi.nlm.nih.gov/articles/PMC9709791/ — GenSLM is more relevant to viral/prokaryotic sequence modeling than plasmid design.
15. ramanathanlab. "genslm." https://github.com/ramanathanlab/genslm — Code license and paper license must be separated.
16. Nguyen et al. 2023. "HyenaDNA..." https://arxiv.org/abs/2306.15794 — Long-context single-nucleotide model useful for representation comparisons.
17. HazyResearch. "hyena-dna." https://github.com/HazyResearch/hyena-dna — Apache-2.0 code/weights but not a primary plasmid generator.
18. Schiff et al. 2024. "Caduceus..." https://arxiv.org/abs/2403.03234 — Reverse-complement equivariant model relevant for embeddings/scoring.
19. kuleshov-group. "caduceus..." https://huggingface.co/kuleshov-group/caduceus-ps_seqlen-131k_d_model-256_n_layer-16/blob/main/README.md — Released Caduceus checkpoint context.
20. Helical. "Caduceus model card." https://helical.readthedocs.io/en/stable/model_cards/caduceus/ — License and model-card context.
21. InstaDeepAI. "nucleotide-transformer." https://github.com/instadeepai/nucleotide-transformer — NTv3 may be relevant but needs license verification.
22. Wu et al. 2025. "GENERator..." https://arxiv.org/abs/2502.07272 — Emerging long-context genomic generator to monitor.
23. Zhou et al. 2025. "GenomeOcean..." https://pubmed.ncbi.nlm.nih.gov/39975405/ — Emerging metagenomic generator with unclear production license.
24. HuggingFaceBio. "Carbon-3B." https://huggingface.co/HuggingFaceBio/Carbon-3B — Lower-cost Apache-2.0 generative baseline candidate.
25. HuggingFaceBio. "carbon-pretraining-corpus." https://huggingface.co/datasets/HuggingFaceBio/carbon-pretraining-corpus — Training corpus license context for Carbon.

## Track D — Prior Art & Related Tools

1. Irvine et al. 2025. "Generating functional plasmid origins with OriGen." DOI: 10.1093/nar/gkaf1198 — Functional origin generation is proven for a narrow scope, not full plasmids.
2. Shao. 2024. "PlasmidGPT." https://github.com/lingxusb/PlasmidGPT — Plasmid-like sequence generation prior art, with validation/licensing caveats.
3. Shao. 2024. "PlasmidGPT" bioRxiv. DOI: 10.1101/2024.09.30.615762 — Preprint context for PlasmidGPT.
4. UCL-CSSB. 2026. "PlasmidGPT compatible version." https://huggingface.co/UCL-CSSB/PlasmidGPT — Architecture/context for model compatibility.
5. `lingxusb/PlasmidGPT`. 2026. https://huggingface.co/lingxusb/PlasmidGPT — Conflicting non-commercial model license signal.
6. Enghiad et al. 2022. "PlasmidMaker..." DOI: 10.1038/s41467-022-30355-y — Automated construction platform, not NL-to-design.
7. Cai. 2010. "GenoCAD..." https://vtechworks.lib.vt.edu/handle/10919/27069 — Formal grammars are useful for construct constraints.
8. McGuffie and Barrick. 2021. "pLannotate..." DOI: 10.1093/nar/gkab374 — Strong precedent for engineered plasmid annotation.
9. Wishart Lab. 2023. "PlasMapper 3.0 help." https://plasmapper.wishartlab.com/help/ — Visualization/annotation/export expectations.
10. Benchling. 2026. "Molecular Bio Software." https://www.benchling.com/molecular-biology — Enterprise CAD/registry feature baseline.
11. SnapGene. 2026. "Discover SnapGene." https://www.snapgene.com/series/snapgene-tour — Human-operated cloning simulation and map expectations.
12. SnapGene Support. 2025. "Simulate Gateway Cloning with Multiple Inserts." https://support.snapgene.com/hc/en-us/articles/10384092210708-Simulate-Gateway-Cloning-with-Multiple-Inserts — Method-specific cloning simulation precedent.
13. VectorBuilder. 2026. "Online Vector Design." https://en.vectorbuilder.com/products-services/service/online-vector-design.html/1000 — Strong component-driven design/order workflow reference.
14. Asimov. 2026. "Welcome to Kernel." https://docs.kernel.asimov.com/ — Product reference for model-guided construct design.
15. Asimov. 2026. "Compiler." https://docs.kernel.asimov.com/compiler-and-simulation/compiler — Closest compiler-style plasmid design precedent.
16. Asimov. 2026. "Kernel." https://www.asimov.com/kernel — Commercial positioning and capability context.
17. Addgene. 2026. "Browse Genes / Search by Sequence." https://www.addgene.org/browse/gene/ — Retrieval source and user expectation baseline.
18. Addgene Help Center. 2026. "How does Addgene create plasmid maps?" https://help.addgene.org/hc/en-us/articles/115005662726-How-does-Addgene-create-plasmid-maps — Sequence provenance and map-generation caveats.

## Track E — Data Sources & Access

1. Addgene. 2026. "Access Plasmid and Sequence Data via API." https://developers.addgene.org/ — Programmatic Addgene data requires approved access.
2. Addgene Developers Portal. 2026. "Access Options." https://developers.addgene.org/access-options/ — Bulk JSON and API versioning/access details.
3. Addgene Developers API. 2026. "Addgene Developers API." https://docs.developers.addgene.org/docs/ — Endpoint and field contract for ingestion.
4. Addgene Help Center. 2026. "What is the Developers Portal?" https://help.addgene.org/hc/en-us/articles/38241923181453-What-is-the-Developers-Portal — Access approval and license workflow.
5. Addgene Help Center. 2026. "Requirements for viewing plasmid sequence data." https://help.addgene.org/hc/en-us/articles/44210206209549-Are-there-any-requirements-for-viewing-plasmid-sequence-data-on-the-Addgene-website — Sequence access is controlled.
6. Addgene Help Center. 2026. "Do you have full sequence for my plasmid?" https://help.addgene.org/hc/en-us/articles/205434259-Do-you-have-full-sequence-for-my-plasmid — Sequence completeness varies.
7. Addgene Help Center. 2026. "How does Addgene create plasmid maps?" https://help.addgene.org/hc/en-us/articles/115005662726-How-does-Addgene-create-plasmid-maps — Sequence provenance categories.
8. Addgene. 2023. "Terms of Use." https://www.addgene.org/terms-of-use/ — Commercial/data-use restrictions require review.
9. Sayers. 2009/2022. "A General Introduction to the E-utilities." https://www.ncbi.nlm.nih.gov/sites/books/NBK25497/ — NCBI access, throttling, and client identification rules.
10. Sayers. 2009/2022. "The E-utilities In-Depth." https://www.ncbi.nlm.nih.gov/books/NBK25499/ — EFetch formats and retrieval details.
11. NCBI. 2026. "GenBank Overview." https://www.ncbi.nlm.nih.gov/genbank/genbank/ — GenBank scope, releases, and use caveats.
12. NCBI. 2017. "FTP access to GenBank data." https://www.ncbi.nlm.nih.gov/genbank/ftp/ — Bulk data access route.
13. NCBI. 2025. "FASTA Format for Nucleotide Sequences." https://www.ncbi.nlm.nih.gov/genbank/fastaformat/ — FASTA import/export rules.
14. DDBJ/ENA/GenBank. 2026. "Feature Table Definition." https://www.ddbj.nig.ac.jp/ddbj/feature-table.html — Canonical feature vocabulary and location syntax.
15. NCBI Datasets. 2026. "`datasets download genome` reference." https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/command-line/datasets/download/genome/ — Useful but not a replacement for Entrez plasmid record retrieval.

## Track F — Sequence Representation & Tokenization

1. Ji et al. 2021. "DNABERT." DOI: 10.1093/bioinformatics/btab083 — Overlapping k-mer tokenization baseline.
2. Zhou et al. 2024. "DNABERT-2." https://arxiv.org/abs/2306.15006 — BPE tokenization motivation and efficiency tradeoffs.
3. Dalla-Torre et al. 2024. "Nucleotide Transformer." DOI: 10.1038/s41592-024-02523-z — 6-mer encoder representation baseline.
4. Nguyen et al. 2023. "HyenaDNA." DOI: 10.48550/arXiv.2306.15794 — Single-nucleotide long-context representation baseline.
5. Nguyen et al. 2024. "Evo." DOI: 10.1126/science.ado9336 — Byte/single-nucleotide generative sequence modeling.
6. Sanabria et al. 2024. "GROVER..." DOI: 10.1038/s42256-024-00872-0 — BPE over genome sequence context.
7. Huang et al. 2026. "EvoLen..." DOI: 10.48550/arXiv.2604.08698 — Emerging biology-guided tokenization idea to monitor.
8. Niktab and Patel. 2026. "DNATokenizer..." DOI: 10.48550/arXiv.2601.05531 — Tokenization throughput can be a production bottleneck.
9. DDBJ/ENA/GenBank. 2026. "Feature Table Definition." https://www.ddbj.nig.ac.jp/ddbj/feature-table.html — Feature coordinate and qualifier standard.
10. Biopython. 2026. "Bio.SeqFeature module documentation." https://biopython.org/docs/1.76/api/Bio.SeqFeature.html — Python coordinate conversion and compound-feature behavior.
11. NCBI. 2026. "GFF3 format." https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/file-formats/annotation-files/about-ncbi-gff3/ — GFF3 coordinate/origin-spanning behavior.
12. Addgene. 2026. "Plasmids 101 topic overview." https://info.addgene.org/plasmids-101-topic-page — Plasmids are commonly circular molecules.
13. Benchling. 2025. "Creating consensus and template alignments..." https://help.benchling.com/hc/en-us/articles/9684273213325-Creating-consensus-and-template-alignments-on-DNA-RNA-sequences — Circular/cross-origin handling matters in practice.
14. Zhou, Shrikumar, and Kundaje. 2022. "Reverse-Complement Equivariance..." https://proceedings.mlr.press/v165/zhou22a.html — Reverse-complement behavior must be evaluated.
15. Schiff et al. 2024. "Caduceus..." https://arxiv.org/abs/2403.03234 — Architecture-level reverse-complement equivariance reference.

## Track G — Validation Tooling

1. Roberts et al. 2023. "REBASE..." DOI: 10.1093/nar/gkac975 — Restriction-enzyme metadata source.
2. Biopython contributors. 2026. "Bio.Restriction package." https://biopython.org/docs/latest/api/Bio.Restriction.html — Local deterministic restriction analysis implementation.
3. Biopython contributors. 2026. "Bio.SeqUtils.CodonAdaptationIndex." https://biopython.org/docs/latest/api/Bio.SeqUtils.html — CAI implementation and codon optimization utility.
4. Sharp and Li. 1987. "The codon adaptation index..." DOI: 10.1093/nar/15.3.1281 — Codon adaptation scoring basis.
5. Kazusa DNA Research Institute. "Codon Usage Database." https://www.kazusa.or.jp/codon/ — Legacy codon table reference.
6. Kazusa DNA Research Institute. "Countcodon." https://www.kazusa.or.jp/codon/countcodon.html — Spot-check codon counting reference.
7. Athey et al. 2017. "A new and updated resource for codon usage tables." DOI: 10.1186/s12859-017-1793-7 — HIVE-CUTs should be preferred where available.
8. EMBOSS. "etandem manual." https://emboss.bioinformatics.nl/cgi-bin/emboss/help/etandem — Tandem-repeat detection reference.
9. EMBOSS. "einverted manual." https://emboss.bioinformatics.nl/cgi-bin/emboss/help/einverted — Inverted-repeat detection reference.
10. Twist Bioscience. "Express Genes." https://www.twistbioscience.com/products/genes/express-genes — Twist synthesis constraints.
11. IDT. "gBlocks and gBlocks HiFi Gene Fragments." https://www.eu.idtdna.com/pages/products/genes-and-gene-fragments/double-stranded-dna-fragments/gblocks-gene-fragments — IDT synthesis constraints.
12. GenScript. "FLASH Gene & Gene Synthesis." https://www.genscript.com/gene_synthesis.html — GenScript synthesis constraints.
13. SIB/ExPASy. "EPD." https://epd.expasy.org/epd/ — Natural eukaryotic promoter reference.
14. Rauluseviciute et al. 2024. "JASPAR 2024." DOI: 10.1093/nar/gkad1059 — TF binding profile database.
15. Santos-Zavaleta et al. 2024. "RegulonDB v12.0." DOI: 10.1093/nar/gkad1072 — E. coli regulation database.
16. Addgene. "Plasmids 101: The Promoter Region." https://blog.addgene.org/plasmids-101-the-promoter-region — Practical promoter compatibility rules.
17. Addgene. "Plasmids 101: What is a plasmid?" https://blog.addgene.org/plasmids-101-what-is-a-plasmid — Component classes for validation.
18. Sequence Ontology Consortium. "Sequence Ontology." https://www.sequenceontology.org/ — Controlled vocabulary for feature normalization.
19. SYSTEM_DESIGN.md. Local source-of-truth sections 8, 11, 12, and 14 — Validation report and test contract.

## Track H — Visualization

1. Lattice Automation. 2025. "`seqviz` npm package." https://www.npmjs.com/package/seqviz — Default circular/linear plasmid map renderer.
2. Lattice Automation. 2025. "`seqviz` GitHub README." https://github.com/Lattice-Automation/seqviz — Feature, primer, enzyme, and interaction support.
3. Lattice Automation. 2024. "`seqparse` npm package." https://www.npmjs.com/package/seqparse — Optional frontend-side parser.
4. TeselaGen. 2024. "`openVectorEditor`." https://github.com/TeselaGen/openVectorEditor — Future editing surface candidate.
5. Grant and CGView.js team. 2025. "CGView.js documentation." https://js.cgview.ca/ — Alternative for dense circular genome maps.
6. Grant and CGView.js team. 2025. "CGView.js API documentation." https://js.cgview.ca/api/index.html — API/license details.
7. Stothard, Grant, and Van Domselaar. 2019. "Visualizing and comparing circular genomes using the CGView family of tools." https://pubmed.ncbi.nlm.nih.gov/29939276/ — CGView family background.
8. GMOD/JBrowse. 2026. "JBrowse 2 embedded components." https://jbrowse.org/jb2/docs/embedded_components/ — Future genome-browser component option.
9. GMOD/JBrowse. 2026. "JBrowse 2 FAQ." https://jbrowse.org/jb2/docs/faq/ — Embedded vs full-app tradeoffs.
10. GMOD/JBrowse. 2025. "`@jbrowse/react-circular-genome-view`." https://www.npmjs.com/package/%40jbrowse/react-circular-genome-view — Circular view package details.
11. Diesh et al. 2023. "JBrowse 2..." https://pmc.ncbi.nlm.nih.gov/articles/PMC10108523/ — Modular browser reference.
12. IGV Team. 2026. "`igv.js` documentation." https://igv.org/doc/igvjs/ — Genome-track viewer alternative.
13. IGV Team. 2026. "`igv.js` quickstart." https://igv.org/doc/igvjs/QuickStart/ — Shows track/reference configuration model.
14. Robinson et al. 2023. "igv.js..." https://academic.oup.com/bioinformatics/article/39/1/btac830/6958554 — Browser-only genome viewer reference.

## Track I — System Architecture & ML In Production

1. Lewis et al. 2020. "Retrieval-Augmented Generation..." https://arxiv.org/abs/2005.11401 — RAG improves grounding/updateability but is not a correctness proof.
2. Cohan et al. 2020. "SPECTER..." https://aclanthology.org/2020.acl-main.207/ — Domain scientific embeddings matter.
3. Wadden et al. 2020. "Fact or Fiction..." https://aclanthology.org/2020.emnlp-main.609/ — Scientific claim verification is a retrieval/reasoning task.
4. Wu et al. 2024. "Medical Graph RAG..." https://arxiv.org/abs/2408.04187 — Structured knowledge can strengthen biomedical RAG.
5. Zhao et al. 2025. "MedRAG..." https://arxiv.org/abs/2502.04413 — Graph/context retrieval pattern for healthcare.
6. Es et al. 2023/2025. "Ragas..." https://arxiv.org/abs/2309.15217 — RAG eval should split context relevance, faithfulness, and answer quality.
7. Saad-Falcon et al. 2023/2024. "ARES..." https://arxiv.org/abs/2311.09476 — Automated RAG eval with small human sets.
8. Kwon et al. 2023. "PagedAttention." https://arxiv.org/abs/2309.06180 — vLLM serving architecture for efficient long-context generation.
9. Hugging Face. "Text Generation Inference." https://huggingface.co/docs/text-generation-inference/index — Production serving reference, now maintenance-mode.
10. Hugging Face. "TGI Quantization." https://huggingface.co/docs/text-generation-inference/conceptual/quantization — Quantization tradeoffs and methods.
11. NVIDIA. "Triton Inference Server." https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/index.html — Heterogeneous model serving option.
12. NVIDIA. "Triton Model Repository." https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/model_repository.html — Versioned model repository pattern.
13. Dettmers et al. 2022. "LLM.int8()." https://arxiv.org/abs/2208.07339 — Quantization can reduce memory but needs eval.
14. MLflow. "Model Registry Workflows." https://mlflow.org/docs/latest/ml/model-registry/workflow/ — Registry/versioning pattern.
15. KServe. "Canary Rollout Strategy." https://kserve.github.io/archive/0.13/modelserving/v1beta1/rollout/canary/ — Canary and rollback serving controls.
16. OWASP. "Top 10 for LLM Applications." https://owasp.org/www-project-top-10-for-large-language-model-applications/ — LLM application threat model.
17. NIST. 2024. "Generative AI Profile." https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf — AI risk management reference.

## Track J — Biosecurity & Compliance

1. OSTP. 2024. "Framework for Nucleic Acid Synthesis Screening." https://www.whitehouse.gov/wp-content/uploads/2024/10/OSTP-Nucleic-Acid_Synthesis_Screening_Framework-Sep2024-Final.pdf — Current screening framework baseline cited by the research.
2. The White House. 2025. "Improving the Safety and Security of Biological Research." https://www.whitehouse.gov/presidential-actions/2025/05/improving-the-safety-and-security-of-biological-research/ — Requires checking the post-EO framework status.
3. HHS ASPR. 2023. "Screening Framework Guidance for Providers and Users of Synthetic Nucleic Acids." https://regulations.justia.com/regulations/fedreg/2023/10/13/2023-22540.html — Broader DNA/RNA screening guidance and customer duties.
4. Federal Select Agent Program. 2025. "Select Agents and Toxins List." https://www.selectagents.gov/sat/list.htm — Select-agent/toxin relevance.
5. eCFR. Current. "15 CFR Part 774, Supplement No. 1." https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-774/appendix-Supplement%20No.%201%20to%20Part%20774 — Export-control sequence relevance.
6. IGSC. 2024. "Harmonized Screening Protocol v3.0." https://genesynthesisconsortium.org/wp-content/uploads/IGSC-Harmonized-Screening-Protocol-v3.0-1.pdf — Industry screening protocol.
7. IBBIS. "Common Mechanism." https://ibbis.bio/our-work/common-mechanism/ — Candidate screening implementation.
8. IBBIS. "Common Mechanism FAQ." https://ibbis.bio/our-work/common-mechanism/faq/ — Screening limitations that must become product rules.
9. NIST. 2025 update. "Biosecurity for Synthetic Nucleic Acid Sequences." https://www.nist.gov/programs-projects/biosecurity-synthetic-nucleic-acid-sequences — AI-enabled design is an emerging screening problem.
10. Laird et al. 2025. "Inter-tool analysis of a NIST dataset..." https://www.nist.gov/publications/inter-tool-analysis-nist-dataset-assessing-baseline-nucleic-acid-sequence-screening — Screening tools can disagree despite high aggregate sensitivity.
11. Wang et al. 2025. "A Call for Built-In Biosecurity Safeguards for Generative AI Tools." DOI: 10.1038/s41587-025-02650-8 — Generative bio-design tools need built-in safeguards.
12. Department for Science, Innovation and Technology. 2024. "UK screening guidance on synthetic nucleic acids." https://www.gov.uk/government/publications/uk-screening-guidance-on-synthetic-nucleic-acids — International screening regimes differ.
