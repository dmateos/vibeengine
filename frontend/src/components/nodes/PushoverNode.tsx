import { Handle, Position } from '@xyflow/react'

interface PushoverNodeData {
  label: string
  icon: string
}

function PushoverNode({ data }: { data: PushoverNodeData }) {
  return (
    <div className="custom-node action-node pushover-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Pushover</div>
      </div>
    </div>
  )
}

export default PushoverNode
