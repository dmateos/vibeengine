import { Handle, Position } from '@xyflow/react'

interface TCPOutputNodeData {
  label: string
  icon: string
}

function TCPOutputNode({ data }: { data: TCPOutputNodeData }) {
  return (
    <div className="custom-node action-node tcp-output-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">TCP Output</div>
      </div>
    </div>
  )
}

export default TCPOutputNode
