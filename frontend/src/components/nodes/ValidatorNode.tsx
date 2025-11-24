import { Handle, Position } from '@xyflow/react'

interface ValidatorNodeData {
  label: string
  icon: string
}

function ValidatorNode({ data }: { data: ValidatorNodeData }) {
  return (
    <div className="custom-node validator-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Validator</div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        id="valid"
        style={{ left: '30%' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="invalid"
        style={{ left: '70%' }}
      />
    </div>
  )
}

export default ValidatorNode
