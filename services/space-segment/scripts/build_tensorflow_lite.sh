#!/usr/bin/env bash
# Optional: build TensorFlow Lite as a CMake install prefix for SENTRY_ENABLE_TFLITE.
# This can take >10 minutes and requires git + Python (see upstream docs).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="${TFLITE_STAGE:-${ROOT}/third_party/tflite-install}"
TAG="${TFLITE_TAG:-v2.16.1}"
TMP="${ROOT}/third_party/tensorflow-src"

echo "Cloning tensorflow ${TAG} into ${TMP} (shallow)..."
mkdir -p "${ROOT}/third_party"
rm -rf "${TMP}"
git clone --depth 1 --branch "${TAG}" https://github.com/tensorflow/tensorflow.git "${TMP}"

echo "Configuring tflite (cpu only)..."
cmake -S "${TMP}/tensorflow/lite" -B "${TMP}/tflite-build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${STAGE}"

echo "Building and installing to ${STAGE}..."
cmake --build "${TMP}/tflite-build" --parallel
cmake --install "${TMP}/tflite-build"

echo "Done. Reconfigure Sentry-Sat with:"
echo "  cmake -S core_engine -B core_engine/build \\"
echo "    -DSENTRY_ENABLE_TFLITE=ON -DTFLITE_ROOT=${STAGE}"
