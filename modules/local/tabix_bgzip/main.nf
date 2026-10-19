// bgzip + tabix for a tab-delimited table or a BED file. preset is 'bed' or 'tab'.
process TABIX_BGZIP {
    tag "${input.name}"
    label 'process_single'
    label 'bcftools'

    input:
    tuple path(input), val(preset)

    output:
    tuple path("${input.name}.gz"), path("${input.name}.gz.tbi"), emit: indexed
    path "versions.yml", emit: versions

    script:
    def index_args = preset == 'bed' ? '-p bed' : '-s1 -b2 -e2'
    """
    bgzip -c ${input} > ${input.name}.gz
    tabix ${index_args} ${input.name}.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        tabix: \$(tabix --version | head -n1 | sed 's/.* //')
    END_VERSIONS
    """

    stub:
    """
    touch ${input.name}.gz ${input.name}.gz.tbi
    printf '"%s":\\n    tabix: stub\\n' "${task.process}" > versions.yml
    """
}
