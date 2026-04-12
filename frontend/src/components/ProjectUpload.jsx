import { useState } from 'react'
import { uploadProject } from '../api'

export default function ProjectUpload({ onUploaded }) {
  const [file,         setFile]         = useState(null)
  const [versionLabel, setVersionLabel] = useState('v1')
  const [status,       setStatus]       = useState('idle')
  const [result,       setResult]       = useState(null)
  const [error,        setError]        = useState(null)

  async function handleUpload() {
  if (!file) return
  setStatus('loading')
  setError(null)
  try {
    const data = await uploadProject(file, versionLabel)
    setResult(data)
    setStatus('success')
    if (onUploaded) onUploaded(data)
  } catch (err) {
    setError(err.response?.data?.detail || err.message)
    setStatus('error')
  }
}

  return (
    <div style={styles.card}>
      <h2 style={styles.heading}>Upload project ZIP</h2>
      <p style={styles.description}>
        Upload a Rockwell project ZIP file. All programs and routines will be
        scanned and stored for comparison.
      </p>

      <div style={styles.row}>
        <div style={styles.field}>
          <label style={styles.label}>Version label</label>
          <input
            type="text"
            value={versionLabel}
            onChange={e => setVersionLabel(e.target.value)}
            placeholder="e.g. v1, baseline, after-change"
            style={styles.input}
          />
        </div>
      </div>

      <div style={styles.uploadRow}>
        <input
          type="file"
          accept=".zip"
          onChange={e => {
            setFile(e.target.files[0])
            setStatus('idle')
            setResult(null)
          }}
          style={styles.fileInput}
        />
        <button
          onClick={handleUpload}
          disabled={!file || status === 'loading'}
          style={{
            ...styles.button,
            opacity: (!file || status === 'loading') ? 0.5 : 1,
          }}
        >
          {status === 'loading' ? 'Scanning...' : 'Upload project'}
        </button>
      </div>

      {status === 'loading' && (
        <div style={styles.loadingBox}>
          Scanning all programs and routines — this takes 30–60 seconds
          for large projects. Please wait...
        </div>
      )}

      {status === 'success' && result && (
        <div style={styles.successBox}>
          <div style={styles.successTitle}>Project uploaded successfully</div>
          <div style={styles.meta}>Name: {result.project_name}</div>
          <div style={styles.meta}>Version: {result.version_label}</div>
          <div style={styles.meta}>Total programs: {result.summary.total_programs}</div>
          <div style={styles.meta}>With PreState: {result.summary.with_prestate}</div>
          <div style={styles.meta}>Phases (PH): {result.summary.phases_PH}</div>
          <div style={styles.meta}>Operations (OP): {result.summary.operations_OP}</div>
          <div style={styles.meta}>Unit Procedures (UP): {result.summary.unit_procedures_UP}</div>
          <div style={styles.metaId}>Project ID: {result.project_id}</div>
        </div>
      )}

      {status === 'error' && (
        <div style={styles.errorBox}>{error}</div>
      )}
    </div>
  )
}

const styles = {
  card: {
    background:   '#fff',
    border:       '1px solid #e5e5e5',
    borderRadius: 8,
    padding:      24,
  },
  heading: {
    fontSize:   18,
    fontWeight: 600,
    margin:     '0 0 8px',
  },
  description: {
    fontSize:   14,
    color:      '#555',
    margin:     '0 0 20px',
  },
  row: {
    marginBottom: 16,
  },
  field: {
    display:       'flex',
    flexDirection: 'column',
    gap:           6,
    maxWidth:      300,
  },
  label: {
    fontSize:   13,
    fontWeight: 500,
    color:      '#333',
  },
  input: {
    fontSize:     13,
    padding:      '6px 10px',
    borderRadius: 6,
    border:       '1px solid #ddd',
  },
  uploadRow: {
    display:    'flex',
    gap:        12,
    alignItems: 'center',
    flexWrap:   'wrap',
  },
  fileInput: {
    fontSize: 14,
  },
  button: {
    padding:      '8px 20px',
    background:   '#2563eb',
    color:        '#fff',
    border:       'none',
    borderRadius: 6,
    cursor:       'pointer',
    fontSize:     14,
    fontWeight:   500,
  },
  loadingBox: {
    marginTop:    16,
    padding:      16,
    background:   '#eff6ff',
    border:       '1px solid #bfdbfe',
    borderRadius: 6,
    color:        '#1d4ed8',
    fontSize:     14,
  },
  successBox: {
    marginTop:    16,
    padding:      16,
    background:   '#f0fdf4',
    border:       '1px solid #86efac',
    borderRadius: 6,
  },
  successTitle: {
    fontWeight:   600,
    color:        '#166534',
    marginBottom: 8,
  },
  meta: {
    fontSize: 13,
    color:    '#166534',
    margin:   '2px 0',
  },
  metaId: {
    fontSize:    12,
    color:       '#166534',
    marginTop:   8,
    fontFamily:  'monospace',
    wordBreak:   'break-all',
  },
  errorBox: {
    marginTop:    16,
    padding:      16,
    background:   '#fef2f2',
    border:       '1px solid #fca5a5',
    borderRadius: 6,
    color:        '#991b1b',
    fontSize:     14,
  },
}