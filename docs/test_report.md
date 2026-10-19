# Test report: v1.0.0, 2026-10-19

Machine: Apple M-series Mac, macOS, Docker Desktop with Docker 29.8; Nextflow 26.10.2;
nf-test 0.9.5; Python 3.13.9; bcftools 1.23.1 (Homebrew and BioContainers).

| Check | Command | Result |
|---|---|---|
| ruff lint | `ruff check src tests scripts bin/cvnf` | RESULT_RUFF |
| ruff format | `ruff format --check src tests scripts` | RESULT_FORMAT |
| mypy (strict) | `mypy` | RESULT_MYPY |
| unit tests | `pytest tests/unit --cov=cvnf` | RESULT_UNIT |
| pipeline tests | `pytest -m pipeline tests/pipeline` | RESULT_PIPELINE |
| nf-test | `nf-test test tests/nf-test` | RESULT_NFTEST |
| shellcheck | `shellcheck scripts/*.sh` | RESULT_SHELLCHECK |
| bats | `bats tests/bats` | RESULT_BATS |
| docs build | `mkdocs build --strict` | RESULT_MKDOCS |
| Docker test profile | `nextflow run . -profile test,docker` | 15 tasks succeeded, 13.5 s |
| real annotate run | see results.md | 12 tasks succeeded, 30.9 s |
| real diff run | see results.md | 6 tasks succeeded, 1 min 20 s |

## Deferred, with reason

- Slurm: no cluster was available. The Slurm profile is untested; the sacct parser is tested
  only on hand-written files in the documented format.
- Apptainer: not available on macOS; `containers/apptainer.def` has not been built.
- GitHub Actions: the workflows in `.github/workflows/` have not run, because the
  repository has not been pushed.
- `nf-core pipelines lint`: not run. This pipeline follows several nf-core conventions
  (nf-schema validation, `modules/local/<name>/main.nf`, `versions.yml` per process, stub
  blocks, resource labels, `resourceLimits`), but it is not built from the nf-core
  template and does not claim nf-core compliance.
- Subsample calibration (1, 5, 20 percent) and an IPR-shaped export: ROADMAP.md.
