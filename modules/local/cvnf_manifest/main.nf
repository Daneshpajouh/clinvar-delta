process CVNF_MANIFEST {
    label 'process_single'
    label 'cvnf'

    input:
    // One folder per input, so two samples' calls.vcf.gz do not collide when staged.
    path inputs, stageAs: 'inputs/?/*'
    path params_json
    val git_commit
    val containers
    val started
    path cvnf_src, stageAs: 'cvnf_pkg/cvnf/*'

    output:
    path "run_manifest.json", emit: manifest

    script:
    """
    PYTHONPATH=cvnf_pkg python3 -m cvnf manifest --engine 'nextflow ${workflow.nextflow.version}' --git-commit '${git_commit}' \\
        --params ${params_json} --containers '${containers}' --started '${started}' \\
        --out run_manifest.json inputs/*/*
    """

    stub:
    """
    echo '{}' > run_manifest.json
    """
}
