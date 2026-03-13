#!/usr/bin/env bash
set -euo pipefail

TOOLS_BIN="${CI_TOOLS_BIN:-$HOME/.local/bin}"
JUST_VERSION="${JUST_VERSION:-1.40.0}"
OPA_VERSION="${OPA_VERSION:-1.14.1}"
mkdir -p "$TOOLS_BIN"

ARCH=$(uname -m)
case "$ARCH" in
  x86_64) UV_ARCH="x86_64-unknown-linux-gnu"; JUST_ARCH="x86_64-unknown-linux-musl"; OPA_ARCH="amd64" ;;
  aarch64|arm64) UV_ARCH="aarch64-unknown-linux-gnu"; JUST_ARCH="aarch64-unknown-linux-musl"; OPA_ARCH="arm64" ;;
  *)
    echo "Unsupported architecture: $ARCH" >&2
    exit 1
    ;;
esac

if [ ! -x "$TOOLS_BIN/uv" ]; then
  curl -LsSf "https://github.com/astral-sh/uv/releases/latest/download/uv-${UV_ARCH}.tar.gz" \
    | tar -xz -C /tmp
  install "/tmp/uv-${UV_ARCH}/uv" "$TOOLS_BIN/uv"
fi

if [ ! -x "$TOOLS_BIN/just" ]; then
  curl -LsSf "https://github.com/casey/just/releases/download/${JUST_VERSION}/just-${JUST_VERSION}-${JUST_ARCH}.tar.gz" \
    | tar -xz -C /tmp just
  install /tmp/just "$TOOLS_BIN/just"
fi

if [ ! -x "$TOOLS_BIN/opa" ]; then
  curl -LsSf -o "$TOOLS_BIN/opa" \
    "https://openpolicyagent.org/downloads/v${OPA_VERSION}/opa_linux_${OPA_ARCH}_static"
  chmod +x "$TOOLS_BIN/opa"
fi

echo "Installed tools to $TOOLS_BIN"
