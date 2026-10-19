"""ClinVar review status, classification groups and gene fields.

The mappings follow the ClinVar review status documentation
(https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/, read 2026-10-19) and the
CLNSIG values present in the 2025-10-13 and 2026-10-11 GRCh38 VCF releases.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Group(StrEnum):
    # Codes are written into VCF INFO fields, so they contain no spaces.
    PLP = "PLP"
    VUS = "VUS"
    BLB = "BLB"
    CONFLICTING = "CONFLICTING"
    RISK = "RISK_ALLELE"
    OTHER = "OTHER"
    MIXED = "MIXED"
    NONE = "NONE"


# Aggregate (VCV) review status to gold stars. Values appear in the VCF with spaces
# replaced by underscores.
REVIEW_STARS: dict[str, int] = {
    "practice_guideline": 4,
    "reviewed_by_expert_panel": 3,
    "criteria_provided,_multiple_submitters,_no_conflicts": 2,
    "criteria_provided,_conflicting_classifications": 1,
    "criteria_provided,_conflicting_interpretations": 1,  # name used before 2024
    "criteria_provided,_single_submitter": 1,
    "no_assertion_criteria_provided": 0,
    "no_classification_provided": 0,
    "no_assertion_provided": 0,
    "no_classification_for_the_single_variant": 0,
    "no_classifications_from_unflagged_records": 0,
    "no_interpretation_for_the_single_variant": 0,
}

_TERM_GROUP: dict[str, Group] = {
    "pathogenic": Group.PLP,
    "likely_pathogenic": Group.PLP,
    "pathogenic,_low_penetrance": Group.PLP,
    "likely_pathogenic,_low_penetrance": Group.PLP,
    "uncertain_significance": Group.VUS,
    "vus-low": Group.VUS,
    "vus-mid": Group.VUS,
    "vus-high": Group.VUS,
    "likely_benign": Group.BLB,
    "benign": Group.BLB,
    "conflicting_classifications_of_pathogenicity": Group.CONFLICTING,
    "conflicting_interpretations_of_pathogenicity": Group.CONFLICTING,
    "established_risk_allele": Group.RISK,
    "likely_risk_allele": Group.RISK,
    "uncertain_risk_allele": Group.RISK,
}


class UnknownReviewStatusError(ValueError):
    pass


def review_stars(revstat: str) -> int:
    """Return gold stars for a CLNREVSTAT value; '.' (no germline record) gives 0.

    Unknown values raise, so that a new ClinVar status is noticed at the monthly update
    instead of silently scoring zero.
    """
    value = revstat.strip()
    if value in {"", "."}:
        return 0
    try:
        return REVIEW_STARS[value]
    except KeyError as exc:
        raise UnknownReviewStatusError(f"unknown ClinVar review status: {value!r}") from exc


@dataclass(frozen=True)
class Classification:
    group: Group
    low_penetrance: bool
    risk_allele_component: bool


def classify(clnsig: str) -> Classification:
    """Group a germline CLNSIG value.

    Only the part before the first '|' is the ACMG-style classification; terms after it
    (risk_factor, drug_response, other) are extra assertions and do not change the group.
    Components joined by '/' must agree once risk-allele terms are set aside; a mix of,
    for example, P/LP and benign terms would give MIXED.
    """
    value = clnsig.strip()
    if value in {"", "."}:
        return Classification(Group.NONE, low_penetrance=False, risk_allele_component=False)
    primary = value.split("|", 1)[0]
    components = [c.lower() for c in primary.split("/") if c]
    groups = [_TERM_GROUP.get(c, Group.OTHER) for c in components]
    low_penetrance = any(c.endswith("_low_penetrance") for c in components)
    has_risk = Group.RISK in groups
    core = {g for g in groups if g is not Group.RISK}
    if not core:
        group = Group.RISK
    elif len(core) == 1:
        group = core.pop()
    else:
        group = Group.MIXED
    return Classification(group, low_penetrance, has_risk and group is not Group.RISK)


def gene_symbols(geneinfo: str) -> list[str]:
    """Split GENEINFO ('BRCA1:672|NBR2:10230') into symbols, keeping order."""
    if geneinfo in {"", "."}:
        return []
    return [pair.split(":", 1)[0] for pair in geneinfo.split("|") if pair]
