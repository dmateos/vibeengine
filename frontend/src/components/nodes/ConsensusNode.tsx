import { Handle, Position } from '@xyflow/react'

interface ConsensusNodeData {
  label: string
  icon: string
  method?: 'exact' | 'semantic' | 'llm_judge'
  threshold?: string | number
}

function ConsensusNode({ data }: { data: ConsensusNodeData }) {
  const method = data.method || 'llm_judge'
  const threshold = data.threshold || 'majority'

  const methodLabel = {
    'exact': 'Exact',
    'semantic': 'Semantic',
    'llm_judge': 'LLM Judge'
  }[method] || 'LLM Judge'

  return (
    <div className="custom-node action-node">
      <Handle type="target" position={Position.Top} id="t" />
      {method === 'llm_judge' && (
        <>
          <Handle
            type="target"
            position={Position.Left}
            id="judge-left"
            style={{ top: '50%', background: '#ec4899' }}
          />
          <Handle
            type="target"
            position={Position.Right}
            id="judge-right"
            style={{ top: '50%', background: '#ec4899' }}
          />
        </>
      )}
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">
          {methodLabel} · {threshold}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} id="s" />
    </div>
  )
}

export default ConsensusNode
