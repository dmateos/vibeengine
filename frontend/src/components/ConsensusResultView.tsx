import { useState } from 'react'

interface ConsensusResult {
  consensus: boolean
  agreement_rate: number
  answer: any
  analysis: string
  responses?: any[]
  disagreements?: any[]
}

interface ConsensusResultViewProps {
  result: ConsensusResult
}

function ConsensusResultView({ result }: ConsensusResultViewProps) {
  const [showAllResponses, setShowAllResponses] = useState(false)
  const [showDisagreements, setShowDisagreements] = useState(false)

  const agreementPercentage = Math.round(result.agreement_rate * 100)
  const totalResponses = result.responses?.length || 0
  const agreeingCount = totalResponses - (result.disagreements?.length || 0)

  return (
    <div className="consensus-result-view">
      {/* Header */}
      <div className="consensus-header">
        <div className="consensus-title">
          🤝 Consensus Analysis
        </div>
      </div>

      {/* Status */}
      <div className={`consensus-status ${result.consensus ? 'consensus-yes' : 'consensus-no'}`}>
        <div className="consensus-status-icon">
          {result.consensus ? '✅' : '❌'}
        </div>
        <div className="consensus-status-text">
          {result.consensus ? 'CONSENSUS REACHED' : 'NO CONSENSUS'}
        </div>
      </div>

      {/* Agreement Metrics */}
      <div className="consensus-metrics">
        <div className="consensus-metric">
          <div className="metric-label">Agreement Rate</div>
          <div className="metric-value">
            {agreeingCount}/{totalResponses} responses ({agreementPercentage}%)
          </div>
        </div>

        {/* Progress Bar */}
        <div className="consensus-progress-bar">
          <div
            className="consensus-progress-fill"
            style={{
              width: `${agreementPercentage}%`,
              background: result.consensus
                ? 'linear-gradient(90deg, #10b981 0%, #059669 100%)'
                : 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)'
            }}
          />
        </div>
      </div>

      {/* Consensus Answer */}
      <div className="consensus-section">
        <div className="section-header">💡 Consensus Answer</div>
        <div className="consensus-answer-box">
          {typeof result.answer === 'string'
            ? result.answer
            : JSON.stringify(result.answer, null, 2)}
        </div>
      </div>

      {/* Analysis */}
      {result.analysis && (
        <div className="consensus-section">
          <div className="section-header">📝 Analysis</div>
          <div className="consensus-analysis">
            {result.analysis}
          </div>
        </div>
      )}

      {/* Agreeing Responses */}
      {result.responses && result.responses.length > 0 && (
        <div className="consensus-section">
          <div
            className="section-header section-header-clickable"
            onClick={() => setShowAllResponses(!showAllResponses)}
          >
            <span>✓ Agreeing Responses ({agreeingCount})</span>
            <span className="toggle-arrow">{showAllResponses ? '▼' : '▶'}</span>
          </div>
          {showAllResponses && (
            <div className="consensus-responses">
              {result.responses
                .filter((resp) => {
                  // Filter out disagreements
                  if (!result.disagreements) return true
                  return !result.disagreements.some(dis =>
                    JSON.stringify(dis) === JSON.stringify(resp)
                  )
                })
                .map((resp, idx) => (
                  <div key={idx} className="consensus-response-item consensus-response-agree">
                    <div className="response-number">Response {idx + 1}</div>
                    <div className="response-content">
                      {typeof resp === 'string'
                        ? resp
                        : JSON.stringify(resp, null, 2)}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* Disagreeing Responses */}
      {result.disagreements && result.disagreements.length > 0 && (
        <div className="consensus-section">
          <div
            className="section-header section-header-clickable"
            onClick={() => setShowDisagreements(!showDisagreements)}
          >
            <span>✗ Disagreeing Responses ({result.disagreements.length})</span>
            <span className="toggle-arrow">{showDisagreements ? '▼' : '▶'}</span>
          </div>
          {showDisagreements && (
            <div className="consensus-responses">
              {result.disagreements.map((resp, idx) => (
                <div key={idx} className="consensus-response-item consensus-response-disagree">
                  <div className="response-number">Response {idx + 1}</div>
                  <div className="response-content">
                    {typeof resp === 'string'
                      ? resp
                      : JSON.stringify(resp, null, 2)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Raw Data (collapsible) */}
      <details className="consensus-raw-data">
        <summary className="section-header" style={{ cursor: 'pointer' }}>
          🔍 Raw Data
        </summary>
        <pre className="consensus-raw-data-content">
          {JSON.stringify(result, null, 2)}
        </pre>
      </details>
    </div>
  )
}

export default ConsensusResultView
