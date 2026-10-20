#!/usr/bin/env bats
# Argument handling and dry-run plan of scripts/fetch_data.sh; no network access.

setup() {
	SCRIPT="${BATS_TEST_DIRNAME}/../../scripts/fetch_data.sh"
	DATA_DIR="${BATS_TEST_TMPDIR}/data"
}

@test "no arguments prints usage and exits 2" {
	run "${SCRIPT}"
	[ "$status" -eq 2 ]
	[[ "$output" == *"Usage:"* ]]
}

@test "unknown stage is rejected" {
	run "${SCRIPT}" --dry-run "${DATA_DIR}" nosuchstage
	[ "$status" -eq 2 ]
	[[ "$output" == *"unknown stage: nosuchstage"* ]]
}

@test "dry run lists the ClinVar files over FTP and downloads nothing" {
	run "${SCRIPT}" --dry-run "${DATA_DIR}" clinvar
	[ "$status" -eq 0 ]
	[[ "$output" == *"ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar_20261011.vcf.gz ->"* ]]
	[[ "$output" == *"archive_2.0/2025/clinvar_20251013.vcf.gz ->"* ]]
	[ ! -e "${DATA_DIR}/provenance.tsv" ]
}

@test "release names can be overridden from the environment" {
	CLINVAR_NEW=clinvar_20261018 run "${SCRIPT}" --dry-run "${DATA_DIR}" clinvar
	[ "$status" -eq 0 ]
	[[ "$output" == *"clinvar_20261018.vcf.gz"* ]]
}

@test "dry run of the reference stage plans one file per chromosome plus md5sum.txt" {
	CHROMS="13 17" run "${SCRIPT}" --dry-run "${DATA_DIR}" reference
	[ "$status" -eq 0 ]
	[ "$(grep -c 'would fetch' <<<"$output")" -eq 3 ]
}

@test "a relative DATA_DIR is planned as an absolute path" {
	cd "${BATS_TEST_TMPDIR}"
	run "${SCRIPT}" --dry-run rel_data clinvar
	[ "$status" -eq 0 ]
	[[ "$output" == *"-> ${BATS_TEST_TMPDIR}/rel_data/clinvar/clinvar_20261011.vcf.gz"* ]] ||
		[[ "$output" == *"-> $(cd "${BATS_TEST_TMPDIR}" && pwd -P)/rel_data/clinvar/clinvar_20261011.vcf.gz"* ]]
}
