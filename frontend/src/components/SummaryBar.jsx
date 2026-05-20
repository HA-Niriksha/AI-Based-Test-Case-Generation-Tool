function StatCard({ label, value, accent }) {
  return (
    <div className="bg-card border border-border rounded-lg px-4 py-3 flex flex-col gap-1 min-w-[100px]">
      <p className={`text-2xl font-bold font-mono ${accent || 'text-amber'}`}>{value}</p>
      <p className="text-xs text-dim uppercase tracking-wide">{label}</p>
    </div>
  )
}

function GroupBar({ label, data, colorMap }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0)
  return (
    <div className="bg-card border border-border rounded-lg px-4 py-3">
      <p className="text-xs text-muted uppercase tracking-widest mb-2 font-mono">{label}</p>
      <div className="space-y-1.5">
        {Object.entries(data).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
          <div key={k} className="flex items-center gap-2">
            <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${colorMap?.[k] || 'bg-border text-dim'}`} style={{minWidth:80}}>
              {k}
            </span>
            <div className="flex-1 bg-surface rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full bg-amber rounded-full transition-all duration-500"
                style={{ width: total ? `${(v / total) * 100}%` : '0%' }}
              />
            </div>
            <span className="text-xs font-mono text-dim w-6 text-right">{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

const SCENARIO_COLORS = {
  normal:     'badge-normal',
  boundary:   'badge-boundary',
  edge:       'badge-edge',
  robustness: 'badge-robustness',
}
const TESTING_COLORS = {
  verification: 'badge-verification',
  validation:   'badge-validation',
  integration:  'badge-integration',
}
const PRIORITY_COLORS = {
  P1: 'badge-p1',
  P2: 'badge-p2',
  P3: 'badge-p3',
}

export default function SummaryBar({ summary }) {
  if (!summary) return null
  return (
    <div className="fade-in space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 rounded bg-amber/10 border border-amber/30 flex items-center justify-center text-amber text-sm font-mono font-bold">✓</div>
        <h2 className="text-base font-semibold text-text">Generation Summary</h2>
      </div>

      {/* Top stats */}
      <div className="flex flex-wrap gap-3">
        <StatCard label="Total Test Cases"  value={summary.total}              accent="text-amber" />
        <StatCard label="Duplicates Removed" value={summary.duplicates_removed} accent="text-red-400" />
        <StatCard label="Modules Detected"  value={Object.keys(summary.by_module).length} accent="text-blue-400" />
      </div>

      {/* Distribution grids */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <GroupBar label="By Scenario Type" data={summary.by_scenario_type} colorMap={SCENARIO_COLORS} />
        <GroupBar label="By Testing Type"  data={summary.by_testing_type}  colorMap={TESTING_COLORS}  />
        <GroupBar label="By Priority"      data={summary.by_priority}      colorMap={PRIORITY_COLORS} />
        <GroupBar label="By Req Type"      data={summary.by_requirement_type} colorMap={{}} />
        <GroupBar label="By Module"        data={summary.by_module}        colorMap={{}} />
      </div>
    </div>
  )
}
