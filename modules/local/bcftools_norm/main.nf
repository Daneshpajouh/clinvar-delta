process BCFTOOLS_NORM {
    tag "${meta.id}"
    label 'process_medium'
    label 'bcftools'

    input:
    tuple val(meta), path(vcf), path(tbi)
    tuple path(fasta), path(fai), path(gzi)

    output:
    tuple val(meta), path("${meta.id}.norm.vcf.gz"), path("${meta.id}.norm.vcf.gz.tbi"), emit: vcf
    tuple val(meta), path("${meta.id}.norm.log"), emit: log
    path "versions.yml", emit: versions

    script:
    // -m -any splits multiallelic records; -f left-aligns indels against the reference;
    // -c w reports REF mismatches instead of stopping, and they are counted in the log.
    """
    bcftools norm --no-version --threads ${task.cpus} -m -any -f ${fasta} -c w \\
        -Oz -o ${meta.id}.norm.vcf.gz ${vcf} 2> ${meta.id}.norm.log
    bcftools index -t ${meta.id}.norm.vcf.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        bcftools: \$(bcftools --version | head -n1 | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    touch ${meta.id}.norm.vcf.gz ${meta.id}.norm.vcf.gz.tbi ${meta.id}.norm.log
    printf '"%s":\\n    bcftools: stub\\n' "${task.process}" > versions.yml
    """
}
