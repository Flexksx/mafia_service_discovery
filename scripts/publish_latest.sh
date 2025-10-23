#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="flexksx/mafia_service_discovery"
TAG="latest"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker CLI not found. Please install Docker before running this script." >&2
  exit 1
fi

echo "Building ${IMAGE_NAME}:${TAG}..."
docker build --pull --platform linux/amd64 -t "${IMAGE_NAME}:${TAG}" "${PROJECT_ROOT}"

echo "Pushing ${IMAGE_NAME}:${TAG} to Docker Hub..."
docker push "${IMAGE_NAME}:${TAG}"

echo "Done."
