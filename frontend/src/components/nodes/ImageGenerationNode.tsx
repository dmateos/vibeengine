import { Handle, Position } from '@xyflow/react'

interface ImageGenerationNodeData {
  label: string
  icon: string
}

function ImageGenerationNode({ data }: { data: ImageGenerationNodeData }) {
  return (
    <div className="custom-node action-node image-generation-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Image Generation</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="s" />
      <Handle type="source" position={Position.Right} id="r" />
    </div>
  )
}

export default ImageGenerationNode
