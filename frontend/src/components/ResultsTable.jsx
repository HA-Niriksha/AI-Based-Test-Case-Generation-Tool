import { useState, useMemo } from 'react'

// Columns match the Excel output_generator.py structure exactly
const COLUMNS = [
  { key: 'traceability_req_id',  label: 'Requirement_ID',                 width: 130 },
  { key: 'test_case_id',         label: 'TC_ID',                          width: 120 },
  { key: 'scenario_id',          label: 'Scenario No',                    width: 100 },
  { key: 'module',               label: 'Module',                         width: 130 },
  { key: 'objective',            label: 'Test Objective',                  width: 300 },
  { key: 'preconditions',        label: 'Test Precondition',               width: 240 },
  { key: 'test_steps',           label: 'Test Steps',                      width: 280 },
  { key: 'inputs',               label: 'Inputs (Signal Values)',          width: 250 },
  { key: 'expected_outcome',     label: 'Expected Outputs',                width: 220 },
  { key: 'dependent_test_cases', label: 'Depands On',                     width: 120 },
  { key: 'remarks',              label: 'Remarks / Additional Information',width: 260 },
  { key: 'design_methodology',   label: 'Methodology',                    width: 170 },
  { key: 'requirement_type',     label: 'Req_Type',                       width: 120 },
  { key: 'scenario_type',        label: 'Scenario_Type',                  width: 120 },
]

function badge(type, value) {
  const map = {
    priority:         { P1: 'badge-p1', P2: 'badge-p2', P3: 'badge-p3' },
    scenario_type:    { normal: 'badge-normal', boundary: 'badge-boundary', edge: 'badge-edge', robustness: 'badge-robustness' },
    testing_type:     { verification: 'badge-verification', validation: 'badge-validation', integration: 'badge-integration' },
    requirement_type: { functional: 'badge-verification', 'non-functional': 'badge-boundary' },
    test_environment: { Dev: 'badge-normal', QA: 'badge-boundary', UAT: 'badge-validation', Prod: 'badge-robustness' },
  }
  const cls = map[type]?.[value]
  if (!cls) return <span className="text-xs text-dim">{value}</span>
  return <span className={`${cls} text-[10px] font-mono px-1.5 py-0.5 rounded`}>{value}</span>
}

function CellValue({ col, value }) {
  if (Array.isArray(value)) {
    // Steps already have 1. 2. 3. numbering — no bullet prefix needed
    return (
      <ol className="space-y-1 list-none m-0 p-0">
        {value.map((v, i) => (
          <li key={i} className="text-[11px] text-dim leading-snug">{v}</li>
        ))}
      </ol>
    )
  }
  const badgeCols = ['priority', 'scenario_type', 'testing_type', 'requirement_type', 'test_environment']
  if (badgeCols.includes(col.key)) return badge(col.key, value)
  if (['test_case_id', 'scenario_id', 'traceability_req_id', 'dependent_test_cases'].includes(col.key)) {
    return <span className="font-mono text-[11px] text-amber/90">{value}</span>
  }
  return <span className="text-[11px] text-dim leading-snug">{value}</span>
}

function unique(arr) {
  return ['All', ...Array.from(new Set(arr)).sort()]
}

export default function ResultsTable({ testCases }) {
  const [filters, setFilters] = useState({ module: 'All', priority: 'All', scenario_type: 'All', testing_type: 'All', requirement_type: 'All' })
  const [search, setSearch]   = useState('')
  const [page, setPage]       = useState(1)
  const PAGE_SIZE = 50

  const opts = useMemo(() => ({
    module:           unique(testCases.map(t => t.module)),
    priority:         unique(testCases.map(t => t.priority)),
    scenario_type:    unique(testCases.map(t => t.scenario_type)),
    testing_type:     unique(testCases.map(t => t.testing_type)),
    requirement_type: unique(testCases.map(t => t.requirement_type)),
  }), [testCases])

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return testCases.filter(tc => {
      if (filters.module           !== 'All' && tc.module           !== filters.module)           return false
      if (filters.priority         !== 'All' && tc.priority         !== filters.priority)         return false
      if (filters.scenario_type    !== 'All' && tc.scenario_type    !== filters.scenario_type)    return false
      if (filters.testing_type     !== 'All' && tc.testing_type     !== filters.testing_type)     return false
      if (filters.requirement_type !== 'All' && tc.requirement_type !== filters.requirement_type) return false
      if (q && !JSON.stringify(tc).toLowerCase().includes(q))                                     return false
      return true
    })
  }, [testCases, filters, search])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paged      = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const setFilter = (k, v) => { setFilters(f => ({ ...f, [k]: v })); setPage(1) }

  const FilterSelect = ({ k, label }) => (
    <div className="flex flex-col gap-1">
      <label className="text-[10px] text-muted font-mono uppercase tracking-widest">{label}</label>
      <select
        value={filters[k]}
        onChange={e => setFilter(k, e.target.value)}
        className="bg-card border border-border text-dim text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-amber/50 cursor-pointer"
      >
        {opts[k].map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  )

  return (
    <div className="fade-in space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded bg-amber/10 border border-amber/30 flex items-center justify-center text-amber text-sm font-mono font-bold">4</div>
          <h2 className="text-base font-semibold text-text">
            Test Cases
            <span className="ml-2 font-mono text-xs text-muted">
              {filtered.length} / {testCases.length}
            </span>
          </h2>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-card border border-border rounded-xl p-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex flex-col gap-1 flex-1 min-w-[160px]">
            <label className="text-[10px] text-muted font-mono uppercase tracking-widest">Search</label>
            <input
              type="text"
              placeholder="Search any field…"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
              className="bg-surface border border-border text-dim text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-amber/50"
            />
          </div>
          <FilterSelect k="module"           label="Module" />
          <FilterSelect k="priority"         label="Priority" />
          <FilterSelect k="scenario_type"    label="Scenario" />
          <FilterSelect k="testing_type"     label="Testing Type" />
          <FilterSelect k="requirement_type" label="Req Type" />
          <button
            onClick={() => { setFilters({ module: 'All', priority: 'All', scenario_type: 'All', testing_type: 'All', requirement_type: 'All' }); setSearch(''); setPage(1) }}
            className="text-xs text-muted hover:text-amber transition-colors self-end pb-1.5"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border overflow-auto" style={{ maxHeight: '65vh' }}>
        <table className="w-full border-collapse" style={{ minWidth: 2400 }}>
          <thead>
            <tr>
              {COLUMNS.map(col => (
                <th key={col.key} className="tc-header" style={{ minWidth: col.width }}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((tc, rowIdx) => (
              <tr
                key={tc.test_case_id + rowIdx}
                className={`transition-colors hover:bg-surface/60 ${rowIdx % 2 === 0 ? 'bg-transparent' : 'bg-surface/30'}`}
              >
                {COLUMNS.map(col => (
                  <td key={col.key} className="tc-cell" style={{ minWidth: col.width }}>
                    <CellValue col={col} value={tc[col.key]} />
                  </td>
                ))}
              </tr>
            ))}
            {paged.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length} className="tc-cell text-center text-muted py-12">
                  No test cases match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-dim font-mono">
            Page {page} of {totalPages}  ·  showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
          </p>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
              className="px-3 py-1 text-xs rounded-lg border border-border text-dim hover:border-amber/50 hover:text-amber disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              ← Prev
            </button>
            <button
              disabled={page === totalPages}
              onClick={() => setPage(p => p + 1)}
              className="px-3 py-1 text-xs rounded-lg border border-border text-dim hover:border-amber/50 hover:text-amber disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
