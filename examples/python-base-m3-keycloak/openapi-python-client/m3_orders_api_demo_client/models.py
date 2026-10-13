from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(slots=True)
class OrderLineBase:
    sku: str
    description: str
    quantity: int
    unit_price: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku": self.sku,
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
        }


@dataclass(slots=True)
class OrderCreate:
    customer: str
    order_date: date = field(default_factory=date.today)
    status: str = "new"
    lines: list[OrderLineBase] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "customer": self.customer,
            "order_date": self.order_date.isoformat(),
            "status": self.status,
            "lines": [line.to_dict() for line in self.lines],
        }

