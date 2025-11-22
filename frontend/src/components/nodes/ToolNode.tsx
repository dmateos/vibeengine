import { Handle, Position } from '@xyflow/react'

interface ToolNodeData {
  label: string
  icon: string
}

function ToolNode({ data }: { data: ToolNodeData }) {
  return (
    <div className="custom-node action-node">
      <Handle type="target" position={Position.Left} id="in" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Tool</div>
      </div>
      <Handle type="source" position={Position.Right} id="out" />
    </div>
  )
}

export default ToolNode
