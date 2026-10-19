process CVNF_DIFF_REPORT {
    label 'process_single'
    label 'cvnf'

    input:
    path all_json
    path panel_json

    output:
    tuple path("clinvar_diff.report.md"), path("clinvar_diff.report.html"), emit: report
    path "versions.yml", emit: versions

    script:
    def panel_arg = panel_json.name != 'NO_PANEL' ? "--panel-json ${panel_json}" : ''
    """
    cvnf diff-report --all-json ${all_json} ${panel_arg} \\
        --markdown clinvar_diff.report.md --html clinvar_diff.report.html

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        cvnf: \$(cvnf --version | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    touch clinvar_diff.report.md clinvar_diff.report.html
    printf '"%s":\\n    cvnf: stub\\n' "${task.process}" > versions.yml
    """
}
