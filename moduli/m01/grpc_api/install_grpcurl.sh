#!/usr/bin/env bash
# Download grpcurl, check its SHA-256 and install it (no sudo): a generic client to explore the gRPC server.
# Usage: install_grpcurl.sh [install_dir]   (default ~/.local/bin; Linux and macOS, use WSL on Windows)
set -euo pipefail

VERSION=1.9.4
INSTALL_DIR="${1:-$HOME/.local/bin}"
BASE="https://github.com/fullstorydev/grpcurl/releases/download/v${VERSION}"

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)         PLATFORM=linux_x86_64; SHA256=97e13d58d2733a0e62cd2571d1d5f0c02823f0d25282f08bddedf1ad9c5d1736 ;;
  Linux-aarch64|Linux-arm64) PLATFORM=linux_arm64; SHA256=ad66227d90631da5428b4a5ccf28d63846f0f15649d8b2367df044a59edbb617 ;;
  Darwin-x86_64)        PLATFORM=osx_x86_64;   SHA256=0c1b24a82097862027af6abe88f362db73e4846859a3ceda2dd466e4dc971a06 ;;
  Darwin-arm64)         PLATFORM=osx_arm64;    SHA256=e0df111350acf8ee38f453f4e97e0474cfe1a987ee0c368ebe5383e6a4bccf25 ;;
  *) echo "No grpcurl build is configured for $(uname -s) $(uname -m)." >&2; exit 1 ;;
esac

if [ -x "$INSTALL_DIR/grpcurl" ] && "$INSTALL_DIR/grpcurl" -version 2>&1 | grep -q "v${VERSION}"; then
  echo "grpcurl ${VERSION} is already installed in $INSTALL_DIR."
  exit 0
fi

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ARCHIVE="grpcurl_${VERSION}_${PLATFORM}.tar.gz"
echo "Downloading $ARCHIVE..."
curl -fL --silent --show-error -o "$TMP/$ARCHIVE" "$BASE/$ARCHIVE"
[ "$(sha256 "$TMP/$ARCHIVE")" = "$SHA256" ] || { echo "Checksum mismatch for $ARCHIVE." >&2; exit 1; }

tar -xzf "$TMP/$ARCHIVE" -C "$TMP" grpcurl
mkdir -p "$INSTALL_DIR"
install -m 755 "$TMP/grpcurl" "$INSTALL_DIR/grpcurl"
echo "Installed: $("$INSTALL_DIR/grpcurl" -version 2>&1) in $INSTALL_DIR"
case ":$PATH:" in *":$INSTALL_DIR:"*) ;; *) echo "Add $INSTALL_DIR to your PATH to run grpcurl from anywhere." ;; esac
