import { Handle, Position } from '@xyflow/react'

interface ClaudeAgentNodeData {
  label: string
  icon: string
}

function ClaudeAgentNode({ data }: { data: ClaudeAgentNodeData }) {
  return (
    <div className="custom-node action-node claude-agent-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Claude Agent</div>
      </div>
      {/* Main downward pipeline output */}
      <Handle type="source" position={Position.Bottom} id="s" />
      {/* Side output for lateral links (e.g., to Memory) */}
      <Handle type="source" position={Position.Right} id="r" />
    </div>
  )
}

export default ClaudeAgentNode
