process CVNF_MANIFEST {
    label 'process_single'
    label 'cvnf'

    input:
    path inputs, stageAs: 'inputs/*'
    path params_json
    val git_commit
    val containers
    val started

    output:
    path "run_manifest.json", emit: manifest

    script:
    """
    cvnf manifest --engine 'nextflow ${workflow.nextflow.version}' --git-commit '${git_commit}' \\
        --params ${params_json} --containers '${containers}' --started '${started}' \\
        --out run_manifest.json inputs/*
    """

    stub:
    """
    echo '{}' > run_manifest.json
    """
}
