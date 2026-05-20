import { useState } from 'react'
import UploadPanel       from './components/UploadPanel'
import ReviewPointsPanel from './components/ReviewPointsPanel'
import SummaryBar        from './components/SummaryBar'
import ResultsTable      from './components/ResultsTable'

const DEFAULT_RP = { rp1: true, rp2: true, rp3: true, rp4: true, rp5: true }

function ExportButton({ label, href, disabled, color }) {
  return (
    <a
      href={disabled ? undefined : href}
      className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium border transition-all
        ${disabled
          ? 'opacity-30 cursor-not-allowed border-border text-dim'
          : color === 'green'
            ? 'border-green-500/40 text-green-400 bg-green-500/10 hover:bg-green-500/20 cursor-pointer'
            : 'border-blue-500/40 text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 cursor-pointer'
        }`}
      download
    >
      {label}
    </a>
  )
}

export default function App() {
  const [uploadData,   setUploadData]   = useState(null)
  const [reviewPoints, setReviewPoints] = useState(DEFAULT_RP)
  const [generating,   setGenerating]   = useState(false)
  const [testCases,    setTestCases]    = useState([])
  const [summary,      setSummary]      = useState(null)
  const [error,        setError]        = useState('')
  const [progress,     setProgress]     = useState('')

  const handleRpChange = (id, val) =>
    setReviewPoints(rp => ({ ...rp, [id]: val }))

  const handleGenerate = async () => {
    if (!uploadData?.session_id) return
    setGenerating(true)
    setError('')
    setTestCases([])
    setSummary(null)
    setProgress('Analysing document…')

    try {
      setProgress('Ingesting requirements…')
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: uploadData.session_id,
          review_points: reviewPoints,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data?.detail?.error || data?.detail || 'Generation failed')
      }
      setProgress('Applying deduplication…')
      setTestCases(data.test_cases)
      setSummary(data.summary)
    } catch (e) {
      setError(e.message)
    } finally {
      setGenerating(false)
      setProgress('')
    }
  }

  const sessionId = uploadData?.session_id

  return (
    <div className="min-h-screen bg-bg text-text font-sans">

      {/* Header */}
      <header className="border-b border-border bg-surface sticky top-0 z-50">
        <div className="max-w-screen-2xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber/10 border border-amber/30 flex items-center justify-center">
              <span className="text-amber text-sm">⚙</span>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-text leading-none">Test Case Generator</h1>
              <p className="text-[10px] text-dim font-mono">Rule-Based NLP · No API · No LLM</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
            <span className="text-xs text-dim font-mono">offline engine</span>
          </div>
        </div>
      </header>

      <div className="max-w-screen-2xl mx-auto px-6 py-8 space-y-8">

        {/* Top grid: upload + review points + generate */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Upload */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <UploadPanel onUploaded={setUploadData} />
          </div>

          {/* Review points + generate */}
          <div className="bg-card border border-border rounded-2xl p-6 flex flex-col gap-6">
            <ReviewPointsPanel
              reviewPoints={reviewPoints}
              onChange={handleRpChange}
              disabled={generating}
            />

            {/* Step 3 — Generate */}
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-7 h-7 rounded bg-amber/10 border border-amber/30 flex items-center justify-center text-amber text-sm font-mono font-bold">3</div>
                <h2 className="text-base font-semibold text-text">Generate</h2>
              </div>

              <button
                onClick={handleGenerate}
                disabled={!uploadData || generating}
                className={`w-full py-3 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2
                  ${!uploadData || generating
                    ? 'bg-border text-muted cursor-not-allowed'
                    : 'bg-amber hover:bg-amber2 text-bg cursor-pointer shadow-lg shadow-amber/20'
                  }`}
              >
                {generating ? (
                  <>
                    <div className="w-4 h-4 border-2 border-bg border-t-transparent rounded-full spin" />
                    {progress || 'Generating…'}
                  </>
                ) : (
                  <>⚙ Generate Test Cases</>
                )}
              </button>

              {!uploadData && (
                <p className="text-center text-xs text-muted mt-2">Upload a document first</p>
              )}

              {error && (
                <div className="mt-3 px-4 py-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                  ⚠ {error}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Summary */}
        {summary && (
          <div className="bg-card border border-border rounded-2xl p-6">
            <SummaryBar summary={summary} />
          </div>
        )}

        {/* Export buttons */}
        {testCases.length > 0 && (
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-7 h-7 rounded bg-amber/10 border border-amber/30 flex items-center justify-center text-amber text-sm font-mono font-bold">5</div>
              <h2 className="text-base font-semibold text-text">Export</h2>
            </div>
            <div className="flex flex-wrap gap-3">
              <ExportButton
                label="📥 Download Excel (.xlsx)"
                href={`/api/export/excel?session_id=${sessionId}`}
                disabled={!sessionId}
                color="green"
              />
              <ExportButton
                label="📄 Download Word (.docx)"
                href={`/api/export/docx?session_id=${sessionId}`}
                disabled={!sessionId}
                color="blue"
              />
            </div>
          </div>
        )}

        {/* Results table */}
        {testCases.length > 0 && (
          <div className="bg-card border border-border rounded-2xl p-6">
            <ResultsTable testCases={testCases} />
          </div>
        )}

      </div>
    </div>
  )
}
