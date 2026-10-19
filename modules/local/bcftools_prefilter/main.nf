// Restricting to padded panel regions before normalisation keeps indels whose
// left-aligned position moves into a gene; the exact panel is applied after annotation.
process BCFTOOLS_PREFILTER {
    tag "${meta.id}"
    label 'process_low'
    label 'bcftools'

    input:
    tuple val(meta), path(vcf), path(tbi)
    path regions

    output:
    tuple val(meta), path("${meta.id}.prefilter.vcf.gz"), path("${meta.id}.prefilter.vcf.gz.tbi"), emit: vcf
    path "versions.yml", emit: versions

    script:
    """
    bcftools view --no-version --threads ${task.cpus} -R ${regions} -Oz -o ${meta.id}.prefilter.vcf.gz ${vcf}
    bcftools index -t ${meta.id}.prefilter.vcf.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        bcftools: \$(bcftools --version | head -n1 | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    touch ${meta.id}.prefilter.vcf.gz ${meta.id}.prefilter.vcf.gz.tbi
    printf '"%s":\\n    bcftools: stub\\n' "${task.process}" > versions.yml
    """
}
