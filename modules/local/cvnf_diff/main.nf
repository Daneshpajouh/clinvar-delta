process CVNF_DIFF {
    tag "${scope}"
    label 'process_low'
    label 'cvnf'

    input:
    tuple val(old_label), path(old_tsv), val(new_label), path(new_tsv)
    tuple val(scope), path(genes)
    path cvnf_src, stageAs: 'cvnf_pkg/cvnf/*'

    output:
    tuple val(scope), path("diff.${scope}.changes.tsv.gz"), emit: changes
    tuple val(scope), path("diff.${scope}.json"), emit: json
    path "versions.yml", emit: versions

    script:
    def gene_arg = genes.name != 'NO_GENES' ? "--genes ${genes}" : ''
    """
    PYTHONPATH=cvnf_pkg python3 -m cvnf diff --old ${old_tsv} --new ${new_tsv} --old-label ${old_label} --new-label ${new_label} \\
        ${gene_arg} --out diff.${scope}.changes.tsv.gz --json diff.${scope}.json

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        cvnf: \$(PYTHONPATH=cvnf_pkg python3 -m cvnf --version | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    echo -n | gzip -nc > diff.${scope}.changes.tsv.gz
    echo '{}' > diff.${scope}.json
    printf '"%s":\\n    cvnf: stub\\n' "${task.process}" > versions.yml
    """
}
