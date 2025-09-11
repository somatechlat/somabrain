#!/usr/bin/env bash
# Build and push SomaBrain image to Docker Hub
set -euo pipefail

IMAGE=${1:-${DOCKERHUB_IMAGE:-${DOCKERHUB_USERNAME:-your-dockerhub-username}/somabrain}}
TAG=${2:-${GIT_TAG:-local}}

if [ -z "${DOCKERHUB_USERNAME:-}" ]; then
  echo "Please set DOCKERHUB_USERNAME environment variable or pass image as first arg."
  exit 1
fi

echo "Building ${IMAGE}:${TAG}..."
docker build --platform linux/amd64,linux/arm64 -t ${IMAGE}:${TAG} .

echo "Logging into Docker Hub as ${DOCKERHUB_USERNAME}..."
docker login -u ${DOCKERHUB_USERNAME}

echo "Pushing ${IMAGE}:${TAG}..."
docker push ${IMAGE}:${TAG}

echo "Done."
