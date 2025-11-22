import { Handle, Position } from '@xyflow/react'

interface ActionNodeData {
  label: string
  icon: string
}

function ActionNode({ data }: { data: ActionNodeData }) {
  return (
    <div className="custom-node action-node">
      <Handle type="target" position={Position.Top} id="b" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Action</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="a" />
    </div>
  )
}

export default ActionNode
