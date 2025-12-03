import { Handle, Position } from '@xyflow/react'

interface WebScraperNodeData {
  label: string
  icon: string
}

function WebScraperNode({ data }: { data: WebScraperNodeData }) {
  return (
    <div className="custom-node action-node web-scraper-node">
      <Handle type="target" position={Position.Top} id="t" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type">Web Scraper</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="s" />
      <Handle type="source" position={Position.Right} id="r" />
    </div>
  )
}

export default WebScraperNode
