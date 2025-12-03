import { Handle, Position } from '@xyflow/react'

interface LoopNodeData {
  label: string
  icon: string
}

function LoopNode({ data }: { data: LoopNodeData }) {
  return (
    <div className="custom-node control-node loop-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Loop</div>
      </div>
      {/* Body handle - connects to loop body start */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="body"
        style={{
          left: '50%',
          background: '#7c3aed',
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

export default LoopNode
