// SHA-256 of the files this run produced, taken from the output channels so that files
// left in the output directory by earlier runs are not listed.
process CVNF_OUTPUT_HASHES {
    label 'process_single'
    label 'cvnf'

    input:
    path outputs, stageAs: 'outputs/*'
    path cvnf_src, stageAs: 'cvnf_pkg/cvnf/*'

    output:
    path "outputs.sha256.json", emit: json

    script:
    """
    PYTHONPATH=cvnf_pkg python3 -m cvnf hash-files --out outputs.sha256.json outputs/*
    """

    stub:
    """
    echo '{}' > outputs.sha256.json
    """
}
