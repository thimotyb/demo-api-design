#!/usr/bin/env sh
set -u

SPECTRAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# The contract linted here is the one the M07 playbooks mock.
CONTRACT_DIR=$(CDPATH= cd -- "$SPECTRAL_DIR/../../m07/openapi" && pwd)

cd "$SPECTRAL_DIR"
result=0
for ruleset in owasp-top-10 url-style-guidelines documentation; do
  printf '\n=== %s ===\n' "$ruleset"
  if ! npx spectral lint "$CONTRACT_DIR/checkout-api.yaml" --ruleset "rulesets/exported/$ruleset/.spectral.json"; then
    result=1
  fi
done
exit "$result"
