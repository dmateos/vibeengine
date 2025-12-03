import { Handle, Position } from '@xyflow/react'

interface SleepNodeData {
  label: string
  icon: string
}

function SleepNode({ data }: { data: SleepNodeData }) {
  return (
    <div className="custom-node control-node sleep-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Sleep</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="s" />
    </div>
  )
}

export default SleepNode
