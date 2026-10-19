process CVNF_REPORT {
    tag "${meta.id}"
    label 'process_single'
    label 'cvnf'

    input:
    tuple val(meta), path(table)
    path panel

    output:
    tuple val(meta), path("${meta.id}.gene_summary.tsv"), emit: summary
    tuple val(meta), path("${meta.id}.report.json"), emit: json
    tuple val(meta), path("${meta.id}.report.md"), path("${meta.id}.report.html"), emit: report
    path "versions.yml", emit: versions

    script:
    """
    cvnf report --sample ${meta.id} --table ${table} --panel ${panel} \\
        --min-stars ${params.min_stars} --max-af ${params.max_af} \\
        --summary ${meta.id}.gene_summary.tsv --json ${meta.id}.report.json \\
        --markdown ${meta.id}.report.md --html ${meta.id}.report.html

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        cvnf: \$(cvnf --version | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    touch ${meta.id}.gene_summary.tsv ${meta.id}.report.json ${meta.id}.report.md ${meta.id}.report.html
    printf '"%s":\\n    cvnf: stub\\n' "${task.process}" > versions.yml
    """
}
