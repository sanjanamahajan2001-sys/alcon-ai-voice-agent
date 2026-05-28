import React, { useState, useCallback, useEffect, useMemo } from 'react';
import ReactFlow, {
  addEdge,
  Background,
  Controls,
  MiniMap,
  applyEdgeChanges,
  applyNodeChanges,
  Panel,
  Handle,
  Position
} from 'reactflow';
import {
  Layers, Play, Save, Plus, Database, MessageSquare, Zap, Target, X, ChevronRight, PhoneOutgoing, RotateCcw
} from 'lucide-react';

// --- Custom Node Components ---

const MessageNode = ({ data, selected }) => {
  const [text, setText] = useState(data.label || '');

  useEffect(() => {
    setText(data.label || '');
  }, [data.label]);

  return (
    <div className={`px-4 py-3 rounded-xl border-2 transition-all ${selected ? 'border-sky-500 bg-sky-500/10 shadow-lg shadow-sky-500/20' : 'border-slate-700 bg-slate-900/80'} backdrop-blur-md min-w-[220px] max-w-[300px]`}>
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-slate-700 border-2 border-slate-900" />
      <div className="flex items-center gap-2 mb-2">
        <MessageSquare className="w-4 h-4 text-sky-400" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Message</span>
      </div>
      <textarea
        className="w-full bg-transparent border-none text-sm font-medium focus:outline-none resize-none text-slate-200 placeholder:text-slate-600 leading-relaxed"
        value={text}
        rows={Math.max(1, Math.ceil(text.length / 30))}
        onChange={(evt) => setText(evt.target.value)}
        onBlur={() => data.onChange(text)}
        placeholder="Type AI response..."
      />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-sky-500 border-2 border-slate-900" />
    </div>
  );
};

const ApiNode = ({ data, selected }) => {
  const [text, setText] = useState(data.label || '');

  useEffect(() => {
    setText(data.label || '');
  }, [data.label]);

  return (
    <div className={`px-4 py-3 rounded-xl border-2 transition-all ${selected ? 'border-emerald-500 bg-emerald-500/10 shadow-lg shadow-emerald-500/20' : 'border-slate-700 bg-slate-900/80'} backdrop-blur-md min-w-[180px]`}>
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-slate-700 border-2 border-slate-900" />
      <div className="flex items-center gap-2 mb-2">
        <Database className="w-4 h-4 text-emerald-400" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">API Call</span>
      </div>
      <input
        className="w-full bg-transparent border-none text-sm font-mono focus:outline-none text-emerald-400 placeholder:text-slate-600"
        value={text}
        onChange={(evt) => setText(evt.target.value)}
        onBlur={() => data.onChange(text)}
        placeholder="https://api.url..."
      />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-emerald-500 border-2 border-slate-900" />
    </div>
  );
};

const StartNode = ({ data }) => (
  <div className="px-6 py-3 rounded-full bg-sky-500 text-white font-bold shadow-lg shadow-sky-500/30 flex items-center gap-2 border-2 border-sky-400/50">
    <Target style={{ width: '20px', height: '20px' }} />
    <span>Start Call</span>
    <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-white border-2 border-sky-500" />
  </div>
);

const EndNode = ({ data }) => (
  <div className="px-6 py-3 rounded-full bg-rose-500 text-white font-bold shadow-lg shadow-rose-500/30 flex items-center gap-2 border-2 border-rose-400/50">
    <X style={{ width: '20px', height: '20px' }} />
    <span>End Call</span>
    <Handle type="target" position={Position.Top} className="w-3 h-3 bg-white border-2 border-rose-500" />
  </div>
);

const ConditionNode = ({ data, selected }) => {
  const [text, setText] = useState(data.label || '');

  useEffect(() => {
    setText(data.label || '');
  }, [data.label]);

  return (
    <div className={`px-4 py-3 rounded-xl border-2 transition-all ${selected ? 'border-amber-500 bg-amber-500/10 shadow-lg shadow-amber-500/20' : 'border-slate-700 bg-slate-900/80'} backdrop-blur-md min-w-[220px]`}>
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-slate-700 border-2 border-slate-900" />
      <div className="flex items-center gap-2 mb-2">
        <Layers className="w-4 h-4 text-amber-400" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Condition</span>
      </div>
      <div className="text-xs font-mono text-amber-200/70 mb-1">IF:</div>
      <input
        className="w-full bg-transparent border-none text-sm font-mono focus:outline-none text-amber-400 placeholder:text-slate-600"
        value={text}
        onChange={(evt) => setText(evt.target.value)}
        onBlur={() => data.onChange(text)}
        placeholder="e.g. Identity Verification"
      />
      <div className="grid grid-cols-2 gap-y-4 mt-3">
        <div className="flex flex-col items-center">
          <span className="text-[8px] font-bold text-emerald-500 mb-1">TRUE</span>
          <Handle type="source" position={Position.Bottom} id="true" style={{ left: '20%' }} className="w-3 h-3 bg-emerald-500 border-2 border-slate-900" />
        </div>
        <div className="flex flex-col items-center">
          <span className="text-[8px] font-bold text-rose-500 mb-1">FALSE</span>
          <Handle type="source" position={Position.Bottom} id="false" style={{ left: '40%' }} className="w-3 h-3 bg-rose-500 border-2 border-slate-900" />
        </div>
        <div className="flex flex-col items-center">
          <span className="text-[8px] font-bold text-sky-500 mb-1">BUSY</span>
          <Handle type="source" position={Position.Bottom} id="busy" style={{ left: '60%' }} className="w-3 h-3 bg-sky-500 border-2 border-slate-900" />
        </div>
        <div className="flex flex-col items-center">
          <span className="text-[8px] font-bold text-slate-400 mb-1">WRONG</span>
          <Handle type="source" position={Position.Bottom} id="wrong_number" style={{ left: '80%' }} className="w-3 h-3 bg-slate-400 border-2 border-slate-900" />
        </div>
      </div>
    </div>
  );
};

const AiNode = ({ data, selected }) => {
  const [text, setText] = useState(data.label || '');

  useEffect(() => {
    setText(data.label || '');
  }, [data.label]);

  return (
    <div className={`px-4 py-3 rounded-xl border-2 transition-all ${selected ? 'border-purple-500 bg-purple-500/10 shadow-lg shadow-purple-500/20' : 'border-slate-700 bg-slate-900/80'} backdrop-blur-md min-w-[200px]`}>
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-slate-700 border-2 border-slate-900" />
      <div className="flex items-center gap-2 mb-2">
        <Zap className="w-4 h-4 text-purple-400" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">AI Prompt</span>
      </div>
      <textarea
        className="w-full bg-transparent border-none text-sm font-medium focus:outline-none resize-none text-slate-200 placeholder:text-slate-600"
        value={text}
        rows={3}
        onChange={(evt) => setText(evt.target.value)}
        onBlur={() => data.onChange(text)}
        placeholder="Ask AI to..."
      />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-purple-500 border-2 border-slate-900" />
    </div>
  );
};

const TransferNode = ({ data, selected }) => {
  const [agentName, setAgentName] = useState(data.agent_name || '');

  useEffect(() => {
    setAgentName(data.agent_name || '');
  }, [data.agent_name]);

  return (
    <div className={`px-4 py-3 rounded-xl border-2 transition-all ${selected ? 'border-rose-500 bg-rose-500/10 shadow-lg shadow-rose-500/20' : 'border-slate-700 bg-slate-900/80'} backdrop-blur-md min-w-[180px]`}>
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-slate-700 border-2 border-slate-900" />
      <div className="flex items-center gap-2 mb-2">
        <PhoneOutgoing className="w-4 h-4 text-rose-400" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Transfer</span>
      </div>
      <div className="text-[11px] font-semibold text-rose-200 mb-1">TO AGENT:</div>
      <input
        className="w-full bg-transparent border-none text-sm font-bold focus:outline-none text-white placeholder:text-slate-600"
        value={agentName}
        onChange={(evt) => setAgentName(evt.target.value)}
        onBlur={() => data.onChange({ ...data, agent_name: agentName })}
        placeholder="e.g. Amit Shah"
      />
      <div className="text-[9px] text-slate-500 mt-1 italic">Reason: {data.reason || 'Manual Verification'}</div>
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-rose-500 border-2 border-slate-900" />
    </div>
  );
};

const nodeTypes = {
  messageNode: MessageNode,
  apiNode: ApiNode,
  conditionNode: ConditionNode,
  aiNode: AiNode,
  startNode: StartNode,
  endNode: EndNode,
  transferNode: TransferNode,
};

const initialNodes = [
  {
    id: '1',
    type: 'startNode',
    data: { label: 'Start Call' },
    position: { x: 450, y: 50 },
  },
];

const initialEdges = [];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/flow-orchestrator';

export default function App() {
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);
  const [selectedNode, setSelectedNode] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [runtimeStatus, setRuntimeStatus] = useState('READY');
  const [activeNodeId, setActiveNodeId] = useState(null);
  const [executionLogs, setExecutionLogs] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [currentFlowId, setCurrentFlowId] = useState('demo_flow');

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/templates`);
      if (response.ok) {
        const data = await response.json();
        setTemplates(data);
      }
    } catch (error) {
      console.error("Failed to fetch templates:", error);
    }
  };

  const loadTemplate = async (templateId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/flows/from-template/${templateId}`, {
        method: 'POST'
      });
      if (response.ok) {
        const data = await response.json();
        // Load into React Flow
        setNodes(data.nodes.map(n => ({
          ...n,
          position: n.position || { x: 250, y: 100 },
          data: { ...n.data, onChange: (val) => updateNodeData(n.id, val) }
        })));
        setEdges(data.edges);
        setCurrentFlowId(data.flow_id);
        alert(`Loaded operational draft: ${data.flow_id}`);
      }
    } catch (error) {
      console.error("Failed to load template:", error);
      alert("Error loading template.");
    }
  };

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [setNodes]
  );

  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [setEdges]
  );

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: '#38bdf8', strokeWidth: 2 } }, eds)),
    [setEdges]
  );

  const onNodeClick = (_, node) => {
    setSelectedNode(node);
  };

  const deleteNode = useCallback((nodeId) => {
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
    setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    setSelectedNode(null);
  }, []);

  const updateNodeData = useCallback((nodeId, newLabel) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          return { ...node, data: { ...node.data, label: newLabel } };
        }
        return node;
      })
    );
  }, []);

  const addNode = (type) => {
    const id = `node_${Date.now()}`;
    const newNode = {
      id,
      type: `${type.toLowerCase()}Node`,
      data: {
        label: '',
        onChange: (val) => updateNodeData(id, val)
      },
      position: { x: 450, y: 250 },
    };
    setNodes((nds) => nds.concat(newNode));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const flowData = {
        flow_id: currentFlowId,
        version: 1,
        status: "draft",
        nodes: nodes.map(n => ({ id: n.id, type: n.type, data: n.data, position: n.position })),
        edges: edges.map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle
        }))
      };

      const response = await fetch(`${API_BASE_URL}/flows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(flowData)
      });

      if (response.ok) {
        alert(`Flow [${currentFlowId}] saved successfully!`);
      } else {
        alert("Failed to save flow.");
      }
    } catch (error) {
      console.error("Save error:", error);
      alert("Backend not reachable.");
    } finally {
      setIsSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!window.confirm("This will overwrite the master template permanently. Older versions will be moved to history. Continue?")) return;

    setIsPublishing(true);
    try {
      // 1. First Save the current state to the backend draft
      const flowData = {
        flow_id: currentFlowId,
        version: 1,
        status: "draft",
        nodes: nodes.map(n => ({ id: n.id, type: n.type, data: n.data, position: n.position })),
        edges: edges.map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle
        }))
      };

      const saveRes = await fetch(`${API_BASE_URL}/flows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(flowData)
      });

      if (!saveRes.ok) {
        throw new Error("Failed to save draft before publishing");
      }

      // 2. Then Publish the saved draft
      const response = await fetch(`${API_BASE_URL}/flows/${currentFlowId}/publish`, {
        method: 'POST'
      });

      if (response.ok) {
        const data = await response.json();
        alert(`SUCCESS: Published to Master Template [${data.template}]`);
      } else {
        alert("Publish failed.");
      }
    } catch (error) {
      console.error("Publish error:", error);
      alert(error.message || "Backend not reachable.");
    } finally {
      setIsPublishing(false);
    }
  };

  const handleRollback = async () => {
    if (!window.confirm("Are you sure you want to rollback? This will immediately revert the live flow to the previous version.")) return;

    setIsRollingBack(true);
    try {
      const response = await fetch(`${API_BASE_URL}/flows/${currentFlowId}/rollback`, {
        method: 'POST'
      });

      if (response.ok) {
        const data = await response.json();
        // Update local state with rolled back data
        setNodes(data.nodes.map(n => ({
          ...n,
          position: n.position || { x: 250, y: 100 },
          data: { ...n.data, onChange: (val) => updateNodeData(n.id, val) }
        })));
        setEdges(data.edges);
        alert(`SUCCESS: Rolled back to version [${data.version}]`);
      } else {
        const err = await response.json();
        alert(`Rollback failed: ${err.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error("Rollback error:", error);
      alert("Backend not reachable.");
    } finally {
      setIsRollingBack(false);
    }
  };

  const handleSimulate = async () => {
    setRuntimeStatus('RUNNING');
    setExecutionLogs([]);
    try {
      const response = await fetch(`${API_BASE_URL}/flows/${currentFlowId}/simulate`, {
        method: 'POST'
      });

      if (response.ok) {
        const data = await response.json();
        const steps = data.execution_steps;

        for (let i = 0; i < steps.length; i++) {
          const step = steps[i];
          setActiveNodeId(step.node_id);
          setExecutionLogs(prev => [...prev, step.logs]);
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
        setRuntimeStatus('COMPLETED');
      } else {
        alert("Simulation failed. Save the flow first.");
        setRuntimeStatus('READY');
      }
    } catch (error) {
      console.error("Simulation error:", error);
      alert("Runtime error.");
      setRuntimeStatus('READY');
    } finally {
      setTimeout(() => {
        setActiveNodeId(null);
        setRuntimeStatus('READY');
      }, 2000);
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', backgroundColor: '#020617', color: '#e2e8f0', overflow: 'hidden', fontFamily: 'Outfit, Inter, sans-serif' }}>
      {/* Sidebar */}
      <div style={{ width: '280px', borderRight: '1px solid #1e293b', backgroundColor: '#0f172a', display: 'flex', flexDirection: 'column', zIndex: 10, boxShadow: '10px 0 30px rgba(0,0,0,0.5)' }}>
        <div style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
            <div style={{ padding: '10px', backgroundColor: '#0ea5e9', borderRadius: '12px' }}>
              <Zap style={{ width: '24px', height: '24px', color: 'white' }} />
            </div>
            <div>
              <h1 style={{ fontSize: '18px', fontWeight: 'bold', margin: 0, color: 'white' }}>Flow Builder</h1>
              <p style={{ fontSize: '10px', color: '#64748b', fontWeight: 'bold', margin: 0 }}>ORCHESTRATOR</p>
            </div>
          </div>

          {/* Template Selector */}
          <div style={{ marginBottom: '32px' }}>
            <p style={{ fontSize: '10px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '12px' }}>Operational Templates</p>
            <select
              onChange={(e) => loadTemplate(e.target.value)}
              style={{ width: '100%', padding: '12px', borderRadius: '12px', backgroundColor: '#1e293b', border: '1px solid #334155', color: 'white', fontSize: '12px', cursor: 'pointer' }}
            >
              <option value="">Select a template...</option>
              {templates.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
            {currentFlowId !== 'demo_flow' && (
              <div style={{ marginTop: '8px', fontSize: '10px', color: '#38bdf8', fontFamily: 'monospace' }}>
                DRAFT: {currentFlowId}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div>
              <p style={{ fontSize: '10px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '16px' }}>Node Library</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <button onClick={() => addNode('Message')} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', padding: '12px', borderRadius: '12px', backgroundColor: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(51, 65, 85, 0.5)', cursor: 'pointer', transition: 'all 0.2s', color: '#cbd5e1' }}>
                  <MessageSquare style={{ width: '16px', height: '16px', color: '#38bdf8' }} />
                  <span style={{ fontSize: '11px', fontWeight: '600' }}>Message</span>
                </button>

                <button onClick={() => addNode('Api')} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', padding: '12px', borderRadius: '12px', backgroundColor: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(51, 65, 85, 0.5)', cursor: 'pointer', transition: 'all 0.2s', color: '#cbd5e1' }}>
                  <Database style={{ width: '16px', height: '16px', color: '#10b981' }} />
                  <span style={{ fontSize: '11px', fontWeight: '600' }}>API Call</span>
                </button>

                <button onClick={() => addNode('Condition')} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', padding: '12px', borderRadius: '12px', backgroundColor: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(51, 65, 85, 0.5)', cursor: 'pointer', transition: 'all 0.2s', color: '#cbd5e1' }}>
                  <Layers style={{ width: '16px', height: '16px', color: '#f59e0b' }} />
                  <span style={{ fontSize: '11px', fontWeight: '600' }}>Condition</span>
                </button>

                <button onClick={() => addNode('Ai')} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', padding: '12px', borderRadius: '12px', backgroundColor: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(51, 65, 85, 0.5)', cursor: 'pointer', transition: 'all 0.2s', color: '#cbd5e1' }}>
                  <Zap style={{ width: '16px', height: '16px', color: '#a855f7' }} />
                  <span style={{ fontSize: '11px', fontWeight: '600' }}>AI Prompt</span>
                </button>

                <button onClick={() => addNode('End')} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', padding: '12px', borderRadius: '12px', backgroundColor: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(244, 63, 94, 0.1)', cursor: 'pointer', transition: 'all 0.2s', color: '#cbd5e1' }}>
                  <X style={{ width: '16px', height: '16px', color: '#fb7185' }} />
                  <span style={{ fontSize: '11px', fontWeight: '600' }}>End Call</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 'auto', padding: '24px', backgroundColor: 'rgba(15, 23, 42, 0.5)', borderTop: '1px solid #1e293b' }}>
          <button onClick={handleSave} disabled={isSaving} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: '100%', padding: '14px', borderRadius: '12px', backgroundColor: isSaving ? '#475569' : '#0284c7', color: 'white', fontWeight: 'bold', fontSize: '14px', border: 'none', cursor: isSaving ? 'not-allowed' : 'pointer', marginBottom: '12px', boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)' }}>
            <Save style={{ width: '16px', height: '16px' }} />
            <span>{isSaving ? 'Saving...' : 'Save Configuration'}</span>
          </button>

          <button onClick={handlePublish} disabled={isPublishing || currentFlowId === 'demo_flow'} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: '100%', padding: '14px', borderRadius: '12px', backgroundColor: isPublishing || currentFlowId === 'demo_flow' ? '#334155' : '#7c3aed', color: 'white', fontWeight: 'bold', fontSize: '14px', border: 'none', cursor: isPublishing || currentFlowId === 'demo_flow' ? 'not-allowed' : 'pointer', marginBottom: '12px', boxShadow: isPublishing ? 'none' : '0 4px 12px rgba(124, 58, 237, 0.3)' }}>
            <Zap style={{ width: '16px', height: '16px' }} />
            <span>{isPublishing ? 'Publishing...' : 'Publish to Master'}</span>
          </button>

          <button onClick={handleRollback} disabled={isRollingBack || currentFlowId === 'demo_flow'} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: '100%', padding: '14px', borderRadius: '12px', backgroundColor: isRollingBack || currentFlowId === 'demo_flow' ? '#334155' : '#475569', color: 'white', fontWeight: 'bold', fontSize: '14px', border: 'none', cursor: isRollingBack || currentFlowId === 'demo_flow' ? 'not-allowed' : 'pointer', marginBottom: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.2)' }}>
            <RotateCcw style={{ width: '16px', height: '16px' }} />
            <span>{isRollingBack ? 'Rolling back...' : 'Rollback to Previous'}</span>
          </button>

          <button onClick={handleSimulate} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: '100%', padding: '14px', borderRadius: '12px', backgroundColor: '#1e293b', color: '#94a3b8', fontWeight: 'bold', fontSize: '14px', border: '1px solid #334155', cursor: 'pointer' }}>
            <Play style={{ width: '16px', height: '16px' }} />
            <span>Run Simulation</span>
          </button>
        </div>
      </div>

      {/* Main Canvas */}
      <div style={{ flex: 1, position: 'relative', height: '100%' }}>
        <div style={{ width: '100%', height: '100%' }}>
          <ReactFlow
            nodes={nodes.map(n => ({ ...n, style: { ...n.style, outline: n.id === activeNodeId ? '4px solid #38bdf8' : 'none', boxShadow: n.id === activeNodeId ? '0 0 20px #38bdf8' : 'none' } }))}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background color="#1e293b" gap={24} size={1} />
            <Controls style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', color: 'white' }} />

            <Panel position="top-right">
              <div style={{ backgroundColor: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(8px)', border: '1px solid rgba(51, 65, 85, 0.5)', padding: '8px 16px', borderRadius: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: 'bold', color: '#94a3b8' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }}></div>
                v1.0.0 (DRAFT)
              </div>
            </Panel>

            <Panel position="bottom-right">
              <div style={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', padding: '20px', border: '1px solid rgba(51, 65, 85, 0.5)', borderRadius: '20px', width: '280px', backdropFilter: 'blur(12px)', boxShadow: '0 20px 40px rgba(0,0,0,0.4)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                  <div style={{ padding: '6px', backgroundColor: 'rgba(14, 165, 233, 0.2)', borderRadius: '8px' }}>
                    <Layers style={{ width: '16px', height: '16px', color: '#38bdf8' }} />
                  </div>
                  <span style={{ fontSize: '10px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.2em', color: '#64748b' }}>Live Runtime</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontFamily: 'monospace', fontSize: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', backgroundColor: 'rgba(30, 41, 59, 0.4)', borderRadius: '8px' }}>
                    <span style={{ color: '#475569' }}>STATUS</span>
                    <span style={{ color: runtimeStatus === 'READY' ? '#10b981' : runtimeStatus === 'RUNNING' ? '#38bdf8' : '#cbd5e1', fontWeight: 'bold' }}>{runtimeStatus}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '100px', overflowY: 'auto', marginTop: '10px', borderTop: '1px solid #1e293b', paddingTop: '10px' }}>
                    {executionLogs.map((log, idx) => (
                      <div key={idx} style={{ color: '#94a3b8', fontSize: '9px', lineHeight: 1.4 }}>
                        <span style={{ color: '#38bdf8' }}>&gt;</span> {log}
                      </div>
                    ))}
                    {executionLogs.length === 0 && <span style={{ color: '#475569' }}>Waiting for execution...</span>}
                  </div>
                </div>
              </div>
            </Panel>
          </ReactFlow>
        </div>

        {/* Advanced Property Panel (Overlay) */}
        {selectedNode && (
          <div style={{ position: 'absolute', top: '24px', right: '24px', width: '320px', backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid #334155', borderRadius: '24px', padding: '24px', backdropFilter: 'blur(16px)', boxShadow: '0 30px 60px rgba(0,0,0,0.5)', zIndex: 100, animation: 'slideIn 0.3s ease-out' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>Node Details</h3>
              <button onClick={() => setSelectedNode(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}><X style={{ width: '18px', height: '18px' }} /></button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <label style={{ fontSize: '10px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Node ID</label>
                <div style={{ fontSize: '12px', fontFamily: 'monospace', color: '#38bdf8', marginTop: '4px' }}>{selectedNode.id}</div>
              </div>

              <div style={{ borderTop: '1px solid #1e293b', paddingTop: '20px' }}>
                <button
                  onClick={() => deleteNode(selectedNode.id)}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: '100%', padding: '12px', borderRadius: '12px', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', fontWeight: 'bold', fontSize: '12px', border: '1px solid rgba(244, 63, 94, 0.2)', cursor: 'pointer', transition: 'all 0.2s' }}
                >
                  <X style={{ width: '14px', height: '14px' }} />
                  <span>Delete This Node</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
