# Contributing

Set up once:

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
pre-commit install
```

Before a pull request, `make check` (ruff, mypy, unit tests, shellcheck) and
`make test-pipeline nf-test` must pass. Python follows PEP 8 through ruff with a line
length of 100.

A change that alters pipeline outputs on the test data updates the nf-test snapshots in the
same pull request, and the description says why the output changed. Output columns,
file names and parameters follow the versioning rules in docs/sop.md.

Commit messages: imperative subject under 72 characters, body only when the reason is not
obvious from the diff.
