process CVNF_FILTER {
    tag "${meta.id}"
    label 'process_single'
    label 'cvnf'

    input:
    tuple val(meta), path(panel_vcf)

    output:
    tuple val(meta), path("${meta.id}.panel_variants.tsv"), emit: table
    path "versions.yml", emit: versions

    script:
    def low_pen = params.include_low_penetrance ? '' : '--exclude-low-penetrance'
    """
    cvnf filter --sample ${meta.id} --vcf ${panel_vcf} --out ${meta.id}.panel_variants.tsv \\
        --min-stars ${params.min_stars} --max-af ${params.max_af} ${low_pen}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        cvnf: \$(cvnf --version | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    touch ${meta.id}.panel_variants.tsv
    printf '"%s":\\n    cvnf: stub\\n' "${task.process}" > versions.yml
    """
}
