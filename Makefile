# Targets used in CONTRIBUTING.md and CI. NFTEST and PYTHON can be overridden.
PYTHON ?= .venv/bin/python
NFTEST ?= nf-test
IMAGE ?= ghcr.io/daneshpajouh/clinvar-variant-nf:1.0.0

.PHONY: venv lint typecheck test-unit test-pipeline nf-test shellcheck bats check docs image test test-docker

venv:
	python3 -m venv .venv && .venv/bin/pip install -e '.[dev]' mkdocs mkdocs-material

lint:
	$(PYTHON) -m ruff check src tests scripts bin/cvnf
	$(PYTHON) -m ruff format --check src tests scripts

typecheck:
	$(PYTHON) -m mypy

test-unit:
	$(PYTHON) -m pytest tests/unit --cov=cvnf --cov-report=term

test-pipeline:
	$(PYTHON) -m pytest -m pipeline tests/pipeline

nf-test:
	$(NFTEST) test tests/nf-test

shellcheck:
	shellcheck scripts/*.sh

bats:
	bats tests/bats

check: lint typecheck test-unit shellcheck bats

docs:
	$(PYTHON) -m mkdocs build --strict

image:
	docker build -f containers/Dockerfile -t $(IMAGE) .

test:
	nextflow run . -profile test --outdir results_test

test-docker: image
	nextflow run . -profile test,docker --outdir results_test_docker
