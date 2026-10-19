# Clean Debian 12 with the local-tools requirements only, for checking the `test` profile
# against a given Nextflow release with an empty plugin cache.
FROM debian:bookworm-slim@sha256:7c7b2c966bc9ee8cedfeef67e0e279108992c77681fa595db4a9d65c06ccc587

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless bcftools tabix procps python3 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG NXF_VER
RUN curl -fsSL -o /usr/local/bin/nextflow \
        "https://github.com/nextflow-io/nextflow/releases/download/v${NXF_VER}/nextflow-${NXF_VER}-dist" \
    && chmod +x /usr/local/bin/nextflow \
    && nextflow -version

RUN useradd -m runner
USER runner
WORKDIR /home/runner
