process CVNF_VALIDATE {
    tag "${meta.id}"
    label 'process_single'
    label 'cvnf'

    input:
    tuple val(meta), path(vcf), path(tbi)
    tuple path(fasta), path(fai), path(gzi)
    path panel

    output:
    tuple val(meta), path("${meta.id}.validation.json"), emit: report
    path "versions.yml", emit: versions

    script:
    """
    cvnf validate --sample ${meta.id} --vcf ${vcf} --fai ${fai} --panel ${panel} \\
        --out ${meta.id}.validation.json

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        cvnf: \$(cvnf --version | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    echo '{"problems": []}' > ${meta.id}.validation.json
    printf '"%s":\\n    cvnf: stub\\n' "${task.process}" > versions.yml
    """
}
