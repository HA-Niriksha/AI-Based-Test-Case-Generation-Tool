import { useState, useRef, useCallback } from 'react'

const ACCEPTED = ['.pdf', '.docx', '.xlsx']
const ICONS = {
  pdf:  '📄',
  docx: '📝',
  doc:  '📝',
  xlsx: '📊',
  xls:  '📊',
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(2)} MB`
}

export default function UploadPanel({ onUploaded }) {
  const [dragging, setDragging] = useState(false)
  const [file, setFile]         = useState(null)
  const [preview, setPreview]   = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const inputRef = useRef()

  const handleFile = useCallback(async (f) => {
    if (!f) return
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    if (!ACCEPTED.includes(ext)) {
      setError(`Unsupported type: ${ext}. Use ${ACCEPTED.join(', ')}`)
      return
    }
    setError('')
    setFile(f)
    setLoading(true)

    const form = new FormData()
    form.append('file', f)

    try {
      const res = await fetch('/api/upload', { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail?.error || 'Upload failed')
      setPreview(data.text_preview)
      onUploaded(data)
    } catch (e) {
      setError(e.message)
      setFile(null)
    } finally {
      setLoading(false)
    }
  }, [onUploaded])

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  const ext = file?.name?.split('.').pop()?.toLowerCase()
  const icon = ICONS[ext] || '📁'

  return (
    <div className="fade-in">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-7 h-7 rounded bg-amber/10 border border-amber/30 flex items-center justify-center text-amber text-sm font-mono font-bold">1</div>
        <h2 className="text-base font-semibold text-text">Upload SRS Document</h2>
      </div>

      <div
        className={`drop-zone rounded-xl p-8 text-center cursor-pointer select-none ${dragging ? 'drag-over' : ''}`}
        onClick={() => inputRef.current.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.xlsx"
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
        />

        {loading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-amber border-t-transparent rounded-full spin" />
            <p className="text-dim text-sm">Parsing document…</p>
          </div>
        ) : file ? (
          <div className="flex flex-col items-center gap-2">
            <span className="text-4xl">{icon}</span>
            <p className="text-text font-medium">{file.name}</p>
            <p className="text-dim text-xs font-mono">{formatBytes(file.size)}</p>
            <p className="text-amber text-xs mt-1">✓ Uploaded — click to replace</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-xl border border-border flex items-center justify-center text-3xl bg-card">
              📋
            </div>
            <div>
              <p className="text-text font-medium">Drop your SRS document here</p>
              <p className="text-dim text-sm mt-1">or click to browse</p>
            </div>
            <div className="flex gap-2 mt-1">
              {ACCEPTED.map(e => (
                <span key={e} className="px-2 py-0.5 rounded text-xs font-mono bg-border text-dim">{e}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-3 px-4 py-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          ⚠ {error}
        </div>
      )}

      {preview && (
        <div className="mt-4">
          <p className="text-xs text-muted mb-1.5 font-mono uppercase tracking-widest">Preview (first 500 chars)</p>
          <pre className="bg-card border border-border rounded-lg p-3 text-xs text-dim font-mono overflow-auto max-h-32 whitespace-pre-wrap">
            {preview}
          </pre>
        </div>
      )}
    </div>
  )
}
