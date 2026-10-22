#!/usr/bin/env bash
# Create a local certificate authority and a server certificate for the two hostnames of the
# example. A browser or client trusts the certificate only if it trusts this CA, which is what
# a public CA such as Let's Encrypt provides for real domains.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f server.pem ]; then
  echo "Certificates already exist (delete certs/*.pem and certs/*.key to recreate them)."
  exit 0
fi

# 1. The CA: a key and a self-signed certificate valid for 10 years.
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -subj "/CN=M3 local demo CA" -out ca.pem

# 2. The server key and a signing request.
openssl genrsa -out server.key 2048
openssl req -new -key server.key -subj "/CN=api.m3.localhost" -out server.csr

# 3. The CA signs the request. The names clients connect to must be in subjectAltName:
#    modern clients ignore the CN.
cat > server.cnf <<CNF
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = DNS:api.m3.localhost, DNS:auth.m3.localhost
CNF
openssl x509 -req -in server.csr -CA ca.pem -CAkey ca.key -CAcreateserial \
  -out server.pem -days 365 -sha256 -extfile server.cnf

rm -f server.csr server.cnf ca.srl
echo "Created certs/ca.pem (trust this) and certs/server.pem + certs/server.key (used by Traefik)."
