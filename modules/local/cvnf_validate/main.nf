process CVNF_VALIDATE {
    tag "${meta.id}"
    label 'process_single'
    label 'cvnf'

    input:
    tuple val(meta), path(vcf), path(tbi)
    tuple path(fasta), path(fai), path(gzi)
    path panel
    tuple path(gnomad), path(gnomad_tbi)
    path cvnf_src, stageAs: 'cvnf_pkg/cvnf/*'

    output:
    tuple val(meta), path("${meta.id}.validation.json"), emit: report
    path "versions.yml", emit: versions

    script:
    """
    PYTHONPATH=cvnf_pkg python3 -m cvnf validate --sample ${meta.id} --vcf ${vcf} --fai ${fai} --panel ${panel} \\
        --gnomad ${gnomad} --out ${meta.id}.validation.json

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        cvnf: \$(PYTHONPATH=cvnf_pkg python3 -m cvnf --version | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    echo '{"problems": []}' > ${meta.id}.validation.json
    printf '"%s":\\n    cvnf: stub\\n' "${task.process}" > versions.yml
    """
}
