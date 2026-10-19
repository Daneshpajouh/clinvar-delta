# Operations notes

Failures hit while building v1.0.0 and v1.0.1 on 2026-10-19, in the order they happened,
with the fix that is now in the code.

## 1. NCBI FTP listing hung for two minutes

`curl --list-only ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/` connected, logged
in, then hung until the 120 s timeout; `rsync://ftp.ncbi.nlm.nih.gov` timed out at connect.
`curl -v` showed the control connection over IPv6 working and the passive data connection
never opening. Forcing IPv4 (`curl -4`) listed the folder at once. `scripts/fetch_data.sh`
uses `-4` for every fetch, with a comment pointing here. The HTTPS route on the same host
was not used because its robots.txt disallows all agents (data_sources.md).

## 2. `cvnf` failed under Python 3.9

The first test run failed in CVNF_VALIDATE with `ImportError: cannot import name 'StrEnum'`.
Nextflow ran with a PATH where `python3` was Xcode's 3.9, and `enum.StrEnum` needs 3.11.
`bin/cvnf` now stops with "cvnf needs Python 3.11 or newer; <path> is <version>" instead of
a traceback. Running with Docker avoids it entirely.

## 3. bcftools annotate could not read a VCF source on a stream

`bcftools annotate -a gnomad.vcf.gz` placed after a pipe failed with
`Could not retrieve index file for '-'`. With a VCF as the annotation source, bcftools 1.23
needs an indexed input file; tab and BED sources stream without it. The gnomAD pass now
reads the indexed normalised VCF directly and the ClinVar table and BED passes follow it
in the pipe.

## 4. One of two samples silently not annotated

After removing a `.first()` that Nextflow had warned was useless, the test run completed
with `[SUCCESS]`, but only SYNTH01 had a report. The ClinVar annotation channel came from
`combine` on two value channels, which returns a queue channel; BCFTOOLS_ANNOTATE consumed
its single item with the first sample and never ran for HG002. Nextflow reported no error.
`pytest -m pipeline` caught it because it opens both samples' reports. The channel is now
collected and checked to hold one item, the workflow fails if any input sample has no
report, and the pipeline tests assert on every sample.

Lesson kept: a pipeline test must check outputs for every input, not only that the run
succeeded.

## 5. Stale tools image after a code change

The real diff run used the `ghcr.io/daneshpajouh/clinvar-variant-nf:1.0.0` image built
before a change to `cvnf diff-report`, so the report still had the old gene ordering.
Nextflow's cache key includes the image name, not its content, so `-resume` would also
have reused stale results. The image was rebuilt and the diff rerun without `-resume`.
`make image` rebuilds it; during development, use `-profile test` (tools from the
checkout) or rebuild before any run whose numbers are kept.

## 6. No task metrics on macOS without containers

Runs with the `standard` profile on macOS print "Task runtime metrics are not reported when
using macOS without a container engine", and the trace has no `%cpu` or `peak_rss`. All
profiling numbers in the docs come from `-profile docker` runs.

## 7. nf-schema 2.8.0 could not be installed by Nextflow 25.04 (v1.0.1)

A verification run of v1.0.0 in a clean Linux container with Nextflow 25.04.6 stopped with
`Plugin nf-schema with version @2.8.0 does not exist in the repository`. Releases after
2.5.1 are published only to the new Nextflow plugin registry, which 25.04 does not read;
the development machine had 2.8.0 in its local plugin cache, so every local run passed.
The first fix pinned 2.5.1, the newest release in the legacy `plugins.json`, whose own
minimum is Nextflow 25.04.0; section 10 replaced it before release. `scripts/test_linux.sh`
runs the test profiles from an empty plugin cache with a given Nextflow release.

## 8. `onComplete:` section rejected by Nextflow 25.04 (v1.0.1)

The first clean-container run with 25.04.0 then failed at compile time with
`Unknown execution scope 'onComplete:'`. The entry workflow now registers
`workflow.onComplete { writeRunSummary() }`. Inside that closure `workflow` and `params`
resolved to the handler's delegate and were null (`Cannot get property 'success' on null
object`), so all the work, including the final log line, is in the script function.

## 9. Tasks fail without `ps` on a minimal Debian image

With `procps` removed, every task fails with `Command 'ps' required by nextflow to collect
task metrics cannot be found`. The tools image installs `procps`; the README lists it for
runs without containers.

## 10. Numeric options rejected by nf-schema 2.5.1 on Nextflow 26.10 (v1.0.1)

With the 2.5.1 pin, `--max_cpus 8`, `--min_stars 1` and `--max_af 0.01` on Nextflow 26.10.2
stopped with `Value is [string] but should be [integer]`; 2.5.1 has no lenient mode. Making
the schema accept strings would have meant converting every numeric parameter by hand in
the workflow. v1.0.1 instead returns to nf-schema 2.8.0, which reads these options as
numbers, and raises the minimum to Nextflow 26.04.0: 2.8.0 is served only by the Nextflow
plugin registry, which Nextflow reads from 25.10.0 ("Migrating to 25.10", Seqera Docs,
docs.seqera.io/nextflow/migrations/25-10), and its own manifest declares
`Plugin-Requires: >=26.04.0`. On 26.10.2 the three options pass, `--max_cpus abc` is still
rejected as a string and `--max_cpus 0` as below the minimum of 1.
