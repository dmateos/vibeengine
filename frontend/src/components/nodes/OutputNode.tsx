import { Handle, Position } from '@xyflow/react'

interface OutputNodeData {
  label: string
  icon: string
}

function OutputNode({ data }: { data: OutputNodeData }) {
  return (
    <div className="custom-node action-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Output</div>
      </div>
    </div>
  )
}

export default OutputNode

