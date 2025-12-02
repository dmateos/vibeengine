import { Handle, Position } from '@xyflow/react'

interface SSHCommandNodeData {
  label: string
  icon: string
}

function SSHCommandNode({ data }: { data: SSHCommandNodeData }) {
  return (
    <div className="custom-node action-node code-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">SSH Command</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="b" />
    </div>
  )
}

export default SSHCommandNode
