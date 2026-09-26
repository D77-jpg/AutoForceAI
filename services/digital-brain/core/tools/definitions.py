from .base import BaseTool
from typing import Dict, Any
import json

class OrderStatusTool(BaseTool):
    name = "check_order_status"
    description = "Order status is unavailable until Genesis freezes an order contract."

    def run(self, params: Dict[str, Any]) -> str:
        # There is no frozen order-fulfillment API. Never guess a status.
        return json.dumps({"error": {"code": "ORDER_STATUS_NOT_SUPPORTED",
                                     "message": "ORDER_STATUS_NOT_SUPPORTED"}})

    @property
    def schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": []
            }
        }


