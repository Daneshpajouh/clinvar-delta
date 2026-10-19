include { CLINVAR_QUERY_SORTED } from '../modules/local/clinvar_query_sorted'
include { CVNF_DIFF as CVNF_DIFF_ALL } from '../modules/local/cvnf_diff'
include { CVNF_DIFF as CVNF_DIFF_PANEL } from '../modules/local/cvnf_diff'
include { CVNF_DIFF_REPORT } from '../modules/local/cvnf_diff_report'

workflow CLINVAR_DIFF {
    take:
    releases  // channel: [ role ('old' or 'new'), label, vcf, tbi ]
    genes     // value: path to a gene symbol list
    cvnf_src  // value: list of src/cvnf/*.py

    main:
    CLINVAR_QUERY_SORTED(releases)
    queried = CLINVAR_QUERY_SORTED.out.tsv
    old_table = queried.filter { role, _label, _tsv -> role == 'old' }.map { _role, label, tsv -> [label, tsv] }
    new_table = queried.filter { role, _label, _tsv -> role == 'new' }.map { _role, label, tsv -> [label, tsv] }
    tables = old_table.combine(new_table)
        .toList()
        .map { pairs ->
            if (pairs.size() != 1) {
                error("expected one old and one new ClinVar table, got ${pairs.size()} pairs")
            }
            pairs[0]
        }

    CVNF_DIFF_ALL(tables, channel.value(['all', file("${projectDir}/assets/NO_GENES")]), cvnf_src)
    CVNF_DIFF_PANEL(tables, genes.map { g -> ['panel', g] }, cvnf_src)
    CVNF_DIFF_REPORT(
        CVNF_DIFF_ALL.out.json.map { _scope, json -> json },
        CVNF_DIFF_PANEL.out.json.map { _scope, json -> json },
        cvnf_src,
    )

    versions = CLINVAR_QUERY_SORTED.out.versions.mix(
        CVNF_DIFF_ALL.out.versions, CVNF_DIFF_PANEL.out.versions, CVNF_DIFF_REPORT.out.versions,
    )

    emit:
    report = CVNF_DIFF_REPORT.out.report
    json = CVNF_DIFF_ALL.out.json.mix(CVNF_DIFF_PANEL.out.json)
    changes = CVNF_DIFF_ALL.out.changes.mix(CVNF_DIFF_PANEL.out.changes)
    versions = versions
}
