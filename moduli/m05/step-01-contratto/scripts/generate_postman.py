#!/usr/bin/env python3
"""Generate the Postman collection from the M05 OpenAPI profile and scenario map."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml


HERE = Path(__file__).resolve().parents[1]
CONTRACT = HERE / "openapi" / "checkout-api.yaml"
UPSTREAM_CONTRACT = HERE.parents[2] / "caso-guida" / "req-apis.yaml"
SCENARIOS = HERE / "scenarios" / "postman-playbooks.yaml"
OUTPUT = HERE / "postman" / "checkout-sequence-playbooks.postman_collection.json"


def example_value(container: dict[str, Any], name: str, label: str) -> Any:
    examples = container.get("examples", {})
    if name not in examples:
        raise ValueError(f"Missing {label} example '{name}' in OpenAPI contract")
    return examples[name]["value"]


def deep_merge(target: Any, override: Any) -> Any:
    if not isinstance(target, dict) or not isinstance(override, dict):
        return override
    result = dict(target)
    for key, value in override.items():
        result[key] = deep_merge(result[key], value) if key in result else value
    return result


def js_string(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_test(step: dict[str, Any], response_code: int) -> str:
    lines = [
        f"pm.test({js_string(f'HTTP {response_code}')}, function () {{",
        f"  pm.expect(pm.response.code).to.eql({response_code});",
        "});",
        "const body = pm.response.json();",
    ]
    for field, expected in step.get("assert", {}).items():
        lines.extend(
            [
                f"pm.test({js_string(f'{field} matches the scenario')}, function () {{",
                f"  pm.expect(body[{js_string(field)}]).to.eql({js_string(expected)});",
                "});",
            ]
        )
    for field, variable in step.get("assertVariables", {}).items():
        lines.extend(
            [
                f"pm.test({js_string(f'{field} matches the saved collection variable')}, function () {{",
                f"  pm.expect(body[{js_string(field)}]).to.eql(pm.collectionVariables.get({js_string(variable)}));",
                "});",
            ]
        )
    if "idempotencyKey" in step:
        lines.extend(
            [
                "pm.test('Idempotency-Key matches this playbook attempt', function () {",
                f"  pm.expect(pm.request.headers.get('Idempotency-Key')).to.eql({js_string(step['idempotencyKey'])});",
                "});",
            ]
        )
    for variable, json_field in step.get("save", {}).items():
        lines.append(f"pm.collectionVariables.set({js_string(variable)}, body[{js_string(json_field)}]);")
    return "\n".join(lines)


def main() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    playbooks = yaml.safe_load(SCENARIOS.read_text(encoding="utf-8"))
    declared_contract = (SCENARIOS.parent / playbooks["sourceContract"]).resolve()
    if declared_contract != CONTRACT.resolve():
        raise ValueError(f"Scenario map contract path does not point to {CONTRACT}")
    base_url = contract["servers"][0]["url"].rstrip("/")
    base = urlsplit(base_url)
    upstream = yaml.safe_load(UPSTREAM_CONTRACT.read_text(encoding="utf-8"))
    for path, path_item in contract["paths"].items():
        if path not in upstream["paths"]:
            raise ValueError(f"Profile path {path} is not present in the source OpenAPI contract")
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if method not in upstream["paths"][path]:
                raise ValueError(f"Profile operation {method.upper()} {path} is not present in the source OpenAPI contract")
            request_content = operation.get("requestBody", {}).get("content", {}).get("application/json")
            if request_content and not request_content.get("examples"):
                raise ValueError(f"Required request examples missing for {method.upper()} {path}")
            for code, response in operation.get("responses", {}).items():
                response_content = response.get("content", {}).get("application/json")
                if response_content and not response_content.get("examples"):
                    raise ValueError(f"Required response examples missing for {method.upper()} {path} {code}")
    operations: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for path, path_item in contract["paths"].items():
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            operations[operation["operationId"]] = (method.upper(), path, operation)

    folders = []
    for scenario in playbooks["scenarios"]:
        sequence_file = (SCENARIOS.parent / scenario["sequence"]).resolve()
        if not sequence_file.is_file():
            raise ValueError(f"Sequence diagram not found: {scenario['sequence']}")
        requests = []
        for index, step in enumerate(scenario["steps"], start=1):
            operation_id = step["operationId"]
            if operation_id not in operations:
                raise ValueError(f"Unknown operationId '{operation_id}' in scenario '{scenario['name']}'")
            method, path, operation = operations[operation_id]
            response_code = str(step["responseCode"])
            if response_code not in operation["responses"]:
                raise ValueError(f"Response {response_code} missing for {operation_id}")
            response = operation["responses"][response_code]["content"]["application/json"]
            response_example = example_value(response, step["responseExample"], f"{operation_id}/{response_code}")

            request_path = path
            for key, value in step.get("pathParams", {}).items():
                request_path = request_path.replace("{" + key + "}", "{{" + key + "}}")
                if "{{" not in value:
                    # Keep literal fixture UUIDs self-contained in the collection URL.
                    request_path = request_path.replace("{{" + key + "}}", value)
            if re.search(r"(?<!\{)\{[^{}]+\}(?!\})", request_path):
                raise ValueError(f"Unresolved path parameter in {request_path} ({scenario['name']})")

            headers = [
                {"key": "Accept", "value": "application/json"},
                {"key": "Prefer", "value": f"code={response_code}, example={step['responseExample']}, dynamic=false"},
            ]
            if "requestBody" in operation:
                if "requestExample" not in step:
                    raise ValueError(f"Missing requestExample for {operation_id} in {scenario['name']}")
                media = operation["requestBody"]["content"]["application/json"]
                payload = example_value(media, step["requestExample"], f"{operation_id} request")
                payload = deep_merge(payload, step.get("bodyOverrides", {}))
                headers.append({"key": "Content-Type", "value": "application/json"})
                body = {"mode": "raw", "raw": json.dumps(payload, ensure_ascii=False, indent=2), "options": {"raw": {"language": "json"}}}
            else:
                body = None
            if "idempotencyKey" in step:
                headers.append({"key": "Idempotency-Key", "value": step["idempotencyKey"]})

            request = {
                "name": "{:02d} - {} {} [{} {}]".format(index, method, path, response_code, step["responseExample"]),
                "request": {
                    "method": method,
                    "header": headers,
                    "url": {
                        "raw": "{{baseUrl}}" + request_path,
                        "protocol": base.scheme,
                        "host": [base.hostname],
                        "port": str(base.port) if base.port else "",
                        "path": request_path.lstrip("/").split("/"),
                    },
                },
                "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": build_test(step, int(response_code)).splitlines()}}],
            }
            if body is not None:
                request["request"]["body"] = body
            requests.append(request)
        folders.append({"name": scenario["name"], "description": scenario["description"], "item": requests})

    collection = {
        "info": {
            "name": "M05 - Playbook Postman per le sequenze checkout",
            "description": "Generata da openapi/checkout-api.yaml e scenarios/postman-playbooks.yaml con scripts/generate_postman.py. Scenario simulati: Prism sceglie gli esempi OAS tramite Prefer; non sono test di un backend stateful.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "m05-demo-token", "type": "string"}]},
        "variable": [
            {"key": "baseUrl", "value": base_url, "type": "string"},
            {"key": "paymentId", "value": "", "type": "string"},
            {"key": "orderId", "value": "", "type": "string"},
        ],
        "item": folders,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(HERE)} ({sum(len(folder['item']) for folder in folders)} requests)")


if __name__ == "__main__":
    main()
