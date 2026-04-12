import { useState, useEffect } from 'react'
import { listProjects, listRoutines, compareProjects } from '../api'

export default function ProjectCompare({ onComplete }) {
  const [projects,      setProjects]      = useState([])
  const [projectAId,    setProjectAId]    = useState('')
  const [projectRefId,  setProjectRefId]  = useState('')
  const [routines,      setRoutines]      = useState([])
  const [routineName,   setRoutineName]   = useState('PrestateRoutine')
  const [normalise,     setNormalise]     = useState(true)
  const [programTypes,  setProgramTypes]  = useState([])
  const [status,        setStatus]        = useState('idle')
  const [error,         setError]         = useState(null)

  const TYPE_OPTIONS = ['PH', 'OP', 'UP']

  useEffect(() => {
    listProjects().then(setProjects).catch(() => {})
  }, [])

  useEffect(() => {
    if (projectAId) {
      listRoutines(projectAId).then(setRoutines).catch(() => {})
    }
  }, [projectAId])

  function toggleType(t) {
    setProgramTypes(prev =>
      prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]
    )
  }

  async function handleCompare() {
    if (!projectAId || !projectRefId) return
    setStatus('loading')
    setError(null)
    try {
      const data = await compareProjects({
        projectAId,
        projectRefId,
        routineName,
        normalise,
        programTypes: programTypes.length ? programTypes : undefined,
      })
      setStatus('idle')
      onComplete(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setStatus('error')
    }
  }

  return (
    <div style={styles.card}>
      <h2 style={styles.heading}>Compare two projects</h2>
      <p style={styles.description}>
        Select two uploaded projects and a routine to compare.
        Programs are matched by name — unmatched programs are flagged as added or removed.
      </p>

      <div style={styles.grid}>

        <div style={styles.field}>
          <label style={styles.label}>Project A</label>
          <select
            style={styles.select}
            value={projectAId}
            onChange={e => setProjectAId(e.target.value)}
          >
            <option value="">Select project...</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>
                {p.name} — {p.version_label} ({p.program_count} programs)
              </option>
            ))}
          </select>
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Reference project</label>
          <select
            style={styles.select}
            value={projectRefId}
            onChange={e => setProjectRefId(e.target.value)}
          >
            <option value="">Select reference...</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>
                {p.name} — {p.version_label} ({p.program_count} programs)
              </option>
            ))}
          </select>
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Routine to compare</label>
          <select
            style={styles.select}
            value={routineName}
            onChange={e => setRoutineName(e.target.value)}
          >
            <option value="PrestateRoutine">PrestateRoutine</option>
            {routines.filter(r => r !== 'PrestateRoutine').map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Program types (optional)</label>
          <div style={styles.checkboxRow}>
            {TYPE_OPTIONS.map(t => (
              <label key={t} style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={programTypes.includes(t)}
                  onChange={() => toggleType(t)}
                />
                {t}
              </label>
            ))}
          </div>
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Normalise program name in rungs</label>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={normalise}
              onChange={e => setNormalise(e.target.checked)}
            />
            Replace program name with __PROGRAM__ before comparing
          </label>
        </div>

      </div>

      <button
        onClick={handleCompare}
        disabled={!projectAId || !projectRefId || status === 'loading'}
        style={{
          ...styles.button,
          opacity: (!projectAId || !projectRefId || status === 'loading') ? 0.5 : 1,
        }}
      >
        {status === 'loading' ? 'Comparing...' : 'Run comparison'}
      </button>

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
  grid: {
    display:             'grid',
    gridTemplateColumns: '1fr 1fr',
    gap:                 16,
    marginBottom:        20,
  },
  field: {
    display:       'flex',
    flexDirection: 'column',
    gap:           6,
  },
  label: {
    fontSize:   13,
    fontWeight: 500,
    color:      '#333',
  },
  select: {
    fontSize:     13,
    padding:      '6px 10px',
    borderRadius: 6,
    border:       '1px solid #ddd',
  },
  checkboxRow: {
    display: 'flex',
    gap:     16,
  },
  checkboxLabel: {
    fontSize:   13,
    display:    'flex',
    alignItems: 'center',
    gap:        6,
    cursor:     'pointer',
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