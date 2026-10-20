// Rename ClinVar contigs to the reference style (1 -> chr1, MT -> chrM), keep only the
// fields the report needs, normalise against the same reference as the sample, and
// write a position-sorted table for cvnf.
process CLINVAR_PREPARE {
    tag "${clinvar.simpleName}"
    label 'process_medium'
    label 'bcftools'

    input:
    tuple path(clinvar), path(clinvar_tbi)
    tuple path(fasta), path(fai), path(gzi)
    path regions

    output:
    path "clinvar.query.tsv.gz", emit: tsv
    path "clinvar.norm_warnings.txt", emit: warnings
    path "versions.yml", emit: versions

    script:
    def restrict = regions.name != 'NO_REGIONS' ? "| bcftools view --no-version -T ${regions} -Ou" : ''
    """
    bcftools index -s ${clinvar} | cut -f1 > clinvar_contigs.txt
    cut -f1 ${fai} > ref_contigs.txt
    awk -v OFS='\\t' 'NR == FNR { ref[\$1] = 1; next }
        { t = (\$1 == "MT") ? "chrM" : (\$1 ~ /^chr/ ? \$1 : "chr" \$1); if (t in ref) print \$1, t }' \\
        ref_contigs.txt clinvar_contigs.txt > rename.tsv
    cut -f2 rename.tsv | paste -sd, - > keep_targets.txt
    if [[ ! -s rename.tsv ]]; then
        echo "no ClinVar contig maps onto a reference contig; the reference must use chr-prefixed GRCh38 names" >&2
        exit 1
    fi

    bcftools annotate --no-version --rename-chrs rename.tsv \\
        -x '^INFO/CLNSIG,INFO/CLNREVSTAT,INFO/GENEINFO' -Ou ${clinvar} \\
        | bcftools view --no-version -t "\$(cat keep_targets.txt)" -Ou ${restrict} \\
        | bcftools norm --no-version -m -any -f ${fasta} -c w -Ou 2> clinvar.norm_warnings.txt \\
        | bcftools query -f '%CHROM\\t%POS\\t%REF\\t%ALT\\t%ID\\t%INFO/CLNSIG\\t%INFO/CLNREVSTAT\\t%INFO/GENEINFO\\n' \\
        | gzip -nc > clinvar.query.tsv.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        bcftools: \$(bcftools --version | head -n1 | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    echo -n | gzip -nc > clinvar.query.tsv.gz
    touch clinvar.norm_warnings.txt
    printf '"%s":\\n    bcftools: stub\\n' "${task.process}" > versions.yml
    """
}
