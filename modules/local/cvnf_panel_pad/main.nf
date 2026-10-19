process CVNF_PANEL_PAD {
    tag "${bed.name}"
    label 'process_single'
    label 'cvnf'

    input:
    path bed
    val pad
    path cvnf_src, stageAs: 'cvnf_pkg/cvnf/*'

    output:
    path "panel.padded.bed", emit: bed
    path "versions.yml", emit: versions

    script:
    """
    PYTHONPATH=cvnf_pkg python3 -m cvnf panel-pad --bed ${bed} --pad ${pad} --out panel.padded.bed

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        cvnf: \$(PYTHONPATH=cvnf_pkg python3 -m cvnf --version | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    touch panel.padded.bed
    printf '"%s":\\n    cvnf: stub\\n' "${task.process}" > versions.yml
    """
}
