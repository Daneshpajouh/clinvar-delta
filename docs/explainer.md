# ClinVar, review stars and reclassification

This page is for readers who do not work with genetic variant data.

## What ClinVar is

Everyone carries millions of small differences from the human reference genome. Almost all
are harmless. A few, in specific genes, raise the risk of disease: a change in BRCA1 can
raise breast and ovarian cancer risk; a change in LDLR can cause very high cholesterol from
childhood.

ClinVar is a free public database run by the US National Center for Biotechnology
Information (NCBI). Clinical laboratories, research groups and expert panels submit their
interpretation of a variant, and ClinVar publishes them side by side with a combined
classification. The main classifications are pathogenic, likely pathogenic, uncertain
significance (VUS), likely benign and benign. The 2026-10-11 release used here has
4,594,764 records.

## Why review stars matter

Not every classification carries the same weight. ClinVar gives each record zero to four
stars for how it was reviewed:

| Stars | Meaning |
|---|---|
| 4 | practice guideline |
| 3 | reviewed by an expert panel |
| 2 | several submitters gave evidence and agree |
| 1 | one submitter gave evidence, or several disagree |
| 0 | no evidence given, or no classification |

A "pathogenic" call with zero stars may be a single old submission with no supporting
evidence. This pipeline only reports pathogenic or likely pathogenic variants with at least
one star by default, and shows the star level next to every result so a reader can judge it.

## What a reclassification means for a patient

Classifications change as evidence accumulates: more families are tested, functional
studies are published, population databases grow. Between October 2025 and October 2026,
1,350 variants went from uncertain to pathogenic or likely pathogenic, and 685 went the
other way. 19,907 uncertain variants became "conflicting", meaning submitters now disagree.

For a patient, a VUS that becomes likely pathogenic can change screening or treatment
for them and their relatives; a pathogenic result that is downgraded can mean an
intervention was based on evidence that no longer holds. Labs therefore re-check old
reports against new ClinVar releases. The diff mode of this pipeline produces that list.

## Assertion changes and annotation changes

Not every difference between two releases is a new opinion. Sometimes ClinVar re-maps a
variant to a corrected position, updates the gene name, or rewords a review status. The
pipeline labels these `annotation_only` and keeps them apart from changes that come from
submitters or expert panels (`reclassified`, `review_changed`, `term_changed`). In the real
comparison, 4,427 records changed only in annotation, against 221,927 assertion changes.

## Population frequency

gnomAD counts how often each variant appears in about 76,000 sequenced genomes (v4.1).
A variant carried by more than 1% of people is unlikely to cause a rare, severe disease,
so the pipeline excludes P/LP variants above a configurable frequency (default 1%).

## What this pipeline does not do

It does not diagnose anyone. It does not interpret variants that are not in ClinVar, check
whether a variant fits the patient's condition, or replace a genetic counsellor. Its
reports say so.
