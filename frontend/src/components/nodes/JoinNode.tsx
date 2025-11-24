import { Handle, Position } from '@xyflow/react'

interface JoinNodeData {
  label: string
  icon: string
  merge_strategy?: 'list' | 'concat' | 'first' | 'last' | 'merge'
}

function JoinNode({ data }: { data: JoinNodeData }) {
  const strategyLabel = data.merge_strategy || 'list'

  return (
    <div className="custom-node action-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Join ({strategyLabel})</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="s" />
    </div>
  )
}

export default JoinNode
