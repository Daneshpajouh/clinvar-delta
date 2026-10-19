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
    // A handler instead of an onComplete: section, which Nextflow 25.04 does not parse. The
    // work happens in a script function: inside the closure, workflow and params resolve
    // to the handler's delegate and are null.
    workflow.onComplete { writeRunSummary() }

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

    // The manifest task starts as soon as the inputs are known, before the analysis steps finish.
    CVNF_MANIFEST(inputs.collect(), params_json, gitCommit(), containers, workflow.start.toString())
}

// Called by the onComplete handler after success and after failure, so a failed run
// still leaves a summary next to its trace: status, duration, task counts, the error,
// and every published file with SHA-256.
def writeRunSummary() {
    def outdir = file(params.outdir)
    def outputs = [:]
    if (outdir.exists()) {
        outdir.eachFileRecurse { f ->
            if (f.isFile() && !f.name.startsWith('execution_') && f.name != 'run_summary.json') {
                def digest = java.security.MessageDigest.getInstance('SHA-256')
                f.withInputStream { stream ->
                    stream.eachByte(65536) { buffer, n -> digest.update(buffer, 0, n) }
                }
                outputs[outdir.relativize(f).toString()] = digest.digest().encodeHex().toString()
            }
        }
    }
    def stats = workflow.stats
    def summary = [
        status: workflow.success ? 'success' : 'failed',
        started: workflow.start.toString(),
        completed: workflow.complete.toString(),
        duration_ms: workflow.duration.toMillis(),
        nextflow: workflow.nextflow.version.toString(),
        profile: workflow.profile,
        session_id: workflow.sessionId.toString(),
        tasks: [succeeded: stats.succeededCount, cached: stats.cachedCount, failed: stats.failedCount,
                ignored: stats.ignoredCount, retried: stats.retriesCount],
        error: workflow.errorMessage ?: null,
        trace: "${params.outdir}/pipeline_info/execution_trace.txt",
        outputs: outputs.sort(),
    ]
    def target = file("${params.outdir}/pipeline_info/run_summary.json")
    target.parent.mkdirs()
    target.text = groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson(summary)) + "\n"
    log.info("clinvar-variant-nf ${summary.status}: ${workflow.duration}, results in ${params.outdir}")
}
