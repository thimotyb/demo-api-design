#!/usr/bin/env bash
# Send three GraphQL requests; each one becomes a trace in Jaeger (service checkout-graphql).
set -euo pipefail
URL=${GRAPHQL_URL:-http://127.0.0.1:${GRAPHQL_PORT:-8001}/graphql}

post() {
  curl -s -X POST "$URL" -H 'Content-Type: application/json' -d "$1"
  echo
}

# 1. One query, three REST calls underneath: the order, its customer and its shipment.
post '{"query":"{ order(id: \"o-1001\") { id status customer { email } shipment { status } } }"}'

# 2. A payment the bank refuses: the REST answer is 402 PAYMENT_DECLINED.
payment() {
  echo '{"query":"mutation($i: AuthorizePaymentInput!){ authorizePayment(input: $i){ id status } }","variables":{"i":{"customerId":"c-001","amount":{"amount":"19.90","currency":"EUR"},"paymentToken":"'"$1"'","idempotencyKey":"'"$2"'"}}}'
}
post "$(payment tok_declined "$RANDOM-declined")"

# 3. A transient gateway failure: the first call fails, the retry with the same key succeeds.
KEY="$RANDOM-flaky"
post "$(payment tok_flaky "$KEY")"
post "$(payment tok_flaky "$KEY")"
