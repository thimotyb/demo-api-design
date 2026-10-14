# API Design Demos

Companion repository for the English **Designing APIs** course ([`corso-api-design`](https://github.com/thimotyb/corso-api-design)). Examples are written in Python; FastAPI is the reference API framework.

Two source trees were merged here, each for the part of the course it supports:

- **Python Base** — FastAPI, JWT and Keycloak examples (course modules 02 and 03).
- **Augmented Coding** — the checkout case study (`caso-guida/`) and the specification, architecture, contract and playbook demos built on it (course modules 01, 04, 06 and 07).

## Repository layout

- `moduli/mNN/` is the home of the examples that belong to each course module. New examples are built here, module by module.
- `examples/` is a provisional reference area. It holds copied source material (Python Base) that is integrated into the modules as the lessons are written; do not build new examples there.
- `caso-guida/` is the shared checkout case.

Folder names and READMEs inside the copied trees stay in Italian, as in their sources, so that provenance can be checked with a plain diff. The course lessons are the English reference.

## Course module → example map

| Course module | Example | Notes |
| --- | --- | --- |
| 01 API Design Fundamentals | [`moduli/m01/`](moduli/m01/README.md) | The checkout domain as REST (FastAPI), GraphQL (Strawberry) and gRPC (`grpc.aio`): requests and bytes compared, idempotent payments, error mapping, contract evolution, gRPC deadlines and server streaming, GraphQL field-level cache and cost-based rate limiting; 42 tests |
| 01 API Design Fundamentals | [`caso-guida/`](caso-guida/README.md) | Requirements, domain model, use cases, sequence diagrams and the source OpenAPI contract |
| 02 FastAPI Core Concepts | [`examples/fastapi-first-steps/`](examples/fastapi-first-steps/README.md) | Minimal FastAPI app |
| 02 FastAPI Core Concepts | [`examples/python-base-m3-keycloak/server/`](examples/python-base-m3-keycloak/server/app/) | Orders API: path parameters, Pydantic models, status codes, `Depends` |
| 03 Authentication and Authorization | [`examples/python-base-m3-keycloak/`](examples/python-base-m3-keycloak/README.md) | Keycloak client credentials, JWT validation, Postman and generated Python client. Read [`SECURITY_AUDIT.md`](examples/python-base-m3-keycloak/SECURITY_AUDIT.md) first: audience verification is disabled in the source |
| 04 Error Handling and Robustness | [`moduli/m03/step-02-speckit/demo-retry/`](moduli/m03/step-02-speckit/demo-retry/README.md) | Bounded retry for transient gateway failures, with tests |
| 05 Performance and Optimization | — | No example yet |
| 06 Documentation and Developer Experience | [`moduli/m05/step-01-contratto/`](moduli/m05/step-01-contratto/README.md) | OpenAPI profile with named examples, Spectral rulesets |
| 07 API Testing | [`moduli/m05/step-01-contratto/`](moduli/m05/step-01-contratto/README.md) | Prism mock, generated Postman collection, Newman playbooks |
| 07 API Testing | [`moduli/m03/step-02-speckit/demo-retry/`](moduli/m03/step-02-speckit/demo-retry/README.md) | `unittest` suite that fails on the starter and passes on the reference solution |
| Case design material | [`moduli/m03/`](moduli/m03/README.md), [`moduli/m04/`](moduli/m04/README.md) | Spec Kit artifacts, architecture and ArchiMate views with a traceability matrix |

## Quick start

Python 3.10 or later is required. Module M01 has its own runner (virtual environment, gRPC code generation, tests and measurement):

```bash
moduli/m01/run_all.sh
```

The retry demo uses the standard library only; its starter fails two tests by design:

```bash
(cd moduli/m03/step-02-speckit/demo-retry && python3 -m unittest -v)
```

The FastAPI examples in `examples/` need their own virtual environment:

```bash
cd examples/fastapi-first-steps
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The Keycloak/JWT laboratory and the Prism/Newman playbooks have their own setup instructions in their READMEs (Node.js 20+ for the playbooks).

## What the examples do not prove

- The Prism playbooks check fixed example responses. They do not verify retry internals, persistent order state or server-side idempotency; that needs a stateful FastAPI implementation and integration tests, which this repository does not contain yet.
- The `demo-retry` starter fails two tests on purpose.
- The M01 servers are in memory and single-process; its idempotency store would need a shared database or Redis in production, and gRPC bidirectional streaming is not covered.
- The Keycloak values (`admin/admin`, client secret, realm) are local teaching fixtures.

## Not copied

Augmented Coding modules about tooling rather than API design are left in their source repository: Plan Mode (M02), React/Java implementation plan (M06), SonarQube scan (M08), CI, MCP, memory and local-model labs (M09–M12). The Python Base `examples/integration/` labs (MuleSoft, SQLite, Microsoft Graph mock) are also left there.

## Provenance

- `caso-guida/`, `moduli/`, `scripts/`: `demo-augmented-coding` commit `10d8de3b00642fcd08f3a6a8db49b4cbc670c832`.
- `examples/`: `python-base` commit `24937f09469edf906712a949693756a0cdfff31d`.

Installed dependencies, virtual environments, local Keycloak runtime files and `.env` files are excluded.
