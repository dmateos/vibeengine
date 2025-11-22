import { useCallback, useState } from 'react'
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

const nodeTypes = {
  trigger: TriggerNode,
  action: ActionNode,
  condition: ConditionNode,
}

const initialNodes: Node[] = [
  {
    id: '1',
    type: 'trigger',
    data: { label: 'When an item is created', icon: '⚡' },
    position: { x: 250, y: 50 },
  },
  {
    id: '2',
    type: 'action',
    data: { label: 'Get item details', icon: '📄' },
    position: { x: 250, y: 180 },
  },
  {
    id: '3',
    type: 'condition',
    data: { label: 'Is priority high?', icon: '❓' },
    position: { x: 250, y: 310 },
  },
  {
    id: '4',
    type: 'action',
    data: { label: 'Send email notification', icon: '📧' },
    position: { x: 100, y: 480 },
  },
  {
    id: '5',
    type: 'action',
    data: { label: 'Create task', icon: '✅' },
    position: { x: 400, y: 480 },
  },
  {
    id: '6',
    type: 'action',
    data: { label: 'Log to database', icon: '💾' },
    position: { x: 250, y: 610 },
  },
]

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e2-3', source: '2', target: '3', animated: true },
  {
    id: 'e3-4',
    source: '3',
    target: '4',
    label: 'Yes',
    animated: true,
    style: { stroke: '#10b981' },
  },
  {
    id: 'e3-5',
    source: '3',
    target: '5',
    label: 'No',
    animated: true,
    style: { stroke: '#ef4444' },
  },
  { id: 'e4-6', source: '4', target: '6', animated: true },
  { id: 'e5-6', source: '5', target: '6', animated: true },
]

function FlowDiagram() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)

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
        <h2>Workflow Designer</h2>
        <div className="flow-actions">
          <button className="btn-secondary">Add Node</button>
          <button className="btn-primary">Save Workflow</button>
        </div>
      </div>

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
