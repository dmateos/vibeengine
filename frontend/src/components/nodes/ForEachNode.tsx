import { Handle, Position } from '@xyflow/react'

interface ForEachNodeData {
  label: string
  icon: string
}

function ForEachNode({ data }: { data: ForEachNodeData }) {
  return (
    <div className="custom-node control-node for-each-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">For Each</div>
      </div>
      {/* Body handle - connects to loop body start */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="body"
        style={{
          left: '50%',
          background: '#3b82f6',
          width: 12,
          height: 12
        }}
      />
      {/* Exit handle - connects to post-loop continuation */}
      <Handle
        type="source"
        position={Position.Right}
        id="exit"
        style={{
          top: '50%',
          background: '#10b981',
          width: 12,
          height: 12
        }}
      />
    </div>
  )
}

export default ForEachNode
