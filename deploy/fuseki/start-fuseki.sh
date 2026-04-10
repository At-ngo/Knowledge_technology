#!/bin/sh
set -eu

FUSEKI_HOME="/opt/fuseki"
DATA_ROOT="/var/lib/fuseki"
DATASET_DIR="${DATA_ROOT}/tdb-legalqa"
INIT_FLAG="${DATA_ROOT}/.initialized"
FUSEKI_PID=""

mkdir -p "${DATASET_DIR}"

cleanup() {
  if [ -n "${FUSEKI_PID}" ]; then
    kill "${FUSEKI_PID}" 2>/dev/null || true
  fi
}

trap cleanup INT TERM

if [ ! -f "${INIT_FLAG}" ]; then
  echo "[Fuseki] First-time initialization..."

  "${FUSEKI_HOME}/fuseki-server" --config /data/config/fuseki-config-inference-docker.ttl &
  FUSEKI_PID="$!"

  READY="0"
  i=0
  while [ "$i" -lt 60 ]; do
    if curl -fsS "http://127.0.0.1:3030/$/ping" >/dev/null 2>&1; then
      READY="1"
      break
    fi
    i=$((i + 1))
    sleep 1
  done

  if [ "$READY" != "1" ]; then
    echo "[Fuseki] Failed to start for initialization"
    exit 1
  fi

  echo "[Fuseki] Loading ontology and triples..."
  curl -fsS -X POST "http://127.0.0.1:3030/legalqa/data?default" \
    -H "Content-Type: application/rdf+xml" \
    --data-binary @/data/input/legal_ontology.rdf >/dev/null

  curl -fsS -X POST "http://127.0.0.1:3030/legalqa/data?default" \
    -H "Content-Type: text/turtle" \
    --data-binary @/data/input/legal_triples.ttl >/dev/null

  kill "${FUSEKI_PID}" 2>/dev/null || true
  wait "${FUSEKI_PID}" 2>/dev/null || true
  FUSEKI_PID=""

  touch "${INIT_FLAG}"
  echo "[Fuseki] Dataset initialized."
fi

echo "[Fuseki] Starting server..."
exec "${FUSEKI_HOME}/fuseki-server" --config /data/config/fuseki-config-inference-docker.ttl
