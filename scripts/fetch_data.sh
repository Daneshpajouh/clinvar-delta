#!/usr/bin/env bash
# Fetch the public datasets used by the real-data runs and record their provenance.
#
# Every file lands under DATA_DIR (never inside the repository). Each fetch appends one
# row to DATA_DIR/provenance.tsv: stage, url, local path, bytes, sha256, fetch time (UTC).
#
# Usage: scripts/fetch_data.sh [--dry-run] DATA_DIR STAGE [STAGE ...]
# Stages: giab clinvar reference panel gnomad
set -euo pipefail

readonly GIAB_BASE="https://giab.s3.amazonaws.com/release/AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/GRCh38"
readonly GIAB_VCF="HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz"
readonly CLINVAR_FTP="ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38"
readonly CLINVAR_NEW="${CLINVAR_NEW:-clinvar_20261011}"
readonly CLINVAR_OLD="${CLINVAR_OLD:-clinvar_20251013}"
readonly UCSC_BASE="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes"
readonly ENSEMBL_REST="https://rest.ensembl.org"
readonly ACMG_PAGE="https://www.ncbi.nlm.nih.gov/clinvar/docs/acmg/"
readonly GNOMAD_BASE="https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes"
readonly CHROMS="${CHROMS:-1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 X}"
# The panel stage runs the checkout's cvnf, so nothing needs to be installed first.
CVNF="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/bin/cvnf"
readonly CVNF

DRY_RUN=0

usage() {
	echo "Usage: $(basename "$0") [--dry-run] DATA_DIR STAGE [STAGE ...]" >&2
	echo "Stages: giab clinvar reference panel gnomad" >&2
}

log() {
	printf '%s fetch_data %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2
}

sha256_of() {
	if command -v sha256sum >/dev/null 2>&1; then
		sha256sum "$1" | cut -d' ' -f1
	else
		shasum -a 256 "$1" | cut -d' ' -f1
	fi
}

bytes_of() {
	wc -c <"$1" | tr -d ' '
}

record() {
	# record STAGE URL PATH
	local stage=$1 url=$2 path=$3
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$stage" "$url" "$path" "$(bytes_of "$path")" \
		"$(sha256_of "$path")" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"${DATA_DIR}/provenance.tsv"
}

fetch() {
	# fetch STAGE URL DEST: download once, atomically, with timeouts and retries.
	local stage=$1 url=$2 dest=$3
	if [[ ${DRY_RUN} -eq 1 ]]; then
		echo "would fetch ${url} -> ${dest}"
		return 0
	fi
	if [[ -s ${dest} ]]; then
		log "present, skipping ${dest}"
		return 0
	fi
	mkdir -p "$(dirname "${dest}")"
	log "fetching ${url}"
	# -4: the NCBI FTP data channel stalls over IPv6 on this network (see docs/operations).
	curl -4 -fsSL --retry 3 --retry-delay 10 --connect-timeout 30 -m 3600 -o "${dest}.part" "${url}"
	mv "${dest}.part" "${dest}"
	record "${stage}" "${url}" "${dest}"
}

check_md5() {
	# check_md5 FILE MD5FILE: NCBI .md5 files hold "<md5>  <remote path>".
	local file=$1 md5file=$2 expected actual
	[[ ${DRY_RUN} -eq 1 ]] && return 0
	expected=$(cut -d' ' -f1 "${md5file}")
	if command -v md5sum >/dev/null 2>&1; then
		actual=$(md5sum "${file}" | cut -d' ' -f1)
	else
		actual=$(md5 -q "${file}")
	fi
	if [[ ${expected} != "${actual}" ]]; then
		log "MD5 mismatch for ${file}: expected ${expected}, got ${actual}"
		return 1
	fi
	log "md5 ok ${file}"
}

stage_giab() {
	fetch giab "${GIAB_BASE}/${GIAB_VCF}" "${DATA_DIR}/giab/${GIAB_VCF}"
	fetch giab "${GIAB_BASE}/${GIAB_VCF}.tbi" "${DATA_DIR}/giab/${GIAB_VCF}.tbi"
}

stage_clinvar() {
	local release path
	for release in "${CLINVAR_NEW}" "${CLINVAR_OLD}"; do
		if [[ ${release} == "${CLINVAR_NEW}" ]]; then
			path="${CLINVAR_FTP}"
		else
			path="${CLINVAR_FTP}/archive_2.0/${release:8:4}"
		fi
		fetch clinvar "${path}/${release}.vcf.gz.md5" "${DATA_DIR}/clinvar/${release}.vcf.gz.md5"
		fetch clinvar "${path}/${release}.vcf.gz" "${DATA_DIR}/clinvar/${release}.vcf.gz"
		fetch clinvar "${path}/${release}.vcf.gz.tbi" "${DATA_DIR}/clinvar/${release}.vcf.gz.tbi"
		check_md5 "${DATA_DIR}/clinvar/${release}.vcf.gz" "${DATA_DIR}/clinvar/${release}.vcf.gz.md5"
	done
}

stage_reference() {
	local chrom out="${DATA_DIR}/reference/hg38_selected.fa.gz"
	fetch reference "${UCSC_BASE}/md5sum.txt" "${DATA_DIR}/reference/ucsc/md5sum.txt"
	for chrom in ${CHROMS}; do
		fetch reference "${UCSC_BASE}/chr${chrom}.fa.gz" "${DATA_DIR}/reference/ucsc/chr${chrom}.fa.gz"
	done
	[[ ${DRY_RUN} -eq 1 ]] && return 0
	if [[ ! -s ${out} ]]; then
		log "building bgzipped reference ${out}"
		for chrom in ${CHROMS}; do
			gzip -dc "${DATA_DIR}/reference/ucsc/chr${chrom}.fa.gz"
		done | bgzip -@ 4 -c >"${out}.part"
		mv "${out}.part" "${out}"
		samtools faidx "${out}"
	fi
}

stage_panel() {
	# The ACMG page is saved as-is; gene symbols and coordinates are parsed by cvnf.
	fetch panel "${ACMG_PAGE}" "${DATA_DIR}/panel/acmg_sf_page.html"
	fetch panel "${ENSEMBL_REST}/info/data/?content-type=application/json" "${DATA_DIR}/panel/ensembl_info_data.json"
	if [[ ${DRY_RUN} -eq 1 ]]; then
		echo "would POST gene symbols to ${ENSEMBL_REST}/lookup/symbol/homo_sapiens"
		return 0
	fi
	local symbols="${DATA_DIR}/panel/acmg_sf_genes.txt"
	local lookup="${DATA_DIR}/panel/ensembl_lookup.json"
	"${CVNF}" panel-symbols --html "${DATA_DIR}/panel/acmg_sf_page.html" --out "${symbols}"
	if [[ ! -s ${lookup} ]]; then
		"${CVNF}" panel-request-body --symbols "${symbols}" |
			curl -fsS --retry 3 -m 120 -H 'Content-Type: application/json' -H 'Accept: application/json' \
				-X POST --data @- "${ENSEMBL_REST}/lookup/symbol/homo_sapiens" -o "${lookup}"
		record panel "${ENSEMBL_REST}/lookup/symbol/homo_sapiens (POST)" "${lookup}"
	fi
	"${CVNF}" panel-bed --lookup "${lookup}" --symbols "${symbols}" --out "${DATA_DIR}/panel/acmg_sf_v3.2.grch38.bed"
}

stage_gnomad() {
	local bed="${DATA_DIR}/panel/acmg_sf_v3.2.grch38.bed" chrom work out
	work="${DATA_DIR}/gnomad/index_cache"
	out="${DATA_DIR}/gnomad/gnomad.genomes.v4.1.acmg_sf_panel.vcf.gz"
	if [[ ${DRY_RUN} -eq 1 ]]; then
		echo "would region-fetch ${GNOMAD_BASE}/gnomad.genomes.v4.1.sites.chrN.vcf.bgz for ${bed}"
		return 0
	fi
	[[ -s ${out} ]] && {
		log "present, skipping ${out}"
		return 0
	}
	mkdir -p "${work}"
	cut -f1 "${bed}" | sort -u >"${work}/chroms.txt"
	while IFS= read -r chrom; do
		log "region fetch gnomAD ${chrom}"
		# htslib caches the remote .tbi in the working directory, so run from the cache dir.
		(cd "${work}" && bcftools view --no-version -R "${bed}" \
			"${GNOMAD_BASE}/gnomad.genomes.v4.1.sites.${chrom}.vcf.bgz" |
			bcftools annotate --no-version -x '^INFO/AC,INFO/AN,INFO/AF,INFO/nhomalt,INFO/AF_grpmax' \
				-O z -o "${work}/${chrom}.vcf.gz")
	done <"${work}/chroms.txt"
	bcftools concat --no-version -O z -o "${out}.part" "${work}"/chr*.vcf.gz
	mv "${out}.part" "${out}"
	tabix -p vcf "${out}"
	record gnomad "${GNOMAD_BASE}/gnomad.genomes.v4.1.sites.chrN.vcf.bgz (region fetch)" "${out}"
}

main() {
	if [[ ${1:-} == "--dry-run" ]]; then
		DRY_RUN=1
		shift
	fi
	if [[ $# -lt 2 ]]; then
		usage
		return 2
	fi
	DATA_DIR=$1
	shift
	mkdir -p "${DATA_DIR}"
	# Absolute, because the gnomAD stage changes directory before it uses these paths.
	DATA_DIR=$(cd "${DATA_DIR}" && pwd)
	local stage
	for stage in "$@"; do
		case ${stage} in
		giab | clinvar | reference | panel | gnomad) "stage_${stage}" ;;
		*)
			echo "unknown stage: ${stage}" >&2
			usage
			return 2
			;;
		esac
	done
}

main "$@"
