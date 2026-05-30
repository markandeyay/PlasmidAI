from __future__ import annotations

from dataclasses import dataclass

from packages.core.schemas import AnnotatedSequence


UNKNOWN_PROFILE = "unknown"


@dataclass(frozen=True)
class ClassificationResult:
    profile: str
    confidence: float
    signals: tuple[str, ...]


def classify(annotated_sequence: AnnotatedSequence) -> ClassificationResult:
    """Classify a plasmid into a conservative vector profile from detected features."""
    context = FeatureContext(annotated_sequence)

    checks = (
        crispr_vector,
        lentiviral_or_retroviral_transfer_vector,
        yeast_shuttle_vector,
        mammalian_reporter_vector,
        mammalian_expression_vector,
        bacterial_expression_vector,
        bacterial_cloning_vector,
        general_shuttle_vector,
    )
    for check in checks:
        result = check(context)
        if result is not None:
            return result
    return ClassificationResult(UNKNOWN_PROFILE, 0.0, ("no profile-specific signals met threshold",))


def is_annotation_complete(annotated_sequence: AnnotatedSequence, profile: str) -> bool:
    context = FeatureContext(annotated_sequence)
    if profile == "bacterial_cloning_vector":
        return context.has("ORI") and (
            (context.has("marker") and context.has("MCS")) or context.count("marker") >= 2
        )
    if profile == "bacterial_expression_vector":
        return context.has_all("ORI", "marker", "promoter") and context.has_any("GOI", "MCS")
    if profile == "mammalian_expression_vector":
        return context.has_all("ORI", "marker", "promoter", "terminator") and context.has_any("GOI", "MCS")
    if profile == "mammalian_reporter_vector":
        return context.has_all("ORI", "marker", "GOI") and context.has_any("terminator", "MCS")
    if profile == "lentiviral_or_retroviral_transfer_vector":
        return context.has_all("ORI", "marker") and context.has_any("GOI", "MCS") and context.has_viral_signal()
    if profile == "crispr_vector":
        return context.has_all("ORI", "marker") and context.has_crispr_signal()
    if profile == "yeast_shuttle_vector":
        return context.has_all("ORI", "marker") and context.has_any("MCS", "GOI")
    if profile == "general_shuttle_vector":
        return context.count("ORI") >= 2 and context.has("marker") and context.has_any("MCS", "GOI", "promoter")
    return False


class FeatureContext:
    def __init__(self, annotated_sequence: AnnotatedSequence) -> None:
        self.features = annotated_sequence.features
        self.types = [str(feature.type) for feature in self.features]
        self.text = " ".join(
            [str(feature.type) for feature in self.features] + [feature.name for feature in self.features]
        ).lower()

    def has(self, feature_type: str) -> bool:
        return feature_type in self.types

    def count(self, feature_type: str) -> int:
        return sum(1 for item in self.types if item == feature_type)

    def has_all(self, *feature_types: str) -> bool:
        return all(self.has(feature_type) for feature_type in feature_types)

    def has_any(self, *feature_types: str) -> bool:
        return any(self.has(feature_type) for feature_type in feature_types)

    def terms(self, *terms: str) -> list[str]:
        return [term for term in terms if term.lower() in self.text]

    def has_viral_signal(self) -> bool:
        return bool(
            self.terms(
                "ltr",
                "long terminal repeat",
                "psi",
                "packaging signal",
                "rre",
                "cppt",
                "wpre",
                "mscv",
                "lentiviral",
                "retroviral",
            )
        )

    def has_crispr_signal(self) -> bool:
        return bool(self.terms("crispr", "cas9", "dcas9", "ncas9", "cas12", "cpf1", "sgrna", "guide rna", "grna"))

    def has_yeast_signal(self) -> bool:
        return bool(self.terms("ura3", "leu2", "his3", "trp1", "ars", "cen", "2-micron", "2 micron", "yeast"))

    def has_reporter_signal(self) -> bool:
        return bool(
            self.terms(
                "egfp",
                "gfp",
                "mcherry",
                "dsred",
                "luciferase",
                "luc+",
                "luc2",
                "renilla",
                "reporter",
            )
        )

    def has_mammalian_expression_signal(self) -> bool:
        return bool(self.terms("cmv", "ef1", "ef-1", "cag", "pgk", "sv40", "tre", "bgh", "polyadenylation"))

    def has_bacterial_expression_signal(self) -> bool:
        return bool(
            self.terms(
                "t7",
                "t3",
                "sp6",
                "tac",
                "trc",
                "pbad",
                "arabad",
                "gst",
                "mbp",
                "his-tag",
                "his tag",
                "rbs",
                "shine-dalgarno",
            )
        )

    def has_cloning_backbone_signal(self) -> bool:
        return bool(
            self.terms(
                "puc",
                "pbr322",
                "pmb1",
                "cole1",
                "p15a",
                "pbluescript",
                "lacz",
                "polylinker",
                "multiple cloning",
            )
        )


def crispr_vector(context: FeatureContext) -> ClassificationResult | None:
    signals = context.terms("crispr", "cas9", "dcas9", "ncas9", "cas12", "cpf1", "sgrna", "guide rna", "grna")
    if not signals:
        return None
    confidence = 0.95 if len(signals) >= 2 else 0.85
    return ClassificationResult("crispr_vector", confidence, tuple(signals))


def lentiviral_or_retroviral_transfer_vector(context: FeatureContext) -> ClassificationResult | None:
    signals = context.terms("ltr", "long terminal repeat", "psi", "packaging signal", "rre", "cppt", "wpre", "mscv")
    if not signals:
        return None
    confidence = 0.92 if len(signals) >= 2 else 0.82
    return ClassificationResult("lentiviral_or_retroviral_transfer_vector", confidence, tuple(signals))


def yeast_shuttle_vector(context: FeatureContext) -> ClassificationResult | None:
    signals = context.terms("ura3", "leu2", "his3", "trp1", "ars", "cen", "2-micron", "2 micron", "yeast")
    if not signals:
        return None
    confidence = 0.92 if context.has("ORI") and context.has("marker") else 0.78
    return ClassificationResult("yeast_shuttle_vector", confidence, tuple(signals))


def mammalian_reporter_vector(context: FeatureContext) -> ClassificationResult | None:
    signals = context.terms("egfp", "gfp", "mcherry", "dsred", "luciferase", "luc+", "luc2", "renilla", "reporter")
    if not signals:
        return None
    confidence = 0.90 if context.has("GOI") else 0.75
    return ClassificationResult("mammalian_reporter_vector", confidence, tuple(signals))


def mammalian_expression_vector(context: FeatureContext) -> ClassificationResult | None:
    signals = context.terms("cmv", "ef1", "ef-1", "cag", "pgk", "sv40", "tre", "bgh", "polyadenylation")
    if not signals:
        return None
    if not context.has_any("GOI", "MCS"):
        return None
    confidence = 0.85 if context.has("terminator") else 0.72
    return ClassificationResult("mammalian_expression_vector", confidence, tuple(signals))


def bacterial_expression_vector(context: FeatureContext) -> ClassificationResult | None:
    signals = context.terms(
        "t7",
        "t3",
        "sp6",
        "tac",
        "trc",
        "pbad",
        "arabad",
        "gst",
        "mbp",
        "his-tag",
        "his tag",
        "rbs",
        "shine-dalgarno",
    )
    if not signals:
        return None
    strong_expression_signals = [
        signal for signal in signals if signal not in {"t7", "t3", "sp6"}
    ]
    if not strong_expression_signals and context.has("MCS") and not context.has("GOI"):
        return None
    if not context.has_all("ORI", "marker", "promoter"):
        return None
    confidence = 0.86 if context.has_any("GOI", "MCS") else 0.72
    return ClassificationResult("bacterial_expression_vector", confidence, tuple(signals))


def bacterial_cloning_vector(context: FeatureContext) -> ClassificationResult | None:
    signals = context.terms(
        "puc",
        "pbr322",
        "pmb1",
        "cole1",
        "p15a",
        "pbluescript",
        "lacz",
        "polylinker",
        "multiple cloning",
    )
    if not (context.has("ORI") and context.has("marker")):
        return None
    if context.has("MCS") or context.count("marker") >= 2 or signals:
        confidence = 0.84 if context.has("MCS") or context.count("marker") >= 2 else 0.72
        return ClassificationResult("bacterial_cloning_vector", confidence, tuple(signals or ["ORI+marker cloning backbone"]))
    return None


def general_shuttle_vector(context: FeatureContext) -> ClassificationResult | None:
    if context.count("ORI") >= 2 and context.has("marker"):
        return ClassificationResult("general_shuttle_vector", 0.68, ("multiple origins", "selectable marker"))
    return None
