import { Handle, Position } from '@xyflow/react'

interface TriggerNodeData {
  label: string
  icon: string
}

function TriggerNode({ data }: { data: TriggerNodeData }) {
  return (
    <div className="custom-node trigger-node">
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Trigger</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="a" />
    </div>
  )
}

export default TriggerNode
