import sys
import os
import importlib.util

# Add flow_orchestrator/server to path
orchestrator_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "flow_orchestrator", "server"))
print("Adding to sys.path:", orchestrator_dir)
sys.path.insert(0, orchestrator_dir)

try:
    # Use importlib to import the flow orchestrator's main file under a custom name
    spec = importlib.util.spec_from_file_location(
        "flow_orchestrator_main",
        os.path.join(orchestrator_dir, "main.py")
    )
    flow_orchestrator_module = importlib.util.module_from_spec(spec)
    sys.modules["flow_orchestrator_main"] = flow_orchestrator_module
    spec.loader.exec_module(flow_orchestrator_module)
    flow_orchestrator_app = flow_orchestrator_module.app
    print("SUCCESS: Imported flow_orchestrator_app!")
    print("App Title:", flow_orchestrator_app.title)
except Exception as e:
    print("FAILED:", e)
    import traceback
    traceback.print_exc()
