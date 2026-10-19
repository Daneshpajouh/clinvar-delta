include { CVNF_VALIDATE } from '../modules/local/cvnf_validate'
include { CVNF_PANEL_PAD } from '../modules/local/cvnf_panel_pad'
include { CLINVAR_PREPARE } from '../modules/local/clinvar_prepare'
include { CVNF_CLINVAR_TABLE } from '../modules/local/cvnf_clinvar_table'
include { TABIX_BGZIP as TABIX_CLINVAR } from '../modules/local/tabix_bgzip'
include { TABIX_BGZIP as TABIX_PANEL } from '../modules/local/tabix_bgzip'
include { BCFTOOLS_PREFILTER } from '../modules/local/bcftools_prefilter'
include { BCFTOOLS_NORM } from '../modules/local/bcftools_norm'
include { BCFTOOLS_ANNOTATE } from '../modules/local/bcftools_annotate'
include { CVNF_FILTER } from '../modules/local/cvnf_filter'
include { CVNF_REPORT } from '../modules/local/cvnf_report'

workflow ANNOTATE {
    take:
    samples   // channel: [ meta, vcf, tbi ]
    fasta     // value: [ fasta, fai, gzi ]
    clinvar   // value: [ vcf, tbi ]
    gnomad    // value: [ vcf, tbi ]
    panel     // value: bed

    main:
    versions = channel.empty()

    CVNF_PANEL_PAD(panel, params.panel_padding)
    TABIX_PANEL(panel.map { bed -> [bed, 'bed'] })

    // Validation runs first; a sample that fails stops the run before any bcftools work.
    CVNF_VALIDATE(samples, fasta, panel)
    validated = samples.join(CVNF_VALIDATE.out.report).map { meta, vcf, tbi, _report -> [meta, vcf, tbi] }

    regions = params.prefilter_panel ? CVNF_PANEL_PAD.out.bed : channel.value(file("${projectDir}/assets/NO_REGIONS"))
    CLINVAR_PREPARE(clinvar, fasta, regions)
    CVNF_CLINVAR_TABLE(CLINVAR_PREPARE.out.tsv)
    TABIX_CLINVAR(CVNF_CLINVAR_TABLE.out.table.map { table, _header -> [table, 'tab'] })
    // combine() returns a queue channel even for single-value inputs; first() turns it back
    // into a value channel so every sample is annotated (without it only one sample ran).
    clinvar_annotation = TABIX_CLINVAR.out.indexed
        .combine(CVNF_CLINVAR_TABLE.out.table.map { _table, header -> header })
        .first()

    if (params.prefilter_panel) {
        BCFTOOLS_PREFILTER(validated, CVNF_PANEL_PAD.out.bed)
        to_normalise = BCFTOOLS_PREFILTER.out.vcf
        versions = versions.mix(BCFTOOLS_PREFILTER.out.versions)
    } else {
        to_normalise = validated
    }

    BCFTOOLS_NORM(to_normalise, fasta)
    BCFTOOLS_ANNOTATE(BCFTOOLS_NORM.out.vcf, clinvar_annotation, gnomad, TABIX_PANEL.out.indexed)
    CVNF_FILTER(BCFTOOLS_ANNOTATE.out.panel)
    CVNF_REPORT(CVNF_FILTER.out.table, panel)

    versions = versions.mix(
        CVNF_VALIDATE.out.versions, CVNF_PANEL_PAD.out.versions, TABIX_PANEL.out.versions,
        CLINVAR_PREPARE.out.versions, CVNF_CLINVAR_TABLE.out.versions, TABIX_CLINVAR.out.versions,
        BCFTOOLS_NORM.out.versions, BCFTOOLS_ANNOTATE.out.versions, CVNF_FILTER.out.versions,
        CVNF_REPORT.out.versions,
    )

    emit:
    annotated = BCFTOOLS_ANNOTATE.out.vcf
    table = CVNF_FILTER.out.table
    report = CVNF_REPORT.out.report
    summary = CVNF_REPORT.out.json
    versions = versions
}
