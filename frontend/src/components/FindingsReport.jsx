export default function FindingsReport({ findings, meta }) {

  if (!findings) {
    return (
      <div style={styles.empty}>
        No review run yet. Go to Review Project and upload a file.
      </div>
    )
  }

  const severityOrder = { critical: 0, warning: 1 }
  const sorted = [...findings].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity]
  )

  const critical = sorted.filter(f => f.severity === 'critical')
  const warnings = sorted.filter(f => f.severity === 'warning')

  return (
    <div>

      {/* Summary bar */}
      <div style={styles.summary}>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>File</span>
          <span style={styles.summaryValue}>{meta?.filename}</span>
        </div>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>Programs checked</span>
          <span style={styles.summaryValue}>{meta?.programsChecked?.length ?? 0}</span>
        </div>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>Total deviations</span>
          <span style={{
            ...styles.summaryValue,
            color: meta?.totalDeviations > 0 ? '#b91c1c' : '#166534',
            fontWeight: 600,
          }}>
            {meta?.totalDeviations ?? 0}
          </span>
        </div>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>Critical</span>
          <span style={{ ...styles.summaryValue, color: critical.length > 0 ? '#b91c1c' : '#166534' }}>
            {critical.length}
          </span>
        </div>
        <div style={styles.summaryItem}>
          <span style={styles.summaryLabel}>Warnings</span>
          <span style={{ ...styles.summaryValue, color: warnings.length > 0 ? '#92400e' : '#166534' }}>
            {warnings.length}
          </span>
        </div>
      </div>

      {/* All clear */}
      {findings.length === 0 && (
        <div style={styles.allClear}>
          All programs match the reference PreState routine exactly.
        </div>
      )}

      {/* Findings list */}
      {sorted.map((finding, i) => (
        <FindingCard key={i} finding={finding} />
      ))}

    </div>
  )
}

function FindingCard({ finding }) {
  const isCritical = finding.severity === 'critical'

  return (
    <div style={{
      ...styles.card,
      borderLeft: `4px solid ${isCritical ? '#dc2626' : '#d97706'}`,
    }}>

      {/* Card header */}
      <div style={styles.cardHeader}>
        <span style={{
          ...styles.badge,
          background: isCritical ? '#fee2e2' : '#fef3c7',
          color:      isCritical ? '#991b1b' : '#92400e',
        }}>
          {finding.severity.toUpperCase()}
        </span>
        <span style={styles.deviationType}>{finding.deviation_type}</span>
        <span style={styles.program}>{finding.program}</span>
        {finding.rung_number && (
          <span style={styles.rungBadge}>rung {finding.rung_number}</span>
        )}
      </div>

      {/* Message */}
      <p style={styles.message}>{finding.message}</p>

      {/* Diff block */}
      {finding.diff && finding.diff.length > 0 && (
        <div style={styles.diffBlock}>
          {finding.diff.map((line, i) => (
            <div key={i} style={{
              ...styles.diffLine,
              background: line.startsWith('+') ? '#f0fdf4'
                        : line.startsWith('-') ? '#fef2f2'
                        : 'transparent',
              color:      line.startsWith('+') ? '#166534'
                        : line.startsWith('-') ? '#991b1b'
                        : '#666',
            }}>
              {line}
            </div>
          ))}
        </div>
      )}

      {/* Fix suggestion */}
      <div style={styles.fix}>
        <span style={styles.fixLabel}>Fix: </span>
        {finding.fix}
      </div>

    </div>
  )
}

const styles = {
  empty: {
    padding:    48,
    textAlign:  'center',
    color:      '#888',
    fontSize:   14,
  },
  summary: {
    display:      'flex',
    gap:          24,
    padding:      20,
    background:   '#f9fafb',
    border:       '1px solid #e5e5e5',
    borderRadius: 8,
    marginBottom: 20,
    flexWrap:     'wrap',
  },
  summaryItem: {
    display:       'flex',
    flexDirection: 'column',
    gap:           4,
  },
  summaryLabel: {
    fontSize: 11,
    color:    '#888',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  summaryValue: {
    fontSize:   16,
    fontWeight: 500,
  },
  allClear: {
    padding:      24,
    background:   '#f0fdf4',
    border:       '1px solid #86efac',
    borderRadius: 8,
    color:        '#166534',
    fontWeight:   500,
    textAlign:    'center',
    marginBottom: 16,
  },
  card: {
    background:   '#fff',
    border:       '1px solid #e5e5e5',
    borderRadius: 8,
    padding:      20,
    marginBottom: 12,
  },
  cardHeader: {
    display:    'flex',
    gap:        10,
    alignItems: 'center',
    marginBottom: 10,
    flexWrap:   'wrap',
  },
  badge: {
    fontSize:     11,
    fontWeight:   600,
    padding:      '3px 8px',
    borderRadius: 4,
    letterSpacing: '0.05em',
  },
  deviationType: {
    fontSize:   13,
    color:      '#555',
    fontFamily: 'monospace',
  },
  program: {
    fontSize:   13,
    fontWeight: 500,
  },
  rungBadge: {
    fontSize:     12,
    color:        '#666',
    background:   '#f3f4f6',
    padding:      '2px 8px',
    borderRadius: 4,
  },
  message: {
    fontSize: 14,
    color:    '#333',
    margin:   '0 0 12px',
  },
  diffBlock: {
    fontFamily:   'monospace',
    fontSize:     12,
    background:   '#f8f8f8',
    border:       '1px solid #e5e5e5',
    borderRadius: 4,
    padding:      12,
    marginBottom: 12,
    overflowX:    'auto',
  },
  diffLine: {
    padding:      '1px 6px',
    whiteSpace:   'pre-wrap',
    wordBreak:    'break-all',
    lineHeight:   1.5,
  },
  fix: {
    fontSize:   13,
    color:      '#555',
    background: '#f9fafb',
    padding:    '10px 12px',
    borderRadius: 4,
  },
  fixLabel: {
    fontWeight: 600,
    color:      '#333',
  },
}