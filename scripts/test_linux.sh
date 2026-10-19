#!/usr/bin/env bash
# Run the test and test_diff profiles in a clean Debian 12 container with one Nextflow
# release, using the files git tracks in this checkout (committed or not).
#
# Usage: scripts/test_linux.sh NXF_VER
set -euo pipefail

if [[ $# -ne 1 ]]; then
	echo "Usage: $(basename "$0") NXF_VER   (for example 25.04.0)" >&2
	exit 2
fi
readonly nxf_ver=$1
readonly image="cvnf-linux-test:${nxf_ver}"
repo=$(git rev-parse --show-toplevel)

docker build -q -f "${repo}/tests/linux/Dockerfile" --build-arg "NXF_VER=${nxf_ver}" \
	-t "${image}" "${repo}/tests/linux" >/dev/null

# COPYFILE_DISABLE and --no-xattrs keep macOS metadata out of the archive.
git -C "${repo}" ls-files -co --exclude-standard -z |
	COPYFILE_DISABLE=1 tar --no-xattrs -C "${repo}" --null -T - -cf - |
	docker run --rm -i "${image}" bash -euo pipefail -c '
		mkdir pipeline && tar -x -C pipeline && cd pipeline
		nextflow -version | grep -m1 version
		nextflow run . -profile test -ansi-log false --outdir results > test.log 2>&1 || { tail -n 30 test.log; exit 1; }
		tail -n 2 test.log
		grep -h "WARN" test.log || echo "no warnings"
		nextflow run . -profile test_diff -ansi-log false --outdir results_diff > diff.log 2>&1 || { tail -n 30 diff.log; exit 1; }
		tail -n 2 diff.log
		python3 -c "import json; r = json.load(open(\"results/report/SYNTH01.report.json\")); print(\"SYNTH01 reportable:\", r[\"reportable\"])"
	'
