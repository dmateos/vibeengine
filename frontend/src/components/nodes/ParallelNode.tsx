import { Handle, Position, useEdges } from '@xyflow/react'

interface ParallelNodeData {
  label: string
  icon: string
}

interface ParallelNodeProps {
  id: string
  data: ParallelNodeData
}

function ParallelNode({ id, data }: ParallelNodeProps) {
  const edges = useEdges()

  // Count how many connections are currently coming from this node
  const connectedBranches = edges.filter(edge => edge.source === id).length

  // Show connected branches + 1 extra, minimum 3
  const handleCount = Math.max(3, connectedBranches + 1)

  return (
    <div className="custom-node condition-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Parallel · {connectedBranches} branches</div>
      </div>
      {/* Single visual handle that represents all branch connections */}
      {Array.from({ length: handleCount }).map((_, i) => (
        <Handle
          key={i}
          type="source"
          position={Position.Bottom}
          id={`branch_${i}`}
          style={{ left: `${((i + 1) * 100) / (handleCount + 1)}%` }}
        />
      ))}
    </div>
  )
}

export default ParallelNode
