# Requested versus used resources

Trace: execution_trace.txt. 12 tasks in 12 processes.

mem used = peak RSS of the largest task / requested memory; time used = longest realtime / requested time; CPU eff = %cpu / (100 x cpus), averaged over tasks.

## Per process

| process | tasks | cpus req | CPU eff | mem req | peak RSS | mem used | time req | max realtime | time used | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| ANNOTATE:BCFTOOLS_ANNOTATE | 1 | 4.0 | 143.5% | 4.0 GB | 63.1 MB | 1.5% | 7200.0s | 3.0s | 0.0% | memory waste, CPU above request |
| ANNOTATE:BCFTOOLS_NORM | 1 | 4.0 | 272.6% | 4.0 GB | 27.0 MB | 0.7% | 7200.0s | 1.0s | 0.0% | memory waste, CPU above request |
| ANNOTATE:BCFTOOLS_PREFILTER | 1 | 2.0 | 305.3% | 2.0 GB | 47.3 MB | 2.3% | 3600.0s | 1.0s | 0.0% | memory waste, CPU above request |
| ANNOTATE:CLINVAR_PREPARE | 1 | 4.0 | 53.1% | 4.0 GB | 97.9 MB | 2.4% | 7200.0s | 16.0s | 0.2% | memory waste |
| ANNOTATE:CVNF_CLINVAR_TABLE | 1 | 1.0 | 74.8% | 1.0 GB | 22.9 MB | 2.2% | 1800.0s | 1.6s | 0.1% | memory waste |
| ANNOTATE:CVNF_FILTER | 1 | 1.0 | 93.2% | 1.0 GB | 20.1 MB | 2.0% | 1800.0s | 0.2s | 0.0% | memory waste |
| ANNOTATE:CVNF_PANEL_PAD | 1 | 1.0 | 88.9% | 1.0 GB | 18.2 MB | 1.8% | 1800.0s | 0.1s | 0.0% | memory waste |
| ANNOTATE:CVNF_REPORT | 1 | 1.0 | 97.5% | 1.0 GB | 17.3 MB | 1.7% | 1800.0s | 0.1s | 0.0% | memory waste |
| ANNOTATE:CVNF_VALIDATE | 1 | 1.0 | 88.0% | 1.0 GB | 11.5 MB | 1.1% | 1800.0s | 0.1s | 0.0% | memory waste |
| ANNOTATE:TABIX_CLINVAR | 1 | 1.0 | 92.9% | 1.0 GB | 12.2 MB | 1.2% | 1800.0s | 0.0s | 0.0% | memory waste |
| ANNOTATE:TABIX_PANEL | 1 | 1.0 | 102.6% | 1.0 GB | 6.4 MB | 0.6% | 1800.0s | 0.0s | 0.0% | memory waste |
| CVNF_MANIFEST | 1 | 1.0 | 30.0% | 1.0 GB | 24.3 MB | 2.4% | 1800.0s | 6.0s | 0.3% | memory waste |
