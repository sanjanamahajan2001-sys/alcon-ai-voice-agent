import pytest
import asyncio
from engine.registry import NodeRegistry
from engine.runtime import FlowRuntime
import json
import os

# 1. Mock Data for Tests
MOCK_FLOW = {
    "flow_id": "test_flow",
    "nodes": [
        {"id": "start", "type": "startNode", "data": {"label": "Start"}},
        {"id": "msg1", "type": "messageNode", "data": {"label": "Hello {{salutation}} {{name}}"}},
        {"id": "check", "type": "conditionNode", "data": {"label": "age > 18"}},
        {"id": "adult", "type": "messageNode", "data": {"label": "Welcome Adult"}},
        {"id": "minor", "type": "messageNode", "data": {"label": "Hello Minor"}},
        {"id": "end", "type": "endNode", "data": {"label": "End"}}
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "msg1"},
        {"id": "e2", "source": "msg1", "target": "check"},
        {"id": "e3", "source": "check", "target": "adult", "sourceHandle": "true"},
        {"id": "e4", "source": "check", "target": "minor", "sourceHandle": "false"},
        {"id": "e5", "source": "adult", "target": "end"},
        {"id": "e6", "source": "minor", "target": "end"}
    ]
}

@pytest.fixture
def runtime():
    registry = NodeRegistry()
    return FlowRuntime(registry)

@pytest.mark.asyncio
async def test_variable_resolution(runtime):
    """Test if MessageNode correctly resolves variables."""
    session = {
        "current_node_id": "msg1",
        "variables": {"name": "Sanjana", "gender": "female"},
        "audit_logs": [],
        "history": []
    }
    result = await runtime.execute_step(MOCK_FLOW, session)
    assert "Sanjana" in result["execution_result"]["logs"]
    assert "Ma'am" in result["execution_result"]["logs"]

@pytest.mark.asyncio
async def test_condition_branching_true(runtime):
    """Test if ConditionNode branches correctly (True)."""
    session = {
        "current_node_id": "check",
        "variables": {"age": 25},
        "audit_logs": [],
        "history": [{"role": "user", "text": "I am 25"}]
    }
    result = await runtime.execute_step(MOCK_FLOW, session)
    assert result["next_node_id"] == "adult"

@pytest.mark.asyncio
async def test_condition_branching_false(runtime):
    """Test if ConditionNode branches correctly (False)."""
    session = {
        "current_node_id": "check",
        "variables": {"age": 15},
        "audit_logs": [],
        "history": [{"role": "user", "text": "I am 15"}]
    }
    result = await runtime.execute_step(MOCK_FLOW, session)
    assert result["next_node_id"] == "minor"

@pytest.mark.asyncio
async def test_intent_detection_busy(runtime):
    """Test if engine detects 'Busy' intent correctly."""
    session = {
        "current_node_id": "check",
        "variables": {"age": 25},
        "audit_logs": [],
        "history": [{"role": "user", "text": "call me later i am busy"}]
    }
    result = await runtime.execute_step(MOCK_FLOW, session)
    # Since there is no 'busy' handle, it should fallback to 'false' (minor) 
    # as per our new engine hardening logic
    assert result["next_node_id"] == "minor"

def test_template_validity():
    """Verify all P&D templates exist and are valid JSON."""
    templates_dir = "templates"
    required_templates = [
        "pd_pickup_coordination.json",
        "pd_workshop_update.json",
        "pd_ready_delivery.json"
    ]
    for tmpl in required_templates:
        path = os.path.join(templates_dir, tmpl)
        assert os.path.exists(path), f"Template {tmpl} is missing!"
        with open(path, 'r') as f:
            data = json.load(f)
            assert "nodes" in data
            assert "edges" in data

if __name__ == "__main__":
    # If run directly, try to execute the test logic
    print("✨ Running Automated Verification Suite...")
    pytest.main([__file__])
