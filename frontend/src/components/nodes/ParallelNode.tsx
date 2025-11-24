import { Handle, Position } from '@xyflow/react'

interface ParallelNodeData {
  label: string
  icon: string
  branchCount?: number
}

function ParallelNode({ data }: { data: ParallelNodeData }) {
  // Default to 3 branches if not specified
  const branchCount = data.branchCount || 3

  // Calculate positions for branch handles
  const getBranchPosition = (index: number) => {
    const spacing = 100 / (branchCount + 1)
    return `${spacing * (index + 1)}%`
  }

  return (
    <div className="custom-node condition-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Parallel</div>
      </div>
      {Array.from({ length: branchCount }).map((_, i) => (
        <Handle
          key={`branch_${i}`}
          type="source"
          position={Position.Bottom}
          id={`branch_${i}`}
          style={{ left: getBranchPosition(i) }}
        />
      ))}
    </div>
  )
}

export default ParallelNode
