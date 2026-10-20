# Test report: v1.0.1, 2026-10-19

Machine for the checks below: Apple M3 Ultra, macOS 27.0.1, Nextflow 26.10.2, Python
3.13.9, bcftools 1.23.1 (Homebrew), Java 27. Tools from the checkout unless a row names a container.

| Check | Command | Result |
|---|---|---|
| unit tests | `pytest tests/unit --cov=cvnf` | 121 passed in 0.38 s; coverage 88% of 994 statements |
| pipeline tests | `pytest -m pipeline tests/pipeline` | 10 passed in 43.3 s |
| numeric options | `nextflow run . -profile test --max_cpus 2 --min_stars 1 --max_af 0.01` | 19 tasks succeeded |
| bad numeric options | `--max_cpus abc`, `--max_cpus 0` | both refused by validation (string; below minimum 1) |
| shellcheck | `shellcheck scripts/*.sh` | no findings |
| bats | `bats tests/bats` | 5 passed |
| nf-test | `nf-test test tests/nf-test` | 14 passed in 62.9 s (nf-test 0.9.5, at 6fe8ffd) |
| ruff, mypy, docs build | `make lint typecheck docs` | ruff no findings, 20 files formatted; mypy no issues in 17 files; `mkdocs build --strict` built (at 6fe8ffd) |
| clean Debian, minimum Nextflow | `scripts/test_linux.sh 26.04.0` | test and test_diff profiles succeeded with no warnings; SYNTH01 6 reportable; 24 s |
| clean Debian, current Nextflow | `scripts/test_linux.sh 26.10.2` | test and test_diff profiles succeeded with no warnings; SYNTH01 6 reportable; 16 s |
| Docker test profiles | `make image`, then `-profile test,docker` and `-profile test_diff,docker` | 19 and 7 tasks succeeded (Docker Desktop, image `clinvar-delta:1.0.1`) |
| Linux unit check | `python:3.13-slim` container: ruff, mypy, pytest tests/unit | ruff no findings; mypy no issues in 17 files; 121 passed |
| real diff run | see results.md | rerun at 7b6f361, 14:34 Pacific, 1 min 20 s: whole-release counts unchanged; panel column moved with the 1.0.1 gene rules |

The real annotate run in results.md is from v1.0.0. v1.0.1 takes review stars from
CLNREVSTAT when present, which could move the P/LP by stars line, so the run was repeated at
6fe8ffd (14:39 Pacific, 29.4 s, 13 tasks): the report, gene summary and panel variant table
are byte-identical to v1.0.0 and P/LP by stars is still 0 at every level. Only the validation
JSON differs: it no longer carries a `header_contigs` count.

## v1.0.0, 2026-10-19

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
| Linux unit check | `python:3.13-slim` container (Linux aarch64): ruff, mypy, pytest tests/unit | 90 passed |
| real annotate run | see results.md | 12 tasks succeeded, 30.9 s |
| real diff run | see results.md | 6 tasks succeeded, 1 min 20 s |

## Deferred, with reason (v1.0.0 and v1.0.1)

- Slurm: no cluster was available. The Slurm profile is untested; the sacct parser is tested
  only on hand-written files in the documented format.
- Apptainer: not available on macOS; `containers/apptainer.def` has not been built.
- GitHub Actions: CI passes on main at `374f9c9`; the release workflow published v1.0.1
  and the tools image.
- nf-core compliance: `nf-core pipelines lint --dir .` (nf-core/tools 4.1.0) gives 110
  passed, 13 warnings, 40 failed, 4 ignored. The failures are files and settings of the
  nf-core template that this pipeline does not use (logos, e-mail templates,
  CODE_OF_CONDUCT.md, `nf-core/` naming, nf-core institutional configs, sharded nf-test
  workflows) and `params.max_cpus|memory|time`, which nf-core has replaced with
  `resourceLimits` alone; here those params set `resourceLimits`. The pipeline follows the
  nf-core conventions it uses (nf-schema validation, `modules/local/<name>/main.nf`,
  `versions.yml` per process, stub blocks, resource labels) but does not claim nf-core
  compliance.
- Subsample calibration (1, 5, 20 percent) and an IPR-shaped export: ROADMAP.md.
