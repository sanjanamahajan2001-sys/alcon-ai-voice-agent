from typing import Dict, Any, List
from pydantic import BaseModel, Field

class NodeSchema(BaseModel):
    type: str
    label: str
    description: str
    config_fields: Dict[str, str] # name: type (e.g., "url": "string")

NODE_SCHEMAS = {
    "startNode": NodeSchema(
        type="startNode",
        label="Start Call",
        description="The entry point of the call",
        config_fields={"greeting": "string"}
    ),
    "messageNode": NodeSchema(
        type="messageNode",
        label="Message",
        description="Speak a message to the caller",
        config_fields={"text": "string"}
    ),
    "apiNode": NodeSchema(
        type="apiNode",
        label="API Call",
        description="Fetch data from an external system (CRM/DB)",
        config_fields={
            "url": "string",
            "method": "string",
            "mappings": "object" # JSON mapping of response to variables
        }
    ),
    "conditionNode": NodeSchema(
        type="conditionNode",
        label="Condition",
        description="Branch the flow based on logic",
        config_fields={"expression": "string"}
    ),
    "endNode": NodeSchema(
        type="endNode",
        label="End Call",
        description="Terminate the interaction",
        config_fields={"goodbye": "string"}
    ),
    "transferNode": NodeSchema(
        type="transferNode",
        label="Transfer to Human",
        description="Escalate the call to a human service advisor",
        config_fields={
            "agent_name": "string",
            "phone_number": "string",
            "reason": "string"
        }
    )
}
