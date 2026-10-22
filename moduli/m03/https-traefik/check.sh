#!/usr/bin/env bash
# Smoke test of the HTTPS example. Run it after `docker compose up -d` and certs/make-certs.sh.
set -uo pipefail
cd "$(dirname "$0")"
CA=certs/ca.pem
API=https://api.m3.localhost
AUTH=https://auth.m3.localhost
TOKEN_URL=$AUTH/realms/m3-jwt/protocol/openid-connect/token
fail=0
check() { # check "description" expected actual
  if [ "$2" = "$3" ]; then echo "ok    $1 ($3)"; else echo "FAIL  $1: expected $2, got $3"; fail=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
token() { curl -s --cacert $CA -X POST $TOKEN_URL -u "$1:$2" -d grant_type=client_credentials \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])"; }

# 1. The certificate is valid for the name, signed by the CA, over a modern TLS version.
tls=$(echo | openssl s_client -connect api.m3.localhost:443 -servername api.m3.localhost -CAfile $CA 2>/dev/null)
check "certificate chain verifies against the CA" "0 (ok)" "$(echo "$tls" | sed -n 's/.*Verify return code: //p' | head -1)"
echo "info  protocol: $(echo "$tls" | sed -n 's/.*Protocol *: *//p' | head -1), cipher: $(echo "$tls" | sed -n 's/.*Cipher *: *//p' | head -1)"

# 2. A client that does not trust the CA refuses the connection (curl exit code 60).
curl -s -o /dev/null $API/ ; check "client without the CA refuses the certificate" "60" "$?"

# 3. Plain HTTP is redirected to HTTPS.
check "HTTP is redirected" "301" "$(code http://api.m3.localhost/)"
check "redirect target is HTTPS" "https://api.m3.localhost/" "$(curl -s -o /dev/null -w '%{redirect_url}' http://api.m3.localhost/)"

# 4. The same flow as the HTTP laboratory, now over HTTPS.
check "public endpoint" "200" "$(code --cacert $CA $API/)"
check "no token" "401" "$(code --cacert $CA $API/orders)"
RW=$(token m3-fastapi-client m3-fastapi-secret)
RO=$(token m3-readonly-client m3-readonly-secret)
body='{"customer":"T","lines":[{"sku":"A","description":"d","quantity":1,"unit_price":1}]}'
check "token with orders:read lists orders" "200" "$(code --cacert $CA $API/orders -H "Authorization: Bearer $RO")"
check "token with orders:read cannot create" "403" "$(code --cacert $CA -X POST $API/orders -H "Authorization: Bearer $RO" -H 'Content-Type: application/json' -d "$body")"
check "token with orders:write creates" "201" "$(code --cacert $CA -X POST $API/orders -H "Authorization: Bearer $RW" -H 'Content-Type: application/json' -d "$body")"

# 5. The token carries the HTTPS issuer and the OpenAPI document points to the HTTPS token URL.
iss=$(python3 -c "import sys, json, base64; p = sys.argv[1].split('.')[1]; print(json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)))['iss'])" "$RW")
check "issuer of the token" "$AUTH/realms/m3-jwt" "$iss"
check "tokenUrl in the OpenAPI scheme" "$TOKEN_URL" "$(curl -s --cacert $CA $API/openapi.json | python3 -c "import sys, json; print(json.load(sys.stdin)['components']['securitySchemes']['OAuth2ClientCredentials']['flows']['clientCredentials']['tokenUrl'])")"

exit $fail
