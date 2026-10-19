#!/usr/bin/env nextflow
/*
 * clinvar-variant-nf
 *   --mode annotate : annotate germline VCFs with ClinVar and gnomAD, report a gene panel
 *   --mode diff     : compare two ClinVar releases (reclassified, added, removed)
 */

include { validateParameters; paramsSummaryLog; samplesheetToList } from 'plugin/nf-schema'
include { ANNOTATE } from './workflows/annotate'
include { CLINVAR_DIFF } from './workflows/diff'
include { CVNF_MANIFEST } from './modules/local/cvnf_manifest'

// Reads the commit from .git when the pipeline runs from a local clone; Nextflow only
// fills workflow.commitId for pipelines pulled from a remote.
def gitCommit() {
    if (workflow.commitId) {
        return workflow.commitId
    }
    def head = file("${projectDir}/.git/HEAD")
    if (!head.exists()) {
        return 'unknown'
    }
    def ref = head.text.trim()
    if (!ref.startsWith('ref: ')) {
        return ref
    }
    def refFile = file("${projectDir}/.git/${ref.substring(5)}")
    return refFile.exists() ? refFile.text.trim() : 'unknown'
}

workflow {
    main:
    validateParameters()
    log.info(paramsSummaryLog(workflow))

    def params_json = file("${workflow.workDir}/params.${workflow.sessionId}.json")
    params_json.text = groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson(params))
    def containers = groovy.json.JsonOutput.toJson(workflow.containerEngine ? workflow.container : [:])

    if (params.mode == 'annotate') {
        samples = channel.fromList(samplesheetToList(params.input, "${projectDir}/assets/schema_input.json"))
            .map { meta, vcf, tbi -> [meta, vcf, tbi ?: file("${vcf}.tbi")] }
        fasta = channel.value([file(params.fasta), file("${params.fasta}.fai"), file("${params.fasta}.gzi")])
        clinvar = channel.value([file(params.clinvar), file("${params.clinvar}.tbi")])
        gnomad = channel.value([file(params.gnomad), file("${params.gnomad}.tbi")])
        panel = channel.value(file(params.panel))
        ANNOTATE(samples, fasta, clinvar, gnomad, panel)
        versions = ANNOTATE.out.versions
        inputs = samples.flatMap { _meta, vcf, _tbi -> [vcf] }
            .mix(channel.of(file(params.fasta), file(params.clinvar), file(params.gnomad), file(params.panel)))
    } else {
        releases = channel.of(
            ['old', params.clinvar_old_label, file(params.clinvar_old), file("${params.clinvar_old}.tbi")],
            ['new', params.clinvar_new_label, file(params.clinvar_new), file("${params.clinvar_new}.tbi")],
        )
        genes = channel.value(file(params.diff_genes))
        CLINVAR_DIFF(releases, genes)
        versions = CLINVAR_DIFF.out.versions
        inputs = channel.of(file(params.clinvar_old), file(params.clinvar_new), file(params.diff_genes))
    }

    versions
        .unique()
        .collectFile(name: 'software_versions.yml', storeDir: "${params.outdir}/pipeline_info", sort: true)

    CVNF_MANIFEST(inputs.collect(), params_json, gitCommit(), containers)

    onComplete:
    log.info("clinvar-variant-nf ${workflow.success ? 'completed' : 'failed'}: ${workflow.duration}, results in ${params.outdir}")
}
