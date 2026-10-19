process CVNF_PANEL_PAD {
    tag "${bed.name}"
    label 'process_single'
    label 'cvnf'

    input:
    path bed
    val pad

    output:
    path "panel.padded.bed", emit: bed
    path "versions.yml", emit: versions

    script:
    """
    cvnf panel-pad --bed ${bed} --pad ${pad} --out panel.padded.bed

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        cvnf: \$(cvnf --version | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    touch panel.padded.bed
    printf '"%s":\\n    cvnf: stub\\n' "${task.process}" > versions.yml
    """
}
