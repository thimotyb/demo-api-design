#!/usr/bin/env sh
set -u

SPECTRAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STEP_DIR=$(CDPATH= cd -- "$SPECTRAL_DIR/.." && pwd)

cd "$SPECTRAL_DIR"
result=0
for ruleset in owasp-top-10 url-style-guidelines documentation; do
  printf '\n=== %s ===\n' "$ruleset"
  if ! npx spectral lint "$STEP_DIR/openapi/checkout-api.yaml" --ruleset "rulesets/exported/$ruleset/.spectral.json"; then
    result=1
  fi
done
exit "$result"
