#!/usr/bin/env nextflow
/*
 * clinvar-delta
 *   --mode annotate : annotate germline VCFs with ClinVar and gnomAD, report a gene panel
 *   --mode diff     : compare two ClinVar releases (reclassified, added, removed)
 */

include { validateParameters; paramsSummaryLog; samplesheetToList } from 'plugin/nf-schema'
include { ANNOTATE } from './workflows/annotate'
include { CLINVAR_DIFF } from './workflows/diff'
include { CVNF_MANIFEST } from './modules/local/cvnf_manifest'
include { CVNF_OUTPUT_HASHES } from './modules/local/cvnf_output_hashes'

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
    // A handler, kept from when Nextflow 25.04 (no onComplete: section) was supported. The
    // work happens in a script function:
    // inside the closure, workflow and params resolve to the handler's delegate and are null.
    workflow.onComplete { writeRunSummary() }

    validateParameters()
    log.info(paramsSummaryLog(workflow))

    def params_json = file("${workflow.workDir}/params.${workflow.sessionId}.json")
    params_json.text = groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson(params))
    def containers = groovy.json.JsonOutput.toJson(workflow.containerEngine ? workflow.container : [:])
    // Staged into every cvnf task, so editing the Python source invalidates those tasks on -resume.
    cvnf_src = channel.value(files("${projectDir}/src/cvnf/*.py"))

    if (params.mode == 'annotate') {
        samples = channel.fromList(samplesheetToList(params.input, "${projectDir}/assets/schema_input.json"))
            .map { meta, vcf, tbi -> [meta, vcf, tbi ?: file("${vcf}.tbi")] }
        fasta = channel.value([file(params.fasta), file("${params.fasta}.fai"), file("${params.fasta}.gzi")])
        clinvar = channel.value([file(params.clinvar), file("${params.clinvar}.tbi")])
        gnomad = channel.value([file(params.gnomad), file("${params.gnomad}.tbi")])
        panel = channel.value(file(params.panel))
        ANNOTATE(samples, fasta, clinvar, gnomad, panel, cvnf_src)
        versions = ANNOTATE.out.versions
        outputs = ANNOTATE.out.annotated.flatMap { _meta, vcf, tbi -> [vcf, tbi] }
            .mix(ANNOTATE.out.table.map { _meta, table -> table })
            .mix(ANNOTATE.out.report.flatMap { _meta, md, html -> [md, html] })
            .mix(ANNOTATE.out.summary.map { _meta, json -> json })
            .mix(ANNOTATE.out.gene_summary.map { _meta, tsv -> tsv })
        inputs = samples.flatMap { _meta, vcf, _tbi -> [vcf] }
            .mix(channel.of(file(params.fasta), file(params.clinvar), file(params.gnomad), file(params.panel)))
    } else {
        releases = channel.of(
            ['old', params.clinvar_old_label, file(params.clinvar_old), file("${params.clinvar_old}.tbi")],
            ['new', params.clinvar_new_label, file(params.clinvar_new), file("${params.clinvar_new}.tbi")],
        )
        if (!params.diff_genes) {
            error("--mode diff needs --diff_genes: a text file with one gene symbol per line")
        }
        genes = channel.value(file(params.diff_genes))
        CLINVAR_DIFF(releases, genes, cvnf_src)
        versions = CLINVAR_DIFF.out.versions
        outputs = CLINVAR_DIFF.out.report.flatMap { md, html -> [md, html] }
            .mix(CLINVAR_DIFF.out.json.map { _scope, json -> json })
            .mix(CLINVAR_DIFF.out.changes.map { _scope, changes -> changes })
        inputs = channel.of(file(params.clinvar_old), file(params.clinvar_new), file(params.diff_genes))
    }

    // Each sample's task writes its own versions.yml; compare contents, not paths, so a
    // process appears once in software_versions.yml however many samples ran.
    versions
        .map { yml -> yml.text }
        .unique()
        .collectFile(name: 'software_versions.yml', storeDir: "${params.outdir}/pipeline_info", sort: true)

    // The manifest task starts as soon as the inputs are known, before the analysis steps finish.
    CVNF_MANIFEST(inputs.collect(), params_json, gitCommit(), containers, workflow.start.toString(), cvnf_src)
    CVNF_OUTPUT_HASHES(outputs.collect(), cvnf_src)
}

// Called by the onComplete handler after success and after failure, so a failed run
// still leaves a summary next to its trace: status, duration, task counts, the error,
// and the SHA-256 of each file this run produced.
def writeRunSummary() {
    // Written by CVNF_OUTPUT_HASHES from this run's output channels. After a failure the
    // file in outdir, if any, is from an earlier run, so it is not reported as this run's.
    def hashes = file("${params.outdir}/pipeline_info/outputs.sha256.json")
    def outputs = workflow.success && hashes.exists() ? new groovy.json.JsonSlurper().parseText(hashes.text) : [:]
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
        outputs: outputs,
    ]
    def target = file("${params.outdir}/pipeline_info/run_summary.json")
    target.parent.mkdirs()
    target.text = groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson(summary)) + "\n"
    log.info("clinvar-delta ${summary.status}: ${workflow.duration}, results in ${params.outdir}")
}
