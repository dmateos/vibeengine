import { useCallback, useState, useEffect } from 'react'
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  BackgroundVariant,
  ConnectionLineType,
  ConnectionMode,
  MarkerType,
  type ReactFlowInstance,
  type Node,
  type Edge,
  type Connection,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './FlowDiagram.css'
import InputNode from './nodes/InputNode'
import OutputNode from './nodes/OutputNode'
import AgentNode from './nodes/AgentNode'
import OpenAIAgentNode from './nodes/OpenAIAgentNode'
import ClaudeAgentNode from './nodes/ClaudeAgentNode'
import ToolNode from './nodes/ToolNode'
import RouterNode from './nodes/RouterNode'
import MemoryNode from './nodes/MemoryNode'

const API_BASE_URL = 'http://localhost:8000/api'

interface NodeTypeData {
  id: number
  name: string
  display_name: string
  icon: string
  color: string
  description: string
}

interface Workflow {
  id: number
  name: string
  description: string
  nodes: Node[]
  edges: Edge[]
  created_at: string
  updated_at: string
}

const nodeTypes = {
  input: InputNode,
  output: OutputNode,
  agent: AgentNode,
  openai_agent: OpenAIAgentNode,
  claude_agent: ClaudeAgentNode,
  tool: ToolNode,
  router: RouterNode,
  memory: MemoryNode,
}

const initialNodes: Node[] = []

const initialEdges: Edge[] = []

function FlowDiagram() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [currentWorkflow, setCurrentWorkflow] = useState<Workflow | null>(null)
  const [showWorkflowList, setShowWorkflowList] = useState(false)
  const [showAddNodeMenu, setShowAddNodeMenu] = useState(false)
  const [workflowName, setWorkflowName] = useState('')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [nodeTypeOptions, setNodeTypeOptions] = useState<NodeTypeData[]>([])
  const [executionInput, setExecutionInput] = useState('')
  const [executionResult, setExecutionResult] = useState<any>(null)
  const [workflowInput, setWorkflowInput] = useState('')
  const [workflowResult, setWorkflowResult] = useState<any>(null)
  const [running, setRunning] = useState(false)
  const [runningNodeId, setRunningNodeId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'log' | 'json'>('log')
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null)

  useEffect(() => {
    loadWorkflows()
    loadNodeTypes()
  }, [])

  // Update node styling when running state changes
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => {
        const isRunning = runningNodeId === n.id
        const classes = (n.className || '')
          .split(' ')
          .filter((c) => c && c !== 'node-running')

        if (isRunning) {
          classes.push('node-running')
        }

        return {
          ...n,
          className: classes.filter(Boolean).join(' '),
        }
      })
    )
  }, [runningNodeId, setNodes])

  const loadNodeTypes = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/node-types/`)
      const data = await response.json()
      setNodeTypeOptions(data)
    } catch (error) {
      console.error('Error loading node types:', error)
    }
  }

  const loadWorkflows = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE_URL}/workflows/`)
      const data = await response.json()
      setWorkflows(data)
      setLoading(false)
      // auto-open last used workflow if any and none loaded yet
      try {
        const lastIdRaw = localStorage.getItem('lastWorkflowId')
        const lastId = lastIdRaw ? parseInt(lastIdRaw) : null
        if (lastId && !currentWorkflow) {
          const wf = data.find((w: Workflow) => w.id === lastId)
          if (wf) {
            loadWorkflow(wf)
          }
        }
      } catch {}
    } catch (error) {
      console.error('Error loading workflows:', error)
      setLoading(false)
    }
  }

  const loadWorkflow = (workflow: Workflow) => {
    setNodes(workflow.nodes)
    setEdges(
      (workflow.edges || []).map((e) => ({
        animated: true,
        type: e.type ?? 'smoothstep',
        markerEnd:
          (e as any).markerEnd ?? {
            type: MarkerType.ArrowClosed,
            width: 18,
            height: 18,
            color: (e as any).style?.stroke ?? '#94a3b8',
          },
        ...e,
      }))
    )
    setCurrentWorkflow(workflow)
    setWorkflowName(workflow.name)
    setShowWorkflowList(false)
    try {
      localStorage.setItem('lastWorkflowId', String(workflow.id))
    } catch {}
  }

  const saveWorkflow = async () => {
    if (!workflowName.trim()) {
      alert('Please enter a workflow name')
      return
    }

    setSaving(true)
    try {
      const workflowData = {
        name: workflowName,
        description: '',
        nodes: nodes,
        edges: edges,
      }

      let response
      if (currentWorkflow) {
        response = await fetch(`${API_BASE_URL}/workflows/${currentWorkflow.id}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(workflowData),
        })
      } else {
        response = await fetch(`${API_BASE_URL}/workflows/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(workflowData),
        })
      }

      const savedWorkflow = await response.json()
      setCurrentWorkflow(savedWorkflow)
      await loadWorkflows()
      alert('Workflow saved successfully!')
      try {
        localStorage.setItem('lastWorkflowId', String(savedWorkflow.id))
      } catch {}
    } catch (error) {
      console.error('Error saving workflow:', error)
      alert('Error saving workflow')
    } finally {
      setSaving(false)
    }
  }

  const createNewWorkflow = () => {
    setNodes(initialNodes)
    setEdges(initialEdges)
    setCurrentWorkflow(null)
    setWorkflowName('New Workflow')
    setShowWorkflowList(false)
    try {
      localStorage.removeItem('lastWorkflowId')
    } catch {}
  }

  const deleteWorkflow = async (id: number) => {
    if (!confirm('Are you sure you want to delete this workflow?')) return

    try {
      await fetch(`${API_BASE_URL}/workflows/${id}/`, {
        method: 'DELETE',
      })
      await loadWorkflows()
      if (currentWorkflow?.id === id) {
        createNewWorkflow()
      }
      try {
        const lastId = localStorage.getItem('lastWorkflowId')
        if (lastId && parseInt(lastId) === id) {
          localStorage.removeItem('lastWorkflowId')
        }
      } catch {}
    } catch (error) {
      console.error('Error deleting workflow:', error)
      alert('Error deleting workflow')
    }
  }

  const addNode = (nodeType: NodeTypeData) => {
    const newNode: Node = {
      id: `node-${Date.now()}`,
      type: nodeType.name,
      data: {
        label: `New ${nodeType.display_name}`,
        icon: nodeType.icon,
      },
      position: { x: 250, y: 100 + nodes.length * 50 },
    }

    setNodes((nds) => [...nds, newNode])
    setShowAddNodeMenu(false)
  }

  const onConnect = useCallback(
    (params: Connection) =>
      setEdges((eds) => {
        const getType = (id?: string | null) => nodes.find((n) => n.id === id)?.type
        const sourceType = getType(params.source)
        const targetType = getType(params.target)

        let edgeStyle: React.CSSProperties | undefined
        let className: string | undefined

        if (sourceType === 'memory' || targetType === 'memory') {
          edgeStyle = { stroke: '#ef4444', strokeDasharray: '6 4', strokeWidth: 2.5, opacity: 0.95 }
          className = 'edge-memory'
        } else if (sourceType === 'tool' || targetType === 'tool') {
          edgeStyle = { stroke: '#10b981', strokeDasharray: '6 4', strokeWidth: 2.5, opacity: 0.95 }
          className = 'edge-tool'
        }

        // Prefer the Agent right-side handle for lateral (Agent -> Memory) links
        let sourceHandle = params.sourceHandle
        let data: any = undefined
        // Context edge: Agent <-> (Memory|Tool)
        const isAgentSource = sourceType === 'openai_agent' || sourceType === 'claude_agent'
        const isAgentTarget = targetType === 'openai_agent' || targetType === 'claude_agent'
        const isAgentContext =
          (isAgentSource && (targetType === 'memory' || targetType === 'tool')) ||
          (isAgentTarget && (sourceType === 'memory' || sourceType === 'tool'))
        if (isAgentContext) {
          data = { context: true }
        }
        if (isAgentSource && targetType === 'memory') {
          sourceHandle = 'r'
        }

        const edgeProps = {
          type: 'smoothstep' as const,
          markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18, color: edgeStyle?.stroke as string | undefined },
          animated: true,
          ...(edgeStyle ? { style: edgeStyle } : {}),
          ...(className ? { className } : {}),
        }

        return addEdge({ ...params, sourceHandle, data, ...edgeProps }, eds)
      }),
    [setEdges, nodes]
  )

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node)
    setExecutionResult(null)
  }, [])

  const executeSelectedNode = async () => {
    if (!selectedNode) return
    try {
      const response = await fetch(`${API_BASE_URL}/execute-node/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node: selectedNode,
          context: {
            input: executionInput,
            // Extend with additional context fields as needed
          },
        }),
      })
      const data = await response.json()
      setExecutionResult(data)
    } catch (err) {
      setExecutionResult({ status: 'error', error: String(err) })
    }
  }

  const executeWorkflow = async (opts?: { fromSelected?: boolean }) => {
    setRunning(true)
    setWorkflowResult(null)

    // Find the start node to highlight it
    let startNodeId: string | null = null
    if (opts?.fromSelected && selectedNode) {
      startNodeId = selectedNode.id
    } else {
      // Find the first input node
      const inputNode = nodes.find(n => n.type === 'input')
      if (inputNode) {
        startNodeId = inputNode.id
      } else {
        // Fallback to first node
        if (nodes.length > 0) {
          startNodeId = nodes[0].id
        }
      }
    }

    // Highlight the running node
    if (startNodeId) {
      setRunningNodeId(startNodeId)
    }

    try {
      const response = await fetch(`${API_BASE_URL}/execute-workflow/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nodes,
          edges,
          context: {
            input: workflowInput,
          },
          ...(opts?.fromSelected && selectedNode ? { startNodeId: selectedNode.id } : {}),
        }),
      })
      const data = await response.json()
      setWorkflowResult(data)

      // Clear running state
      setRunningNodeId(null)

      // Highlight active path
      const activeEdgeIds = new Set<string>()
      const activeNodeIds = new Set<string>()
      if (Array.isArray(data?.trace)) {
        data.trace.forEach((step: any) => {
          if (step?.nodeId) activeNodeIds.add(String(step.nodeId))
          if (step?.edgeId) activeEdgeIds.add(String(step.edgeId))
        })
      }
      setEdges((eds) =>
        eds.map((e) => ({
          ...e,
          className: [
            (e.className || '')
              .split(' ')
              .filter((c) => c && c !== 'edge-active')
              .join(' '),
            activeEdgeIds.has(e.id) ? 'edge-active' : '',
          ]
            .filter(Boolean)
            .join(' '),
        }))
      )
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          className: [
            (n.className || '')
              .split(' ')
              .filter((c) => c && c !== 'node-active')
              .join(' '),
            activeNodeIds.has(n.id) ? 'node-active' : '',
          ]
            .filter(Boolean)
            .join(' '),
        }))
      )

      // Fit view to active nodes
      if (rfInstance && activeNodeIds.size > 0) {
        const nodesToFit = nodes.filter((n) => activeNodeIds.has(n.id))
        if (nodesToFit.length) {
          rfInstance.fitView({ nodes: nodesToFit, padding: 0.2, duration: 400 })
        }
      }
    } catch (err) {
      setWorkflowResult({ status: 'error', error: String(err) })
      setRunningNodeId(null)  // Clear running state on error
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="flow-container">
      <div className="flow-header">
        <div className="flow-title">
          <h2>Workflow Designer</h2>
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            placeholder="Workflow name..."
            className="workflow-name-input"
          />
          {currentWorkflow && (
            <span className="workflow-status">
              Last saved: {new Date(currentWorkflow.updated_at).toLocaleString()}
            </span>
          )}
        </div>
        <div className="flow-actions">
          <div className="add-node-dropdown">
            <button
              className="btn-secondary"
              onClick={() => setShowAddNodeMenu(!showAddNodeMenu)}
            >
              + Add Node
            </button>
            {showAddNodeMenu && (
              <div className="dropdown-menu">
                {nodeTypeOptions.map((nodeType) => (
                  <button
                    key={nodeType.id}
                    className={`dropdown-item ${nodeType.name}`}
                    onClick={() => addNode(nodeType)}
                  >
                    <span className="node-type-icon">{nodeType.icon}</span>
                    {nodeType.display_name}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            className="btn-secondary"
            onClick={() => setShowWorkflowList(!showWorkflowList)}
          >
            {showWorkflowList ? 'Close' : 'Load Workflow'}
          </button>
          <button className="btn-secondary" onClick={createNewWorkflow}>
            New Workflow
          </button>
          <button
            className="btn-primary"
            onClick={saveWorkflow}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Workflow'}
          </button>
          <input
            type="text"
            value={workflowInput}
            onChange={(e) => setWorkflowInput(e.target.value)}
            placeholder="Workflow input..."
            className="workflow-name-input"
            style={{ minWidth: 160 }}
          />
          <button className="btn-secondary" onClick={() => executeWorkflow()} disabled={running}>
            {running ? 'Running...' : 'Run'}
          </button>
          <button
            className="btn-secondary"
            onClick={() => executeWorkflow({ fromSelected: true })}
            disabled={running || !selectedNode}
            title={selectedNode ? `Run from ${selectedNode.data?.label || selectedNode.type}` : 'Select a node to enable'}
          >
            {running ? 'Running...' : 'Run From Selected'}
          </button>
        </div>
      </div>

      {showWorkflowList && (
        <div className="workflow-list-panel">
          <h3>Saved Workflows</h3>
          {loading ? (
            <p>Loading workflows...</p>
          ) : workflows.length === 0 ? (
            <p>No saved workflows yet. Create your first workflow!</p>
          ) : (
            <div className="workflow-list">
              {workflows.map((workflow) => (
                <div key={workflow.id} className="workflow-item">
                  <div
                    className="workflow-item-content"
                    onClick={() => loadWorkflow(workflow)}
                  >
                    <strong>{workflow.name}</strong>
                    <span className="workflow-meta">
                      {workflow.nodes.length} nodes • Updated{' '}
                      {new Date(workflow.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <button
                    className="btn-delete"
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteWorkflow(workflow.id)
                    }}
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flow-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          onInit={(inst) => setRfInstance(inst)}
          defaultEdgeOptions={{
            type: 'smoothstep',
            animated: true,
            markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18, color: '#94a3b8' },
          }}
          /* Make connections easier and less finicky */
          connectOnClick={true}
          connectionMode={ConnectionMode.Loose}
          connectionRadius={48}
          connectionDragThreshold={3}
          connectionLineType={ConnectionLineType.SmoothStep}
          connectionLineStyle={{ strokeWidth: 2.5, stroke: '#667eea' }}
          panOnDrag={[2]} /* right mouse only, avoid accidental pans while connecting */
          fitView
          attributionPosition="bottom-left"
        >
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              switch (node.type) {
                case 'input':
                  return '#3b82f6'
                case 'output':
                  return '#8b5cf6'
                case 'agent':
                  return '#667eea'
                case 'openai_agent':
                  return '#10a37f'
                case 'claude_agent':
                  return '#d97757'
                case 'tool':
                  return '#10b981'
                case 'router':
                  return '#f59e0b'
                case 'memory':
                  return '#ef4444'
                default:
                  return '#cbd5e1'
              }
            }}
          />
          <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        </ReactFlow>
      </div>

      <div className="run-output">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <h3>Run Output</h3>
          <div>
            <button
              className="btn-secondary"
              onClick={() => setViewMode(viewMode === 'log' ? 'json' : 'log')}
              style={{ padding: '0.35rem 0.6rem' }}
            >
              {viewMode === 'log' ? 'View JSON' : 'View Log'}
            </button>
          </div>
        </div>
        {workflowResult ? (
          viewMode === 'json' ? (
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
              {JSON.stringify(workflowResult, null, 2)}
            </pre>
          ) : (
            <div>
              <div style={{ marginBottom: 8, color: 'var(--text-secondary)' }}>
                Final: <strong style={{ color: 'var(--text-primary)' }}>{String(workflowResult.final ?? '')}</strong>
              </div>
              {Array.isArray(workflowResult.trace) && workflowResult.trace.length > 0 ? (
                <ol style={{ paddingLeft: 18, margin: 0 }}>
                  {workflowResult.trace.map((step: any, idx: number) => {
                    const res = step?.result || {}
                    const primary =
                      res.final ?? res.output ?? res.route ?? (res.status === 'ok' ? 'ok' : res.error)
                    return (
                      <li key={`${step.nodeId}-${idx}`} style={{ marginBottom: 6 }}>
                        <span style={{ color: 'var(--text-secondary)' }}>{idx + 1}.</span>{' '}
                        <strong>{step.type}</strong> <span style={{ opacity: 0.6 }}>({step.nodeId})</span>{' '}
                        {res.route !== undefined && (
                          <span style={{ marginLeft: 8 }}>route: <strong>{String(res.route)}</strong></span>
                        )}
                        {primary !== undefined && (
                          <span style={{ marginLeft: 8 }}>→ {typeof primary === 'object' ? JSON.stringify(primary) : String(primary)}</span>
                        )}
                        {(step.type === 'openai_agent' || step.type === 'claude_agent') && Array.isArray(res.tool_call_log) && res.tool_call_log.length > 0 && (
                          <div style={{ marginTop: 4, marginLeft: 12, fontSize: '0.85em', color: 'var(--text-secondary)' }}>
                            {res.tool_call_log.map((tc: any, i: number) => (
                              <div key={i}>
                                tool: <code>{tc?.name || ''}</code>{' '}
                                args: <code>{tc?.args ? JSON.stringify(tc.args) : '{}'}</code>{' '}
                                → result: <code>{tc?.result ? (typeof tc.result === 'object' ? JSON.stringify(tc.result) : String(tc.result)) : ''}</code>
                              </div>
                            ))}
                          </div>
                        )}
                      </li>
                    )
                  })}
                </ol>
              ) : (
                <p style={{ margin: 0, color: 'var(--text-secondary)' }}>No steps executed.</p>
              )}
            </div>
          )
        ) : (
          <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
            Run the workflow to see output and trace here.
          </p>
        )}
      </div>

      {selectedNode && (
        <div className="node-details">
          <h3>Node Details</h3>
          <div className="detail-item">
            <strong>Type:</strong> {selectedNode.type}
          </div>
          <div className="detail-item">
            <strong>Label:</strong>
            <input
              type="text"
              value={(selectedNode.data as any)?.label ?? ''}
              onChange={(e) => {
                const newLabel = e.target.value
                setNodes((nds) =>
                  nds.map((n) =>
                    n.id === selectedNode.id
                      ? { ...n, data: { ...(n.data as any), label: newLabel } }
                      : n
                  )
                )
                setSelectedNode((prev) =>
                  prev ? { ...prev, data: { ...(prev.data as any), label: newLabel } } : prev
                )
              }}
              style={{ width: '100%', marginLeft: 6 }}
            />
          </div>
          <div className="detail-item">
            <strong>ID:</strong> {selectedNode.id}
          </div>
          {selectedNode.type === 'input' && (
            <div className="detail-item">
              <strong>Value:</strong>
              <input
                type="text"
                value={(selectedNode.data as any)?.value ?? ''}
                onChange={(e) => {
                  const value = e.target.value
                  setNodes((nds) =>
                    nds.map((n) => (n.id === selectedNode.id ? { ...n, data: { ...(n.data as any), value } } : n))
                  )
                  setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), value } } : prev))
                }}
                style={{ width: '100%', marginLeft: 6 }}
                placeholder="Default input used if run input is blank"
              />
            </div>
          )}
          {(selectedNode.type === 'openai_agent' || selectedNode.type === 'claude_agent') && (
            <>
              <div className="detail-item">
                <strong>Model:</strong>
                <input
                  type="text"
                  value={(selectedNode.data as any)?.model ?? (selectedNode.type === 'claude_agent' ? 'claude-3-5-sonnet-20241022' : 'gpt-4o-mini')}
                  onChange={(e) => {
                    const model = e.target.value
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id ? { ...n, data: { ...(n.data as any), model } } : n
                      )
                    )
                    setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), model } } : prev))
                  }}
                  style={{ width: '100%', marginLeft: 6 }}
                  placeholder={selectedNode.type === 'claude_agent' ? 'e.g., claude-3-5-sonnet-20241022' : 'e.g., gpt-4o-mini'}
                />
              </div>
              <div className="detail-item">
                <strong>Temperature:</strong>
                <input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  value={(selectedNode.data as any)?.temperature ?? 0.2}
                  onChange={(e) => {
                    const temperature = parseFloat(e.target.value)
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id
                          ? { ...n, data: { ...(n.data as any), temperature } }
                          : n
                      )
                    )
                    setSelectedNode((prev) =>
                      prev ? { ...prev, data: { ...(prev.data as any), temperature } } : prev
                    )
                  }}
                  style={{ width: 100, marginLeft: 6 }}
                />
              </div>
              <div className="detail-item">
                <strong>System Prompt:</strong>
                <textarea
                  value={(selectedNode.data as any)?.system ?? 'You are a helpful assistant.'}
                  onChange={(e) => {
                    const system = e.target.value
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id ? { ...n, data: { ...(n.data as any), system } } : n
                      )
                    )
                    setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), system } } : prev))
                  }}
                  style={{ width: '100%', marginLeft: 6, minHeight: 60 }}
                />
              </div>
            </>
          )}
          {selectedNode.type === 'memory' && (
            <div className="detail-item">
              <strong>Key:</strong>
              <input
                type="text"
                value={(selectedNode.data as any)?.key ?? ''}
                onChange={(e) => {
                  const key = e.target.value
                  setNodes((nds) =>
                    nds.map((n) =>
                      n.id === selectedNode.id
                        ? { ...n, data: { ...(n.data as any), key } }
                        : n
                    )
                  )
                  setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), key } } : prev))
                }}
                style={{ width: '100%', marginLeft: 6 }}
                placeholder="e.g., session"
              />
            </div>
          )}

          {selectedNode.type === 'tool' && (
            <>
              <div className="detail-item">
                <strong>Operation:</strong>
                <select
                  value={(selectedNode.data as any)?.operation ?? 'echo'}
                  onChange={(e) => {
                    const operation = e.target.value
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id
                          ? { ...n, data: { ...(n.data as any), operation } }
                          : n
                      )
                    )
                    setSelectedNode((prev) =>
                      prev ? { ...prev, data: { ...(prev.data as any), operation } } : prev
                    )
                  }}
                  style={{ marginLeft: 6 }}
                >
                  <option value="echo">Echo Params</option>
                  <option value="uppercase">Uppercase Input</option>
                  <option value="lowercase">Lowercase Input</option>
                  <option value="append">Append Suffix</option>
                </select>
              </div>
              <div className="detail-item">
                <strong>Arg:</strong>
                <input
                  type="text"
                  value={(selectedNode.data as any)?.arg ?? ''}
                  onChange={(e) => {
                    const arg = e.target.value
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id
                          ? { ...n, data: { ...(n.data as any), arg } }
                          : n
                      )
                    )
                    setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), arg } } : prev))
                  }}
                  style={{ width: '100%', marginLeft: 6 }}
                  placeholder="Used for Append"
                />
              </div>
            </>
          )}
          <div className="detail-item">
            <strong>Test Input:</strong>
            <input
              type="text"
              value={executionInput}
              onChange={(e) => setExecutionInput(e.target.value)}
              placeholder="Type input to execute..."
              style={{ width: '100%', marginTop: 6 }}
            />
          </div>
          <div className="detail-item">
            <button className="btn-primary" onClick={executeSelectedNode}>
              Execute Node
            </button>
          </div>
          {executionResult && (
            <div className="detail-item">
              <strong>Result:</strong>
              <pre style={{ whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(executionResult, null, 2)}
              </pre>
            </div>
          )}
          <button
            className="btn-close"
            onClick={() => setSelectedNode(null)}
          >
            Close
          </button>
        </div>
      )}
    </div>
  )
}

export default FlowDiagram
