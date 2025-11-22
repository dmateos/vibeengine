import { Handle, Position } from '@xyflow/react'

interface ConditionNodeData {
  label: string
  icon: string
}

function ConditionNode({ data }: { data: ConditionNodeData }) {
  return (
    <div className="custom-node condition-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Condition</div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        id="yes"
        style={{ left: '30%' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="no"
        style={{ left: '70%' }}
      />
    </div>
  )
}

export default ConditionNode
