import { useState } from 'react'
import { uploadReference } from '../api'

export default function UploadReference() {
  const [file,    setFile]    = useState(null)
  const [status,  setStatus]  = useState('idle')  // idle | loading | success | error
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState(null)

  async function handleSubmit() {
    if (!file) return
    setStatus('loading')
    setError(null)
    try {
      const data = await uploadReference(file)
      setResult(data)
      setStatus('success')
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setStatus('error')
    }
  }

  return (
    <div style={styles.card}>
      <h2 style={styles.heading}>Upload reference routine</h2>
      <p style={styles.description}>
        Upload the authoritative PreState .L5X file. All future reviews will
        compare against this version.
      </p>

      <div style={styles.uploadRow}>
        <input
          type="file"
          accept=".l5x,.L5X"
          onChange={e => { setFile(e.target.files[0]); setStatus('idle') }}
          style={styles.fileInput}
        />
        <button
          onClick={handleSubmit}
          disabled={!file || status === 'loading'}
          style={{
            ...styles.button,
            opacity: (!file || status === 'loading') ? 0.5 : 1,
          }}
        >
          {status === 'loading' ? 'Uploading...' : 'Upload reference'}
        </button>
      </div>

      {status === 'success' && result && (
        <div style={styles.successBox}>
          <div style={styles.successTitle}>Reference stored successfully</div>
          <div style={styles.meta}>Routine: {result.routine_name}</div>
          <div style={styles.meta}>Rungs: {result.rung_count}</div>
          <div style={styles.meta}>Action: {result.action}</div>
          <div style={styles.meta}>ID: {result.reference_id}</div>
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
  uploadRow: {
    display:    'flex',
    gap:        12,
    alignItems: 'center',
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
  errorBox: {
    marginTop:  16,
    padding:    16,
    background: '#fef2f2',
    border:     '1px solid #fca5a5',
    borderRadius: 6,
    color:      '#991b1b',
    fontSize:   14,
  },
}