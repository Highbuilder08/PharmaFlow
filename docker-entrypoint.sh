#!/bin/sh
set -eu

PROMETHEUS_MULTIPROC_DIR="${PROMETHEUS_MULTIPROC_DIR:-/tmp/pharmaflow-prometheus}"

export PROMETHEUS_MULTIPROC_DIR

# prometheus_client multiprocess files must not survive a fresh
# Gunicorn master start. The directory is container-local /tmp.
rm -rf "${PROMETHEUS_MULTIPROC_DIR}"
mkdir -p "${PROMETHEUS_MULTIPROC_DIR}"

exec "$@"
