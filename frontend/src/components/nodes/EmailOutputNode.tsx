import { Handle, Position } from '@xyflow/react'

interface EmailOutputNodeData {
  label: string
  icon: string
}

function EmailOutputNode({ data }: { data: EmailOutputNodeData }) {
  return (
    <div className="custom-node action-node email-output-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Email Output</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="s" />
      <Handle type="source" position={Position.Right} id="r" />
    </div>
  )
}

export default EmailOutputNode
