// One row per ClinVar record, sorted by Variation ID for the streaming merge in cvnf diff.
process CLINVAR_QUERY_SORTED {
    tag "${label}"
    label 'process_medium'
    label 'bcftools'

    input:
    tuple val(role), val(label), path(clinvar), path(clinvar_tbi)

    output:
    tuple val(role), val(label), path("${label}.by_id.tsv.gz"), emit: tsv
    path "versions.yml", emit: versions

    script:
    """
    bcftools query -f '%ID\\t%CHROM\\t%POS\\t%REF\\t%ALT\\t%INFO/CLNSIG\\t%INFO/CLNREVSTAT\\t%INFO/GENEINFO\\n' ${clinvar} \\
        | LC_ALL=C sort -t "\$(printf '\\t')" -k1,1n \\
        | gzip -c > ${label}.by_id.tsv.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        bcftools: \$(bcftools --version | head -n1 | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    echo -n | gzip -c > ${label}.by_id.tsv.gz
    printf '"%s":\\n    bcftools: stub\\n' "${task.process}" > versions.yml
    """
}
