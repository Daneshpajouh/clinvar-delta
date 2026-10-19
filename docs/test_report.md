# Test report: v1.0.0, 2026-10-19

Machine: Apple M-series Mac, macOS, Docker Desktop with Docker 29.8; Nextflow 26.10.2;
nf-test 0.9.5; Python 3.13.9; bcftools 1.23.1 (Homebrew and BioContainers).

| Check | Command | Result |
|---|---|---|
| ruff lint | `ruff check src tests scripts bin/cvnf` | all checks passed |
| ruff format | `ruff format --check src tests scripts` | 20 files already formatted |
| mypy (strict) | `mypy` | no issues in 17 source files |
| unit tests | `pytest tests/unit --cov=cvnf` | 90 passed in 0.28 s; coverage 88% of 942 statements |
| pipeline tests | `pytest -m pipeline tests/pipeline` | 9 passed in 26.2 s |
| nf-test | `nf-test test tests/nf-test` | 14 passed in 63.4 s (11 module, 3 pipeline including a stub run) |
| shellcheck | `shellcheck scripts/*.sh` | no findings |
| bats | `bats tests/bats` | 5 passed |
| docs build | `mkdocs build --strict` | built, no warnings |
| Docker test profiles | `make image`, then `nextflow run . -profile test,docker` and `-profile test_diff,docker` | 18 tasks in 12.6 s; 6 tasks in 8.8 s |
| Linux unit check | `python:3.13-slim` container (Linux aarch64): ruff, mypy, pytest tests/unit | passed (89 tests, before the last gzip test was added) |
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
