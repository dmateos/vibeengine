import { Handle, Position } from '@xyflow/react'

interface MCPToolNodeData {
  label: string
  icon: string
}

function MCPToolNode({ data }: { data: MCPToolNodeData }) {
  return (
    <div className="custom-node action-node" style={{ borderColor: '#6366f1' }}>
      <Handle type="target" position={Position.Left} id="in" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">MCP Tool</div>
      </div>
      <Handle type="source" position={Position.Right} id="out" />
    </div>
  )
}

export default MCPToolNode
