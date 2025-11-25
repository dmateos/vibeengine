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
import OllamaAgentNode from './nodes/OllamaAgentNode'
import HuggingFaceNode from './nodes/HuggingFaceNode'
import ToolNode from './nodes/ToolNode'
import RouterNode from './nodes/RouterNode'
import ConditionNode from './nodes/ConditionNode'
import ValidatorNode from './nodes/ValidatorNode'
import TextTransformNode from './nodes/TextTransformNode'
import MemoryNode from './nodes/MemoryNode'
import ParallelNode from './nodes/ParallelNode'
import JoinNode from './nodes/JoinNode'
import { usePolling } from '../hooks/usePolling'

const API_BASE_URL = 'http://localhost:8000/api'

interface NodeTypeData {
  id: number
  name: string
  display_name: string
  icon: string
  color: string
  description: string
  category: string
}

interface Workflow {
  id: number
  name: string
  description: string
  nodes: Node[]
  edges: Edge[]
  api_enabled: boolean
  api_key: string | null
  created_at: string
  updated_at: string
}

const nodeTypes = {
  input: InputNode,
  output: OutputNode,
  agent: AgentNode,
  openai_agent: OpenAIAgentNode,
  claude_agent: ClaudeAgentNode,
  ollama_agent: OllamaAgentNode,
  huggingface: HuggingFaceNode,
  tool: ToolNode,
  router: RouterNode,
  condition: ConditionNode,
  json_validator: ValidatorNode,
  text_transform: TextTransformNode,
  memory: MemoryNode,
  parallel: ParallelNode,
  join: JoinNode,
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
  const [viewMode, setViewMode] = useState<'log' | 'json'>('log')
  const [showTriggersModal, setShowTriggersModal] = useState(false)
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [executionHistory, setExecutionHistory] = useState<any[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [selectedExecution, setSelectedExecution] = useState<any | null>(null)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null)
  const [consoleHeight, setConsoleHeight] = useState(240)
  const [isResizing, setIsResizing] = useState(false)

  // Polling hook for async workflow execution
  const { state: executionState, startExecution } = usePolling()

  // Update node classes based on execution state
  useEffect(() => {
    if (executionState.status === 'idle') return

    setNodes((nds) =>
      nds.map((n) => {
        const classes = []

        // Running state
        if (executionState.currentNodeId === n.id) {
          classes.push('node-running')
        }

        // Completed state
        if (executionState.completedNodes.includes(n.id)) {
          classes.push('node-completed')
        }

        // Error state
        if (executionState.errorNodes.includes(n.id)) {
          classes.push('node-error')
        }

        return {
          ...n,
          className: classes.join(' ')
        }
      })
    )
  }, [executionState, setNodes])

  // Update workflow result when execution completes
  useEffect(() => {
    if (executionState.status === 'completed') {
      setWorkflowResult({
        status: 'ok',
        final: executionState.final,
        trace: executionState.trace,
        steps: executionState.steps
      })
      setRunning(false)
    } else if (executionState.status === 'error') {
      setWorkflowResult({
        status: 'error',
        error: executionState.error,
        trace: executionState.trace
      })
      setRunning(false)
    } else if (executionState.status === 'running') {
      setRunning(true)
    }
  }, [executionState])

  useEffect(() => {
    loadWorkflows()
    loadNodeTypes()
  }, [])

  // Auto-dismiss toast after 3 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  // Handle console resize
  useEffect(() => {
    if (!isResizing) return

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY
      setConsoleHeight(Math.max(150, Math.min(600, newHeight)))
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type })
  }

  const startResize = () => {
    setIsResizing(true)
  }

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
      showToast('Please enter a workflow name', 'error')
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
      showToast('Workflow saved successfully!', 'success')
      try {
        localStorage.setItem('lastWorkflowId', String(savedWorkflow.id))
      } catch {}
    } catch (error) {
      console.error('Error saving workflow:', error)
      showToast('Error saving workflow', 'error')
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
      showToast('Workflow deleted successfully', 'success')
      try {
        const lastId = localStorage.getItem('lastWorkflowId')
        if (lastId && parseInt(lastId) === id) {
          localStorage.removeItem('lastWorkflowId')
        }
      } catch {}
    } catch (error) {
      console.error('Error deleting workflow:', error)
      showToast('Error deleting workflow', 'error')
    }
  }

  const toggleApiAccess = async () => {
    if (!currentWorkflow) return

    try {
      const response = await fetch(`${API_BASE_URL}/workflows/${currentWorkflow.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          api_enabled: !currentWorkflow.api_enabled,
        }),
      })

      if (response.ok) {
        const updated = await response.json()
        setCurrentWorkflow(updated)
        showToast(
          updated.api_enabled ? 'API access enabled' : 'API access disabled',
          'success'
        )
      }
    } catch (error) {
      console.error('Error toggling API access:', error)
      showToast('Error updating API access', 'error')
    }
  }

  const regenerateApiKey = async () => {
    if (!currentWorkflow) return
    if (!confirm('Are you sure you want to regenerate the API key? The old key will stop working.')) return

    try {
      const response = await fetch(
        `${API_BASE_URL}/workflows/${currentWorkflow.id}/regenerate-api-key/`,
        {
          method: 'POST',
        }
      )

      if (response.ok) {
        const data = await response.json()
        setCurrentWorkflow({
          ...currentWorkflow,
          api_key: data.api_key,
        })
        showToast('API key regenerated successfully', 'success')
      }
    } catch (error) {
      console.error('Error regenerating API key:', error)
      showToast('Error regenerating API key', 'error')
    }
  }

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    showToast(`${label} copied to clipboard`, 'success')
  }

  const loadExecutionHistory = async () => {
    if (!currentWorkflow) return

    setHistoryLoading(true)
    try {
      const response = await fetch(
        `${API_BASE_URL}/workflows/${currentWorkflow.id}/executions/?limit=50`
      )
      if (response.ok) {
        const data = await response.json()
        setExecutionHistory(data.results)
      }
    } catch (error) {
      console.error('Error loading execution history:', error)
      showToast('Error loading execution history', 'error')
    } finally {
      setHistoryLoading(false)
    }
  }

  const addNode = (nodeType: NodeTypeData) => {
    // Better positioning: arrange nodes in a grid pattern to prevent overlap
    const gridCols = 3
    const nodeWidth = 280 // approximate node width including spacing
    const nodeHeight = 180 // approximate node height including spacing
    const startX = 100
    const startY = 100

    const col = nodes.length % gridCols
    const row = Math.floor(nodes.length / gridCols)

    const newNode: Node = {
      id: `node-${Date.now()}`,
      type: nodeType.name,
      data: {
        label: `New ${nodeType.display_name}`,
        icon: nodeType.icon,
      },
      position: {
        x: startX + col * nodeWidth,
        y: startY + row * nodeHeight
      },
    }

    setNodes((nds) => [...nds, newNode])
    setShowAddNodeMenu(false)
    showToast(`Added ${nodeType.display_name}`, 'success')
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

        // Normalize agent connections:
        // - Agent <-> (Memory|Tool): mark as context and force right handle 'r'
        // - Agent -> non-(Memory|Tool): prefer bottom handle 's' for control-flow
        let sourceHandle = params.sourceHandle
        let data: any = undefined

        const isAgentSource = ['openai_agent','claude_agent','ollama_agent'].includes(String(sourceType))
        const isAgentTarget = ['openai_agent','claude_agent','ollama_agent'].includes(String(targetType))
        const isMemoryOrTool = (t?: string | null) => t === 'memory' || t === 'tool'
        const isAgentContext =
          (isAgentSource && isMemoryOrTool(targetType)) ||
          (isAgentTarget && isMemoryOrTool(sourceType))

        if (isAgentContext) {
          data = { context: true }
          if (isAgentSource && isMemoryOrTool(targetType)) {
            sourceHandle = 'r'
          }
        } else if (isAgentSource && !isMemoryOrTool(targetType)) {
          // Ensure control-flow from agents prefers the bottom handle
          if (sourceHandle !== 's') {
            sourceHandle = 's'
          }
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

  // Handle node deletion
  const onNodesDelete = useCallback((deleted: Node[]) => {
    const deletedIds = new Set(deleted.map(n => n.id))
    if (selectedNode && deletedIds.has(selectedNode.id)) {
      setSelectedNode(null)
    }
    // Prune edges connected to any deleted node to avoid stale edges
    setEdges((eds) => eds.filter(e => !deletedIds.has(String(e.source)) && !deletedIds.has(String(e.target))))
    showToast(`Deleted ${deleted.length} node${deleted.length > 1 ? 's' : ''}`, 'info')
  }, [selectedNode, setEdges])

  // Handle edge deletion
  const onEdgesDelete = useCallback((deleted: Edge[]) => {
    showToast(`Deleted ${deleted.length} edge${deleted.length > 1 ? 's' : ''}`, 'info')
  }, [])

  const deleteSelectedNode = () => {
    if (!selectedNode) return
    const id = selectedNode.id
    setNodes(nds => nds.filter(n => n.id !== id))
    // Also remove any edges connected to this node
    setEdges(eds => eds.filter(e => e.source !== id && e.target !== id))
    setSelectedNode(null)
    showToast('Node deleted', 'info')
  }

  const deleteSelectedEdges = () => {
    const selectedEdges = edges.filter(e => e.selected)
    if (selectedEdges.length === 0) {
      showToast('No edges selected', 'info')
      return
    }

    setEdges(eds => eds.filter(e => !e.selected))
    showToast(`Deleted ${selectedEdges.length} edge${selectedEdges.length > 1 ? 's' : ''}`, 'info')
  }

  // (Removed: edge straightening/alignment tools)

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

    // Determine start node
    let startNodeId: string | undefined = undefined
    if (opts?.fromSelected && selectedNode) {
      startNodeId = selectedNode.id
    }

    // Start async execution with polling
    await startExecution(
      nodes,
      edges,
      {
        input: workflowInput,
      },
      startNodeId,
      currentWorkflow?.id
    )
  }

  return (
    <div className="flow-container">
      <div className="flow-header">
        <div className="flow-title">
          <h2>Workflow Designer</h2>
          <div className="workflow-name-container">
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
                {Object.entries(
                  nodeTypeOptions.reduce((acc, nodeType) => {
                    const category = nodeType.category || 'Other'
                    if (!acc[category]) acc[category] = []
                    acc[category].push(nodeType)
                    return acc
                  }, {} as Record<string, NodeTypeData[]>)
                ).map(([category, nodes]) => (
                  <div key={category} className="dropdown-category">
                    <div className="dropdown-category-item">
                      {category}
                      <span className="submenu-arrow">›</span>
                    </div>
                    <div className="dropdown-submenu">
                      {nodes.map((nodeType) => (
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
                  </div>
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
          <button
            className="btn-secondary"
            onClick={() => setShowTriggersModal(true)}
            disabled={!currentWorkflow}
            title={currentWorkflow ? 'Configure API triggers' : 'Save workflow first'}
          >
            ⚡ Triggers
          </button>
          <button
            className="btn-secondary"
            onClick={() => {
              setShowHistoryModal(true)
              loadExecutionHistory()
            }}
            disabled={!currentWorkflow}
            title={currentWorkflow ? 'View execution history' : 'Save workflow first'}
          >
            📊 History
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
          {/* Alignment tools removed */}
          <button
            className="btn-delete"
            onClick={deleteSelectedEdges}
            title="Delete selected edges"
          >
            Delete Edges
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
          onNodesDelete={onNodesDelete}
          onEdgesDelete={onEdgesDelete}
          nodeTypes={nodeTypes}
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
          deleteKeyCode={null} /* Disable default delete behavior, we'll handle it with keyboard shortcuts */
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
                case 'ollama_agent':
                  return '#06b6d4'
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

      <div
        className="resize-handle"
        onMouseDown={startResize}
        style={{ cursor: isResizing ? 'row-resize' : 'ns-resize' }}
      />
      <div className="run-output" style={{ height: consoleHeight }}>
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
              {workflowResult.status === 'error' && workflowResult.error && (
                <div style={{ marginBottom: 12, padding: '8px 12px', background: '#fee2e2', borderLeft: '3px solid #ef4444', borderRadius: 4 }}>
                  <div style={{ color: '#ef4444', fontWeight: 600, marginBottom: 4 }}>Workflow Error</div>
                  <div style={{ color: '#dc2626', fontSize: '0.9em' }}>{workflowResult.error}</div>
                </div>
              )}
              <div style={{ marginBottom: 8, color: 'var(--text-secondary)' }}>
                Final: <strong style={{ color: 'var(--text-primary)' }}>{String(workflowResult.final ?? '')}</strong>
              </div>
              {Array.isArray(workflowResult.trace) && workflowResult.trace.length > 0 ? (
                <ol style={{ paddingLeft: 18, margin: 0 }}>
                  {workflowResult.trace.map((step: any, idx: number) => {
                    const res = step?.result || {}
                    const node = nodes.find(n => n.id === step.nodeId)
                    const nodeLabel = node?.data?.label || step.nodeId
                    const inputValue = step?.context?.input

                    return (
                      <li key={`${step.nodeId}-${idx}`} style={{ marginBottom: 10 }}>
                        <div>
                          <span style={{ color: 'var(--text-secondary)' }}>{idx + 1}.</span>{' '}
                          <strong style={{ color: 'var(--text-primary)' }}>{nodeLabel}</strong>{' '}
                          <span style={{ opacity: 0.5, fontSize: '0.85em' }}>({step.type})</span>
                        </div>

                        {inputValue !== undefined && inputValue !== null && (
                          <div style={{ marginLeft: 12, marginTop: 4, fontSize: '0.9em' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>Input:</span>{' '}
                            <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4 }}>
                              {typeof inputValue === 'object' ? JSON.stringify(inputValue) : String(inputValue)}
                            </code>
                          </div>
                        )}

                        {res.route !== undefined && (
                          <div style={{ marginLeft: 12, marginTop: 4, fontSize: '0.9em' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>Route:</span>{' '}
                            <strong style={{ color: res.route === 'yes' ? '#22c55e' : '#ef4444' }}>{String(res.route)}</strong>
                          </div>
                        )}

                        {res.output !== undefined && (
                          <div style={{ marginLeft: 12, marginTop: 4, fontSize: '0.9em' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>Output:</span>{' '}
                            <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4 }}>
                              {typeof res.output === 'object' ? JSON.stringify(res.output) : String(res.output)}
                            </code>
                          </div>
                        )}

                        {res.final !== undefined && res.output === undefined && (
                          <div style={{ marginLeft: 12, marginTop: 4, fontSize: '0.9em' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>Final:</span>{' '}
                            <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4 }}>
                              {typeof res.final === 'object' ? JSON.stringify(res.final) : String(res.final)}
                            </code>
                          </div>
                        )}

                        {(res.status === 'error' || res.had_error) && res.error && (
                          <div style={{ marginLeft: 12, marginTop: 4, fontSize: '0.9em' }}>
                            <span style={{ color: '#ef4444' }}>Error:</span>{' '}
                            <span style={{ color: '#ef4444' }}>{res.error}</span>
                            {res.had_error && res.status === 'ok' && (
                              <span style={{ marginLeft: 8, fontSize: '0.85em', opacity: 0.7 }}>(continued)</span>
                            )}
                          </div>
                        )}

                        {(step.type === 'openai_agent' || step.type === 'claude_agent') && Array.isArray(res.tool_call_log) && res.tool_call_log.length > 0 && (
                          <div style={{ marginTop: 6, marginLeft: 12, fontSize: '0.85em', color: 'var(--text-secondary)' }}>
                            <div style={{ marginBottom: 4, fontWeight: 500 }}>Tool Calls:</div>
                            {res.tool_call_log.map((tc: any, i: number) => (
                              <div key={i} style={{ marginLeft: 8, marginBottom: 4 }}>
                                <span style={{ color: '#10b981' }}>{tc?.name || 'unknown'}</span>
                                {tc?.args && (
                                  <>
                                    {' '}
                                    <code style={{ background: 'var(--bg-secondary)', padding: '2px 4px', borderRadius: 3, fontSize: '0.95em' }}>
                                      {JSON.stringify(tc.args)}
                                    </code>
                                  </>
                                )}
                                {tc?.result && (
                                  <>
                                    {' → '}
                                    <code style={{ background: 'var(--bg-secondary)', padding: '2px 4px', borderRadius: 3, fontSize: '0.95em' }}>
                                      {typeof tc.result === 'object' ? JSON.stringify(tc.result) : String(tc.result)}
                                    </code>
                                  </>
                                )}
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
          {(selectedNode.type === 'openai_agent' || selectedNode.type === 'claude_agent' || selectedNode.type === 'ollama_agent') && (
            <>
              <div className="detail-item">
                <strong>Model:</strong>
                <input
                  type="text"
                  value={(selectedNode.data as any)?.model ?? (
                    selectedNode.type === 'claude_agent' ? 'claude-3-5-sonnet-20241022' : (
                      selectedNode.type === 'openai_agent' ? 'gpt-4o-mini' : 'llama3.1:8b-instruct'
                    )
                  )}
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
                  placeholder={
                    selectedNode.type === 'claude_agent'
                      ? 'e.g., claude-3-5-sonnet-20241022'
                      : selectedNode.type === 'openai_agent'
                      ? 'e.g., gpt-4o-mini'
                      : 'e.g., llama3.1:8b-instruct'
                  }
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
          {selectedNode.type === 'huggingface' && (
            <>
              <div className="detail-item">
                <strong>Model:</strong>
                <input
                  type="text"
                  value={(selectedNode.data as any)?.model ?? ''}
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
                  placeholder="e.g., distilbert-base-uncased-finetuned-sst-2-english"
                />
              </div>
              <div className="detail-item">
                <strong>Task:</strong>
                <select
                  value={(selectedNode.data as any)?.task ?? 'text-classification'}
                  onChange={(e) => {
                    const task = e.target.value
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id
                          ? { ...n, data: { ...(n.data as any), task } }
                          : n
                      )
                    )
                    setSelectedNode((prev) =>
                      prev ? { ...prev, data: { ...(prev.data as any), task } } : prev
                    )
                  }}
                  style={{ width: '100%', marginLeft: 6 }}
                >
                  <option value="text-classification">Text Classification</option>
                  <option value="sentiment-analysis">Sentiment Analysis</option>
                  <option value="zero-shot-classification">Zero-Shot Classification</option>
                  <option value="question-answering">Question Answering</option>
                  <option value="ner">Named Entity Recognition (NER)</option>
                  <option value="feature-extraction">Feature Extraction (Embeddings)</option>
                  <option value="summarization">Summarization</option>
                  <option value="translation">Translation</option>
                </select>
              </div>
              {(selectedNode.data as any)?.task === 'zero-shot-classification' && (
                <div className="detail-item">
                  <strong>Candidate Labels:</strong>
                  <input
                    type="text"
                    value={(selectedNode.data as any)?.candidate_labels?.join(', ') ?? ''}
                    onChange={(e) => {
                      const candidate_labels = e.target.value.split(',').map(s => s.trim()).filter(s => s)
                      setNodes((nds) =>
                        nds.map((n) =>
                          n.id === selectedNode.id
                            ? { ...n, data: { ...(n.data as any), candidate_labels } }
                            : n
                        )
                      )
                      setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), candidate_labels } } : prev))
                    }}
                    style={{ width: '100%', marginLeft: 6 }}
                    placeholder="e.g., positive, negative, neutral"
                  />
                </div>
              )}
              {(selectedNode.data as any)?.task === 'question-answering' && (
                <div className="detail-item">
                  <strong>Question:</strong>
                  <input
                    type="text"
                    value={(selectedNode.data as any)?.question ?? ''}
                    onChange={(e) => {
                      const question = e.target.value
                      setNodes((nds) =>
                        nds.map((n) =>
                          n.id === selectedNode.id
                            ? { ...n, data: { ...(n.data as any), question } }
                            : n
                        )
                      )
                      setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), question } } : prev))
                    }}
                    style={{ width: '100%', marginLeft: 6 }}
                    placeholder="e.g., What is the main topic?"
                  />
                </div>
              )}
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
                  <option value="google_search">Google Search</option>
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
                  placeholder={(selectedNode.data as any)?.operation === 'google_search' ? 'Optional: e.g., site:example.com OR extra keywords' : 'Used for Append'}
                />
              </div>

            </>
          )}

          {selectedNode.type === 'text_transform' && (
            <>
              <div className="detail-item">
                <strong>Operation:</strong>
                <select
                  value={(selectedNode.data as any)?.operation ?? 'upper'}
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
                  style={{ width: '100%', marginLeft: 6 }}
                >
                  <option value="upper">Uppercase</option>
                  <option value="lower">Lowercase</option>
                  <option value="trim">Trim Whitespace</option>
                  <option value="replace">Replace</option>
                  <option value="regex_replace">Regex Replace</option>
                  <option value="regex_extract">Regex Extract</option>
                  <option value="filter_lines">Filter Lines</option>
                  <option value="split">Split</option>
                  <option value="join">Join Lines</option>
                  <option value="substring">Substring</option>
                  <option value="length">Length</option>
                </select>
              </div>

              {(selectedNode.data as any)?.operation === 'replace' && (
                <>
                  <div className="detail-item">
                    <strong>Find:</strong>
                    <input
                      type="text"
                      value={(selectedNode.data as any)?.find ?? ''}
                      onChange={(e) => {
                        const find = e.target.value
                        setNodes((nds) =>
                          nds.map((n) =>
                            n.id === selectedNode.id
                              ? { ...n, data: { ...(n.data as any), find } }
                              : n
                          )
                        )
                        setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), find } } : prev))
                      }}
                      style={{ width: '100%', marginLeft: 6 }}
                      placeholder="Text to find"
                    />
                  </div>
                  <div className="detail-item">
                    <strong>Replace With:</strong>
                    <input
                      type="text"
                      value={(selectedNode.data as any)?.replace_with ?? ''}
                      onChange={(e) => {
                        const replace_with = e.target.value
                        setNodes((nds) =>
                          nds.map((n) =>
                            n.id === selectedNode.id
                              ? { ...n, data: { ...(n.data as any), replace_with } }
                              : n
                          )
                        )
                        setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), replace_with } } : prev))
                      }}
                      style={{ width: '100%', marginLeft: 6 }}
                      placeholder="Replacement text"
                    />
                  </div>
                </>
              )}

              {((selectedNode.data as any)?.operation === 'regex_replace' ||
                (selectedNode.data as any)?.operation === 'regex_extract' ||
                (selectedNode.data as any)?.operation === 'filter_lines') && (
                <>
                  <div className="detail-item">
                    <strong>Pattern:</strong>
                    <input
                      type="text"
                      value={(selectedNode.data as any)?.pattern ?? ''}
                      onChange={(e) => {
                        const pattern = e.target.value
                        setNodes((nds) =>
                          nds.map((n) =>
                            n.id === selectedNode.id
                              ? { ...n, data: { ...(n.data as any), pattern } }
                              : n
                          )
                        )
                        setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), pattern } } : prev))
                      }}
                      style={{ width: '100%', marginLeft: 6 }}
                      placeholder="Regex pattern (e.g., \\d+)"
                    />
                  </div>
                  {(selectedNode.data as any)?.operation === 'regex_replace' && (
                    <div className="detail-item">
                      <strong>Replace With:</strong>
                      <input
                        type="text"
                        value={(selectedNode.data as any)?.replace_with ?? ''}
                        onChange={(e) => {
                          const replace_with = e.target.value
                          setNodes((nds) =>
                            nds.map((n) =>
                              n.id === selectedNode.id
                                ? { ...n, data: { ...(n.data as any), replace_with } }
                                : n
                            )
                          )
                          setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), replace_with } } : prev))
                        }}
                        style={{ width: '100%', marginLeft: 6 }}
                        placeholder="Replacement text"
                      />
                    </div>
                  )}
                </>
              )}

              {((selectedNode.data as any)?.operation === 'split' ||
                (selectedNode.data as any)?.operation === 'join') && (
                <div className="detail-item">
                  <strong>Delimiter:</strong>
                  <input
                    type="text"
                    value={(selectedNode.data as any)?.delimiter ?? ((selectedNode.data as any)?.operation === 'split' ? ',' : ' ')}
                    onChange={(e) => {
                      const delimiter = e.target.value
                      setNodes((nds) =>
                        nds.map((n) =>
                          n.id === selectedNode.id
                            ? { ...n, data: { ...(n.data as any), delimiter } }
                            : n
                        )
                      )
                      setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), delimiter } } : prev))
                    }}
                    style={{ width: '100%', marginLeft: 6 }}
                    placeholder={(selectedNode.data as any)?.operation === 'split' ? 'e.g., ,' : 'e.g., space'}
                  />
                </div>
              )}

              {(selectedNode.data as any)?.operation === 'substring' && (
                <>
                  <div className="detail-item">
                    <strong>Start:</strong>
                    <input
                      type="number"
                      value={(selectedNode.data as any)?.start ?? 0}
                      onChange={(e) => {
                        const start = e.target.value
                        setNodes((nds) =>
                          nds.map((n) =>
                            n.id === selectedNode.id
                              ? { ...n, data: { ...(n.data as any), start } }
                              : n
                          )
                        )
                        setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), start } } : prev))
                      }}
                      style={{ width: '100%', marginLeft: 6 }}
                      placeholder="Start index"
                    />
                  </div>
                  <div className="detail-item">
                    <strong>End (optional):</strong>
                    <input
                      type="number"
                      value={(selectedNode.data as any)?.end ?? ''}
                      onChange={(e) => {
                        const end = e.target.value
                        setNodes((nds) =>
                          nds.map((n) =>
                            n.id === selectedNode.id
                              ? { ...n, data: { ...(n.data as any), end } }
                              : n
                          )
                        )
                        setSelectedNode((prev) => (prev ? { ...prev, data: { ...(prev.data as any), end } } : prev))
                      }}
                      style={{ width: '100%', marginLeft: 6 }}
                      placeholder="End index (leave empty for end of string)"
                    />
                  </div>
                </>
              )}
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
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <button
              className="btn-delete"
              onClick={deleteSelectedNode}
              style={{ flex: 1 }}
            >
              Delete Node
            </button>
            <button
              className="btn-close"
              onClick={() => setSelectedNode(null)}
              style={{ flex: 1 }}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Triggers Modal */}
      {showTriggersModal && currentWorkflow && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setShowTriggersModal(false)}
        >
          <div
            style={{
              background: 'var(--card-bg)',
              borderRadius: '12px',
              padding: '2rem',
              maxWidth: '600px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto',
              boxShadow: '0 8px 32px var(--shadow-lg)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ marginTop: 0, marginBottom: '1.5rem', color: 'var(--text-primary)' }}>
              ⚡ External Triggers
            </h2>

            <div style={{ marginBottom: '1.5rem' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '1rem',
                }}
              >
                <strong style={{ color: 'var(--text-primary)' }}>API Access</strong>
                <button
                  className={currentWorkflow.api_enabled ? 'btn-primary' : 'btn-secondary'}
                  onClick={toggleApiAccess}
                  style={{ minWidth: '100px' }}
                >
                  {currentWorkflow.api_enabled ? 'Enabled' : 'Disabled'}
                </button>
              </div>

              {currentWorkflow.api_enabled && currentWorkflow.api_key && (
                <div>
                  <div style={{ marginBottom: '1rem' }}>
                    <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '0.5rem' }}>
                      API Endpoint
                    </strong>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <input
                        type="text"
                        readOnly
                        value={`${API_BASE_URL}/workflows/${currentWorkflow.id}/trigger/`}
                        style={{
                          flex: 1,
                          padding: '0.5rem',
                          borderRadius: '4px',
                          border: '1px solid var(--border-color)',
                          background: 'var(--bg-secondary)',
                          color: 'var(--text-primary)',
                          fontFamily: 'monospace',
                          fontSize: '0.85rem',
                        }}
                      />
                      <button
                        className="btn-secondary"
                        onClick={() =>
                          copyToClipboard(
                            `${API_BASE_URL}/workflows/${currentWorkflow.id}/trigger/`,
                            'Endpoint'
                          )
                        }
                      >
                        Copy
                      </button>
                    </div>
                  </div>

                  <div style={{ marginBottom: '1rem' }}>
                    <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '0.5rem' }}>
                      API Key
                    </strong>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <input
                        type="password"
                        readOnly
                        value={currentWorkflow.api_key}
                        style={{
                          flex: 1,
                          padding: '0.5rem',
                          borderRadius: '4px',
                          border: '1px solid var(--border-color)',
                          background: 'var(--bg-secondary)',
                          color: 'var(--text-primary)',
                          fontFamily: 'monospace',
                          fontSize: '0.85rem',
                        }}
                      />
                      <button
                        className="btn-secondary"
                        onClick={() => copyToClipboard(currentWorkflow.api_key || '', 'API key')}
                      >
                        Copy
                      </button>
                      <button className="btn-secondary" onClick={regenerateApiKey}>
                        Regenerate
                      </button>
                    </div>
                  </div>

                  <div
                    style={{
                      padding: '1rem',
                      background: 'var(--bg-tertiary)',
                      borderRadius: '8px',
                      marginBottom: '1rem',
                    }}
                  >
                    <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '0.5rem' }}>
                      Example cURL Command
                    </strong>
                    <pre
                      style={{
                        margin: 0,
                        padding: '0.75rem',
                        background: 'var(--bg-secondary)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        overflow: 'auto',
                        color: 'var(--text-primary)',
                      }}
                    >
{`curl -X POST ${API_BASE_URL}/workflows/${currentWorkflow.id}/trigger/ \\
  -H "X-API-Key: ${currentWorkflow.api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{"input": "your input text here"}'`}
                    </pre>
                    <button
                      className="btn-secondary"
                      onClick={() =>
                        copyToClipboard(
                          `curl -X POST ${API_BASE_URL}/workflows/${currentWorkflow.id}/trigger/ -H "X-API-Key: ${currentWorkflow.api_key}" -H "Content-Type: application/json" -d '{"input": "your input text here"}'`,
                          'cURL command'
                        )
                      }
                      style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}
                    >
                      Copy Command
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div style={{ textAlign: 'right' }}>
              <button className="btn-primary" onClick={() => setShowTriggersModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History Modal */}
      {showHistoryModal && currentWorkflow && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => {
            setShowHistoryModal(false)
            setSelectedExecution(null)
          }}
        >
          <div
            style={{
              background: 'var(--card-bg)',
              borderRadius: '12px',
              padding: '2rem',
              maxWidth: '900px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto',
              boxShadow: '0 8px 32px var(--shadow-lg)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ marginTop: 0, marginBottom: '1.5rem', color: 'var(--text-primary)' }}>
              📊 Execution History
            </h2>

            {historyLoading ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                Loading history...
              </div>
            ) : executionHistory.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                No executions yet. Trigger your workflow via API to see history here.
              </div>
            ) : selectedExecution ? (
              <div>
                <button
                  className="btn-secondary"
                  onClick={() => setSelectedExecution(null)}
                  style={{ marginBottom: '1rem' }}
                >
                  ← Back to List
                </button>
                <div
                  style={{
                    padding: '1rem',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '8px',
                    marginBottom: '1rem',
                  }}
                >
                  <div style={{ marginBottom: '0.5rem' }}>
                    <strong style={{ color: 'var(--text-primary)' }}>Status:</strong>{' '}
                    <span
                      style={{
                        color:
                          selectedExecution.status === 'completed'
                            ? '#10b981'
                            : selectedExecution.status === 'error'
                            ? '#ef4444'
                            : '#f59e0b',
                      }}
                    >
                      {selectedExecution.status === 'completed' && '✓ '}
                      {selectedExecution.status === 'error' && '✗ '}
                      {selectedExecution.status}
                    </span>
                  </div>
                  <div style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                    <strong>Time:</strong> {new Date(selectedExecution.created_at).toLocaleString()}
                  </div>
                  {selectedExecution.execution_time && (
                    <div style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                      <strong>Duration:</strong> {selectedExecution.execution_time.toFixed(2)}s
                    </div>
                  )}
                  <div style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                    <strong>Triggered by:</strong> {selectedExecution.triggered_by}
                  </div>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '0.5rem' }}>
                    Input:
                  </strong>
                  <pre
                    style={{
                      padding: '0.75rem',
                      background: 'var(--bg-secondary)',
                      borderRadius: '4px',
                      fontSize: '0.85rem',
                      overflow: 'auto',
                      color: 'var(--text-primary)',
                      margin: 0,
                    }}
                  >
                    {selectedExecution.input_data}
                  </pre>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '0.5rem' }}>
                    Output:
                  </strong>
                  <pre
                    style={{
                      padding: '0.75rem',
                      background: 'var(--bg-secondary)',
                      borderRadius: '4px',
                      fontSize: '0.85rem',
                      overflow: 'auto',
                      color: 'var(--text-primary)',
                      margin: 0,
                    }}
                  >
                    {selectedExecution.final_output || 'No output'}
                  </pre>
                </div>

                {selectedExecution.error_message && (
                  <div style={{ marginBottom: '1rem' }}>
                    <strong style={{ color: '#ef4444', display: 'block', marginBottom: '0.5rem' }}>
                      Error:
                    </strong>
                    <pre
                      style={{
                        padding: '0.75rem',
                        background: '#fee2e2',
                        borderRadius: '4px',
                        fontSize: '0.85rem',
                        overflow: 'auto',
                        color: '#991b1b',
                        margin: 0,
                      }}
                    >
                      {selectedExecution.error_message}
                    </pre>
                  </div>
                )}

                {selectedExecution.trace && selectedExecution.trace.length > 0 && (
                  <div>
                    <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '0.5rem' }}>
                      Execution Trace ({selectedExecution.trace.length} steps):
                    </strong>
                    <pre
                      style={{
                        padding: '0.75rem',
                        background: 'var(--bg-secondary)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        overflow: 'auto',
                        color: 'var(--text-primary)',
                        margin: 0,
                        maxHeight: '300px',
                      }}
                    >
                      {JSON.stringify(selectedExecution.trace, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div>
                <table
                  style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                  }}
                >
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                      <th style={{ padding: '0.75rem', textAlign: 'left', color: 'var(--text-primary)' }}>
                        Time
                      </th>
                      <th style={{ padding: '0.75rem', textAlign: 'left', color: 'var(--text-primary)' }}>
                        Status
                      </th>
                      <th style={{ padding: '0.75rem', textAlign: 'left', color: 'var(--text-primary)' }}>
                        Input
                      </th>
                      <th style={{ padding: '0.75rem', textAlign: 'left', color: 'var(--text-primary)' }}>
                        Output
                      </th>
                      <th style={{ padding: '0.75rem', textAlign: 'left', color: 'var(--text-primary)' }}>
                        Duration
                      </th>
                      <th style={{ padding: '0.75rem', textAlign: 'center', color: 'var(--text-primary)' }}>
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {executionHistory.map((execution) => (
                      <tr
                        key={execution.id}
                        style={{
                          borderBottom: '1px solid var(--border-color)',
                        }}
                      >
                        <td
                          style={{
                            padding: '0.75rem',
                            fontSize: '0.85rem',
                            color: 'var(--text-primary)',
                          }}
                        >
                          {new Date(execution.created_at).toLocaleString()}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <span
                            style={{
                              fontSize: '0.85rem',
                              color:
                                execution.status === 'completed'
                                  ? '#10b981'
                                  : execution.status === 'error'
                                  ? '#ef4444'
                                  : '#f59e0b',
                            }}
                          >
                            {execution.status === 'completed' && '✓'}
                            {execution.status === 'error' && '✗'}
                            {execution.status === 'running' && '⏳'}
                          </span>
                        </td>
                        <td
                          style={{
                            padding: '0.75rem',
                            maxWidth: '200px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            fontSize: '0.85rem',
                            color: 'var(--text-secondary)',
                          }}
                        >
                          {execution.input_data}
                        </td>
                        <td
                          style={{
                            padding: '0.75rem',
                            maxWidth: '200px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            fontSize: '0.85rem',
                            color: 'var(--text-secondary)',
                          }}
                        >
                          {execution.final_output || '-'}
                        </td>
                        <td
                          style={{
                            padding: '0.75rem',
                            fontSize: '0.85rem',
                            color: 'var(--text-secondary)',
                          }}
                        >
                          {execution.execution_time ? `${execution.execution_time.toFixed(2)}s` : '-'}
                        </td>
                        <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                          <button
                            className="btn-secondary"
                            onClick={() => setSelectedExecution(execution)}
                            style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          >
                            Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div style={{ textAlign: 'right', marginTop: '1.5rem' }}>
              <button
                className="btn-primary"
                onClick={() => {
                  setShowHistoryModal(false)
                  setSelectedExecution(null)
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          <div className="toast-content">
            <span className="toast-icon">
              {toast.type === 'success' && '✓'}
              {toast.type === 'error' && '✕'}
              {toast.type === 'info' && 'ℹ'}
            </span>
            <span className="toast-message">{toast.message}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default FlowDiagram
