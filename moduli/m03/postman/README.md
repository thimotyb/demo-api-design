# Postman playbook

This folder contains a collection that reproduces the full flow step by step against the M3 Orders API.

## Setup

1. Start the example with `docker compose up --build`.
2. Import the environment file first.
3. Import the collection file second.
4. Select the `M3 Keycloak JWT demo` environment.

If Postman shows empty URL fields after import, re-import the environment first and then the collection. The requests rely on environment variables for the base URLs and on host/port variables to render the endpoints clearly in the client.

The scripts store `access_token`, `order_id`, and `created_order_id` in the selected environment, so you should not need to copy them manually after running the requests.

## Step by step

1. Run `01 - Get access token`.
2. Check that the response contains `access_token`.
3. Run `02 - List orders`.
4. Check that the response contains at least one order and that `order_id` is stored.
5. Run `03 - Get order detail`.
6. Run `04 - Create order`.
7. Check that the new order id is stored in `created_order_id`.
8. Run `05 - Get created order lines`.
9. Run `06 - Get access token (read-only client)`. The token is stored in `readonly_access_token`.
10. Run `07 - Create order with the read-only token (expect 403)`: the client has `orders:read` but not `orders:write`, so the API answers `403`.
11. Run `08 - List orders with the read-only token (expect 200)`: reading still works.

## What the collection does

- It requests a token from Keycloak with `client_credentials`.
- It stores the token in a collection variable.
- It lists the existing orders.
- It reads one order detail.
- It creates a new order with header and lines.
- It reads back the lines of the created order.
- It repeats the token request with a read-only client and shows that creating an order is refused with `403` while reading still works.
