import { Handle, Position } from '@xyflow/react'

interface HTMLOutputNodeData {
  label: string
  icon: string
}

function HTMLOutputNode({ data }: { data: HTMLOutputNodeData }) {
  return (
    <div className="custom-node output-node html-output-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">HTML Output</div>
      </div>
    </div>
  )
}

export default HTMLOutputNode
