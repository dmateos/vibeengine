import { Handle, Position } from '@xyflow/react'

interface RedisNodeData {
  label: string
  icon: string
}

function RedisNode({ data }: { data: RedisNodeData }) {
  return (
    <div className="custom-node action-node redis-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Redis</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="s" />
      <Handle type="source" position={Position.Right} id="r" />
    </div>
  )
}

export default RedisNode
