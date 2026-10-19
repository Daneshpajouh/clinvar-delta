// Three annotation passes in one pipe: gnomAD allele frequency, ClinVar (with derived
// stars and group), and the panel gene name from the BED.
process BCFTOOLS_ANNOTATE {
    tag "${meta.id}"
    label 'process_medium'
    label 'bcftools'

    input:
    tuple val(meta), path(vcf), path(tbi)
    tuple path(clinvar_table), path(clinvar_tbi), path(clinvar_header)
    tuple path(gnomad), path(gnomad_tbi)
    tuple path(panel_bed), path(panel_tbi)

    output:
    tuple val(meta), path("${meta.id}.annotated.vcf.gz"), path("${meta.id}.annotated.vcf.gz.tbi"), emit: vcf
    tuple val(meta), path("${meta.id}.panel.vcf.gz"), emit: panel
    path "versions.yml", emit: versions

    script:
    """
    echo '##INFO=<ID=PANEL_GENE,Number=.,Type=String,Description="Gene panel interval(s) overlapping the variant">' > panel.header.txt

    # The gnomAD pass reads the indexed input file directly: bcftools 1.23 cannot pair a
    # VCF annotation source with a streamed input. Table and BED sources stream fine.
    bcftools annotate --no-version -a ${gnomad} -c 'INFO/gnomAD_AF:=INFO/AF' -Ou ${vcf} \\
        | bcftools annotate --no-version -a ${clinvar_table} -h ${clinvar_header} \\
            -c CHROM,POS,REF,ALT,CLNVID,CLNSIG,CLNREVSTAT,CLNSTARS,CLNGROUP,CLNGENE -Ou \\
        | bcftools annotate --no-version -a ${panel_bed} -h panel.header.txt \\
            -c CHROM,FROM,TO,PANEL_GENE --merge-logic PANEL_GENE:unique \\
            --threads ${task.cpus} -Oz -o ${meta.id}.annotated.vcf.gz
    bcftools index -t ${meta.id}.annotated.vcf.gz
    bcftools view --no-version -i 'INFO/PANEL_GENE!="."' -Oz -o ${meta.id}.panel.vcf.gz ${meta.id}.annotated.vcf.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        bcftools: \$(bcftools --version | head -n1 | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    touch ${meta.id}.annotated.vcf.gz ${meta.id}.annotated.vcf.gz.tbi ${meta.id}.panel.vcf.gz
    printf '"%s":\\n    bcftools: stub\\n' "${task.process}" > versions.yml
    """
}
