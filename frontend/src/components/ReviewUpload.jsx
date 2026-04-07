import { useState } from 'react'
import { submitReview } from '../api'

export default function ReviewUpload({ onComplete }) {
  const [file,   setFile]   = useState(null)
  const [status, setStatus] = useState('idle')
  const [error,  setError]  = useState(null)

  async function handleSubmit() {
    if (!file) return
    setStatus('loading')
    setError(null)
    try {
      const data = await submitReview(file)
      setStatus('idle')
      onComplete(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setStatus('error')
    }
  }

  return (
    <div style={styles.card}>
      <h2 style={styles.heading}>Review a project file</h2>
      <p style={styles.description}>
        Upload a Rockwell .L5X project file. Every program inside it will be
        checked against the reference PreState routine.
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
          {status === 'loading' ? 'Reviewing...' : 'Run review'}
        </button>
      </div>

      {status === 'loading' && (
        <div style={styles.loadingBox}>
          Parsing file and comparing rungs — please wait...
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
  loadingBox: {
    marginTop:  16,
    padding:    16,
    background: '#eff6ff',
    border:     '1px solid #bfdbfe',
    borderRadius: 6,
    color:      '#1d4ed8',
    fontSize:   14,
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