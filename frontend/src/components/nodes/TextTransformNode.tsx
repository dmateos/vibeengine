import { Handle, Position } from '@xyflow/react'

interface TextTransformNodeData {
  label: string
  icon: string
}

function TextTransformNode({ data }: { data: TextTransformNodeData }) {
  return (
    <div className="custom-node action-node text-transform-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Text Transform</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="b" />
    </div>
  )
}

export default TextTransformNode
