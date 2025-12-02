import { Handle, Position } from '@xyflow/react'

interface CronTriggerNodeData {
  label: string
  icon: string
  cronExpression?: string
}

function CronTriggerNode({ data }: { data: CronTriggerNodeData }) {
  return (
    <div className="custom-node trigger-node cron-trigger-node">
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Cron Trigger</div>
        {data.cronExpression && (
          <div className="node-description" style={{ fontSize: '10px', opacity: 0.7 }}>
            {data.cronExpression}
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} id="s" />
    </div>
  )
}

export default CronTriggerNode
