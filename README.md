# API Design Demos

Public companion repository for the English **Designing APIs** course. Examples are written in Python; FastAPI is the reference API framework.

## Available examples

- [`examples/fastapi-first-steps/`](examples/fastapi-first-steps/) — minimal FastAPI application copied from Python Base M3.
- [`examples/python-base-m3-keycloak/`](examples/python-base-m3-keycloak/) — existing local Keycloak/JWT laboratory and its security audit, preserved as a source reference. Its audience validation is disabled; review and correct it before using it as a model for a new service.
- [`caso-guida/`](caso-guida/) — checkout case requirements, source OpenAPI contract, and five PlantUML diagrams.
- [`moduli/m03/`](moduli/m03/), [`moduli/m04/`](moduli/m04/), and [`moduli/m05/`](moduli/m05/) — specification and architecture documents plus the OpenAPI profile, Prism mock, generated Postman collection, Newman playbooks, and Spectral checks from augmented coding.

The M05 workflow is documented in [`moduli/m05/step-01-contratto/README.md`](moduli/m05/step-01-contratto/README.md). It targets a fixed Prism mock. A future FastAPI implementation and integration tests should verify stateful behavior, including payment idempotency, retry handling, and order persistence.

## Provenance

- `caso-guida/` and `moduli/`: `demo-augmented-coding` commit `10d8de3b00642fcd08f3a6a8db49b4cbc670c832`.
- `examples/`: `python-base` commit `24937f09469edf906712a949693756a0cdfff31d`.

Installed dependencies, virtual environments, local Keycloak runtime files, and `.env` files are excluded. The copied Keycloak values are local teaching fixtures.
