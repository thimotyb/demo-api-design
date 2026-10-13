"""Prototipo didattico intenzionalmente incompleto: non usare in produzione."""

from __future__ import annotations

import json
from dataclasses import dataclass, field


class TemporaryGatewayError(Exception):
    pass


@dataclass
class FakeGateway:
    outcomes: list[str]
    attempts: int = 0
    amounts_eur: list[int] = field(default_factory=list)

    def authorize(self, amount_eur: int, payment_token: str) -> str:
        self.attempts += 1
        self.amounts_eur.append(amount_eur)
        outcome = self.outcomes.pop(0)
        if outcome == "transient":
            raise TemporaryGatewayError("gateway temporarily unavailable")
        return f"pay-{self.attempts}"


def checkout(cart: dict, payment_token: str, gateway: FakeGateway, orders: list[dict]) -> dict:
    # Il prototipo si fida del prezzo presente nella richiesta.
    amount_eur = sum(item["unit_price_eur"] * item["quantity"] for item in cart["items"])
    try:
        # Un errore transitorio termina il flusso: manca il retry previsto dalla sequenza.
        payment_id = gateway.authorize(amount_eur, payment_token)
    except TemporaryGatewayError:
        return {"status": "FAILED", "reason": "temporary gateway error"}

    # Una nuova chiamata crea sempre un nuovo ordine, anche con lo stesso carrello.
    order = {
        "id": f"ord-{len(orders) + 1}",
        "status": "PAID",
        "amount_eur": amount_eur,
        "payment_id": payment_id,
    }
    orders.append(order)
    return order


def run_scenarios() -> dict:
    cart = {"items": [{"product_id": "SKU-DEMO", "unit_price_eur": 20, "quantity": 1}]}

    success_gateway = FakeGateway(["approved"])
    success = checkout(cart, "tok_demo", success_gateway, [])

    retry_gateway = FakeGateway(["transient", "approved"])
    transient = checkout(cart, "tok_demo", retry_gateway, [])

    repeated_gateway = FakeGateway(["approved", "approved"])
    repeated_orders: list[dict] = []
    first = checkout(cart, "tok_demo", repeated_gateway, repeated_orders)
    second = checkout(cart, "tok_demo", repeated_gateway, repeated_orders)

    altered_cart = {"items": [{"product_id": "SKU-DEMO", "unit_price_eur": 1, "quantity": 1}]}
    altered_gateway = FakeGateway(["approved"])
    altered = checkout(altered_cart, "tok_demo", altered_gateway, [])

    return {
        "success": {"status": success["status"], "orders": 1, "amount_eur": success["amount_eur"]},
        "transient": {"status": transient["status"], "gateway_attempts": retry_gateway.attempts},
        "repeated": {"order_ids": [first["id"], second["id"]], "orders": len(repeated_orders)},
        "altered_price": {"status": altered["status"], "gateway_amount_eur": altered_gateway.amounts_eur[0]},
    }


if __name__ == "__main__":
    print(json.dumps(run_scenarios(), indent=2, ensure_ascii=False))
