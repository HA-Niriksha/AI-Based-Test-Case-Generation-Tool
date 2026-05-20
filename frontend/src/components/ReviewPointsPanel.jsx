const REVIEW_POINTS = [
  {
    id: 'rp1',
    label: 'Segregate by Module & Requirement Type',
    desc: 'Detect modules (Login, Payment, API…) and classify functional vs non-functional',
  },
  {
    id: 'rp2',
    label: 'Full Scenario Coverage',
    desc: 'Generate Normal, Boundary, Edge, and Robustness test cases for every requirement',
  },
  {
    id: 'rp3',
    label: 'Map to Testing Type',
    desc: 'Assign Verification, Validation, or Integration based on requirement context',
  },
  {
    id: 'rp4',
    label: 'Rule-Based Remarks',
    desc: 'Auto-detect security risks, PCI concerns, external dependencies, and missing specs',
  },
  {
    id: 'rp5',
    label: 'Deduplicate Test Cases',
    desc: 'Remove similar objectives (similarity threshold ≥ 0.85) using sequence matching',
  },
]

export default function ReviewPointsPanel({ reviewPoints, onChange, disabled }) {
  return (
    <div className="fade-in">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-7 h-7 rounded bg-amber/10 border border-amber/30 flex items-center justify-center text-amber text-sm font-mono font-bold">2</div>
        <h2 className="text-base font-semibold text-text">Review Points</h2>
      </div>

      <div className="space-y-2">
        {REVIEW_POINTS.map((rp, i) => {
          const enabled = reviewPoints[rp.id]
          return (
            <label
              key={rp.id}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all
                ${enabled
                  ? 'border-amber/30 bg-amber/5'
                  : 'border-border bg-card'}
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-amber/40'}
              `}
            >
              <div className="mt-0.5 flex-shrink-0">
                <div
                  className={`w-4.5 h-4.5 w-[18px] h-[18px] rounded border flex items-center justify-center transition-all
                    ${enabled ? 'bg-amber border-amber' : 'bg-transparent border-border'}
                  `}
                >
                  {enabled && <span className="text-bg text-[10px] font-bold leading-none">✓</span>}
                </div>
              </div>
              <input
                type="checkbox"
                className="hidden"
                checked={enabled}
                disabled={disabled}
                onChange={() => !disabled && onChange(rp.id, !enabled)}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-amber/70 bg-amber/10 px-1.5 py-0.5 rounded">RP{i + 1}</span>
                  <span className="text-sm font-medium text-text">{rp.label}</span>
                </div>
                <p className="text-xs text-dim mt-0.5 leading-relaxed">{rp.desc}</p>
              </div>
            </label>
          )
        })}
      </div>
    </div>
  )
}
