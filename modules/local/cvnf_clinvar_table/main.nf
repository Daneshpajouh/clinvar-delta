process CVNF_CLINVAR_TABLE {
    label 'process_single'
    label 'cvnf'

    input:
    path query_tsv
    path cvnf_src, stageAs: 'cvnf_pkg/cvnf/*'

    output:
    tuple path("clinvar.annotation.tsv"), path("clinvar.header.txt"), emit: table
    path "versions.yml", emit: versions

    script:
    """
    PYTHONPATH=cvnf_pkg python3 -m cvnf clinvar-table --input ${query_tsv} --out clinvar.annotation.tsv --header clinvar.header.txt

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        cvnf: \$(PYTHONPATH=cvnf_pkg python3 -m cvnf --version | cut -d' ' -f2)
    END_VERSIONS
    """

    stub:
    """
    touch clinvar.annotation.tsv clinvar.header.txt
    printf '"%s":\\n    cvnf: stub\\n' "${task.process}" > versions.yml
    """
}
