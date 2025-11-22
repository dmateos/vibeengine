import { Handle, Position } from '@xyflow/react'

interface MemoryNodeData {
  label: string
  icon: string
}

function MemoryNode({ data }: { data: MemoryNodeData }) {
  return (
    <div className="custom-node action-node">
      <Handle type="target" position={Position.Left} id="read" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Memory</div>
      </div>
      <Handle type="source" position={Position.Right} id="write" />
    </div>
  )
}

export default MemoryNode
