import { Handle, Position } from '@xyflow/react'

interface OpenAIAgentNodeData {
  label: string
  icon: string
}

function OpenAIAgentNode({ data }: { data: OpenAIAgentNodeData }) {
  return (
    <div className="custom-node action-node openai-agent-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">OpenAI Agent</div>
      </div>
      {/* Main downward pipeline output */}
      <Handle type="source" position={Position.Bottom} id="s" />
      {/* Side output for lateral links (e.g., to Memory) */}
      <Handle type="source" position={Position.Right} id="r" />
    </div>
  )
}

export default OpenAIAgentNode
