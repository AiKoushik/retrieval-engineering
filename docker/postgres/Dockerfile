# The database image: PostgreSQL 18.6 with pgvector 0.8.7 (vectors) and
# pg_textsearch 1.4.0 (BM25 ranking), both built from source at those
# tags: the exact versions the book's numbers come from.
FROM postgres:18.6-bookworm

ARG PGVECTOR_VERSION=0.8.7
ARG PG_TEXTSEARCH_VERSION=1.4.0

# Build both extensions against this server's own headers (the image's
# PG_MAJOR and PG_VERSION pin the dev package), then remove the build
# tools again. OPTFLAGS="" keeps pgvector portable across CPUs (no
# machine-specific instructions).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential ca-certificates git \
      "postgresql-server-dev-${PG_MAJOR}=${PG_VERSION}" \
 && git clone --branch "v${PGVECTOR_VERSION}" --depth 1 \
      https://github.com/pgvector/pgvector.git /tmp/pgvector \
 && make -C /tmp/pgvector OPTFLAGS="" \
 && make -C /tmp/pgvector install \
 && git clone --branch "v${PG_TEXTSEARCH_VERSION}" --depth 1 \
      https://github.com/timescale/pg_textsearch.git /tmp/pg_textsearch \
 && make -C /tmp/pg_textsearch \
 && make -C /tmp/pg_textsearch install \
 && rm -rf /tmp/pgvector /tmp/pg_textsearch \
 && apt-get purge -y --auto-remove \
      build-essential git "postgresql-server-dev-${PG_MAJOR}" \
 && rm -rf /var/lib/apt/lists/*

# Runs once, when the data volume is first created.
COPY initdb/ /docker-entrypoint-initdb.d/

# pg_textsearch must be loaded when the server starts.
CMD ["postgres", "-c", "shared_preload_libraries=pg_textsearch"]
