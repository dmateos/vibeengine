import { Handle, Position } from '@xyflow/react'

interface InputNodeData {
  label: string
  icon: string
}

function InputNode({ data }: { data: InputNodeData }) {
  return (
    <div className="custom-node trigger-node">
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Input</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="s" />
    </div>
  )
}

export default InputNode

