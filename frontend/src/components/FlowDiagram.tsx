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
  type Node,
  type Edge,
  type Connection,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './FlowDiagram.css'
import TriggerNode from './nodes/TriggerNode'
import ActionNode from './nodes/ActionNode'
import ConditionNode from './nodes/ConditionNode'

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
  trigger: TriggerNode,
  action: ActionNode,
  condition: ConditionNode,
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

  useEffect(() => {
    loadWorkflows()
    loadNodeTypes()
  }, [])

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
    } catch (error) {
      console.error('Error loading workflows:', error)
      setLoading(false)
    }
  }

  const loadWorkflow = (workflow: Workflow) => {
    setNodes(workflow.nodes)
    setEdges(workflow.edges)
    setCurrentWorkflow(workflow)
    setWorkflowName(workflow.name)
    setShowWorkflowList(false)
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
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node)
  }, [])

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
          fitView
          attributionPosition="bottom-left"
        >
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              switch (node.type) {
                case 'trigger':
                  return '#667eea'
                case 'action':
                  return '#10b981'
                case 'condition':
                  return '#f59e0b'
                default:
                  return '#cbd5e1'
              }
            }}
          />
          <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        </ReactFlow>
      </div>

      {selectedNode && (
        <div className="node-details">
          <h3>Node Details</h3>
          <div className="detail-item">
            <strong>Type:</strong> {selectedNode.type}
          </div>
          <div className="detail-item">
            <strong>Label:</strong> {(selectedNode.data as { label: string }).label}
          </div>
          <div className="detail-item">
            <strong>ID:</strong> {selectedNode.id}
          </div>
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
