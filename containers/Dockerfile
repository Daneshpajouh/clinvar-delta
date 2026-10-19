# cvnf reporting tools. procps provides `ps`, which Nextflow needs inside the container
# to record %cpu and peak_rss in the trace.
FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

LABEL org.opencontainers.image.source="https://github.com/Daneshpajouh/clinvar-delta" \
      org.opencontainers.image.description="cvnf tools for clinvar-delta" \
      org.opencontainers.image.licenses="Apache-2.0"

RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/cvnf
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && cvnf --version
