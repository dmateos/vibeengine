import { Handle, Position } from '@xyflow/react'

interface HuggingFaceNodeData {
  label: string
  icon: string
}

function HuggingFaceNode({ data }: { data: HuggingFaceNodeData }) {
  return (
    <div className="custom-node action-node huggingface-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Hugging Face</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="b" />
    </div>
  )
}

export default HuggingFaceNode
