import pytest

from cvnf.clinvar import (
    REVIEW_STARS,
    Group,
    UnknownReviewStatusError,
    classify,
    gene_symbols,
    review_stars,
)

# Every CLNREVSTAT value in the 2025-10-13 and 2026-10-11 GRCh38 releases (bcftools query
# over both files, 2026-10-19) with the stars ClinVar documents for it.
OBSERVED = {
    "practice_guideline": 4,
    "reviewed_by_expert_panel": 3,
    "criteria_provided,_multiple_submitters,_no_conflicts": 2,
    "criteria_provided,_conflicting_classifications": 1,
    "criteria_provided,_single_submitter": 1,
    "no_assertion_criteria_provided": 0,
    "no_classification_provided": 0,
    "no_classification_for_the_single_variant": 0,
    "no_classifications_from_unflagged_records": 0,
    ".": 0,
}


@pytest.mark.parametrize(("status", "stars"), OBSERVED.items())
def test_review_stars_for_observed_statuses(status: str, stars: int) -> None:
    assert review_stars(status) == stars


def test_unknown_review_status_raises() -> None:
    with pytest.raises(UnknownReviewStatusError):
        review_stars("criteria_provided,_new_wording")


def test_star_table_values_are_in_range() -> None:
    assert set(REVIEW_STARS.values()) <= {0, 1, 2, 3, 4}


@pytest.mark.parametrize(
    ("clnsig", "group", "low_pen", "risk"),
    [
        ("Pathogenic", Group.PLP, False, False),
        ("Likely_pathogenic", Group.PLP, False, False),
        ("Pathogenic/Likely_pathogenic", Group.PLP, False, False),
        ("Pathogenic|risk_factor", Group.PLP, False, False),
        ("Likely_pathogenic,_low_penetrance", Group.PLP, True, False),
        ("Pathogenic/Likely_pathogenic/Likely_risk_allele", Group.PLP, False, True),
        ("Uncertain_significance", Group.VUS, False, False),
        ("VUS-high", Group.VUS, False, False),
        ("Uncertain_significance/Uncertain_risk_allele", Group.VUS, False, True),
        ("Benign/Likely_benign|drug_response", Group.BLB, False, False),
        ("Conflicting_classifications_of_pathogenicity", Group.CONFLICTING, False, False),
        ("Conflicting_interpretations_of_pathogenicity", Group.CONFLICTING, False, False),
        ("Likely_risk_allele", Group.RISK, False, False),
        ("drug_response", Group.OTHER, False, False),
        ("Pathogenic/Benign", Group.MIXED, False, False),
        (".", Group.NONE, False, False),
    ],
)
def test_classify(clnsig: str, group: Group, low_pen: bool, risk: bool) -> None:
    result = classify(clnsig)
    assert result.group is group
    assert result.low_penetrance is low_pen
    assert result.risk_allele_component is risk


def test_gene_symbols_keeps_order() -> None:
    assert gene_symbols("BRCA1:672|NBR2:10230") == ["BRCA1", "NBR2"]
    assert gene_symbols(".") == []
