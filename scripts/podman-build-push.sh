#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/podman-build-push.sh <quay-image> [tag]

Examples:
  scripts/podman-build-push.sh quay.io/your-org/getback
  scripts/podman-build-push.sh quay.io/your-org/getback v1

Environment:
  PODMAN                Podman executable to use. Default: podman
  EXTRA_TAG             Optional second tag to apply and push.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 1
fi

IMAGE="$1"
TAG="${2:-$(git rev-parse --short HEAD)}"
PODMAN="${PODMAN:-podman}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRIMARY_REF="${IMAGE}:${TAG}"

echo "Building ${PRIMARY_REF}"
"${PODMAN}" build -f "${ROOT_DIR}/Dockerfile" -t "${PRIMARY_REF}" "${ROOT_DIR}"

echo "Pushing ${PRIMARY_REF}"
"${PODMAN}" push "${PRIMARY_REF}"

if [[ -n "${EXTRA_TAG:-}" ]]; then
  EXTRA_REF="${IMAGE}:${EXTRA_TAG}"
  echo "Tagging ${PRIMARY_REF} as ${EXTRA_REF}"
  "${PODMAN}" tag "${PRIMARY_REF}" "${EXTRA_REF}"
  echo "Pushing ${EXTRA_REF}"
  "${PODMAN}" push "${EXTRA_REF}"
fi
