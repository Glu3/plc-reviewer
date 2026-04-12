import { charDiff } from '../utils/diffHighlight'

export default function CompareReport({ data }) {
  if (!data) return (
    <div style={styles.empty}>
      No comparison run yet. Go to Compare Projects and select two projects.
    </div>
  )

  const { summary, findings, routine_name, normalise,
          programs_in_a, programs_in_ref, total_findings } = data

  const critical = findings.filter(f =>
    ['program_removed', 'routine_missing_in_a', 'rung_removed'].includes(f.finding_type)
  )
  const warnings = findings.filter(f =>
    !['program_removed', 'routine_missing_in_a', 'rung_removed'].includes(f.finding_type)
  )

  return (
    <div>

      {/* Summary bar */}
      <div style={styles.summary}>
        <SummaryItem label="Routine"     value={routine_name} />
        <SummaryItem label="Programs A"  value={programs_in_a} />
        <SummaryItem label="Programs Ref" value={programs_in_ref} />
        <SummaryItem label="Identical"   value={summary.identical}
          color="#166534" />
        <SummaryItem label="Differences" value={total_findings}
          color={total_findings > 0 ? '#b91c1c' : '#166534'} />
        <SummaryItem label="Normalised"  value={normalise ? 'Yes' : 'No'} />
      </div>

      {/* Breakdown chips */}
      <div style={styles.chips}>
        {summary.programs_added > 0 &&
          <Chip label="Programs added" count={summary.programs_added} color="#854f0b" bg="#fef3c7" />}
        {summary.programs_removed > 0 &&
          <Chip label="Programs removed" count={summary.programs_removed} color="#991b1b" bg="#fee2e2" />}
        {summary.routine_missing_in_a > 0 &&
          <Chip label="Routine missing in A" count={summary.routine_missing_in_a} color="#991b1b" bg="#fee2e2" />}
        {summary.routine_missing_in_ref > 0 &&
          <Chip label="Routine missing in Ref" count={summary.routine_missing_in_ref} color="#854f0b" bg="#fef3c7" />}
        {summary.rungs_modified > 0 &&
          <Chip label="Rungs modified" count={summary.rungs_modified} color="#1d4ed8" bg="#eff6ff" />}
        {summary.rungs_added > 0 &&
          <Chip label="Rungs added" count={summary.rungs_added} color="#854f0b" bg="#fef3c7" />}
        {summary.rungs_removed > 0 &&
          <Chip label="Rungs removed" count={summary.rungs_removed} color="#991b1b" bg="#fee2e2" />}
      </div>

      {total_findings === 0 && (
        <div style={styles.allClear}>
          All programs are identical between the two projects.
        </div>
      )}

      {/* Findings */}
      {findings.map((f, i) => (
        <FindingCard key={i} finding={f} />
      ))}

    </div>
  )
}

function FindingCard({ finding }) {
  const isStructural = ['program_added', 'program_removed',
    'routine_missing_in_a', 'routine_missing_in_ref'].includes(finding.finding_type)

  const borderColor =
    finding.finding_type === 'program_removed' ||
    finding.finding_type === 'routine_missing_in_a' ||
    finding.finding_type === 'rung_removed' ? '#dc2626' :
    finding.finding_type === 'rung_modified' ? '#2563eb' : '#d97706'

  return (
    <div style={{ ...styles.card, borderLeft: `4px solid ${borderColor}` }}>

      <div style={styles.cardHeader}>
        <span style={{
          ...styles.badge,
          background: finding.severity === 'critical' ? '#fee2e2' : '#eff6ff',
          color:      finding.severity === 'critical' ? '#991b1b' : '#1d4ed8',
        }}>
          {finding.finding_type.replace(/_/g, ' ').toUpperCase()}
        </span>
        <span style={styles.program}>{finding.program_name}</span>
        {finding.rung_number && (
          <span style={styles.rungBadge}>rung {finding.rung_number}</span>
        )}
      </div>

      <p style={styles.message}>{finding.message}</p>

      {/* Character-level diff for rung_modified */}
      {finding.finding_type === 'rung_modified' && finding.evidence && (
        <RungDiff evidence={finding.evidence} />
      )}

      {/* Plain evidence for structural findings */}
      {isStructural && finding.evidence && (
        <div style={styles.plainEvidence}>{finding.evidence}</div>
      )}

      <div style={styles.fix}>
        <span style={styles.fixLabel}>Fix: </span>
        {finding.fix}
      </div>

    </div>
  )
}

function RungDiff({ evidence }) {
  // Parse the unified diff to extract the two rung texts
  const lines = evidence.split('\n')
  let refText = ''
  let aText   = ''

  for (const line of lines) {
    if (line.startsWith('-') && !line.startsWith('---')) {
      refText = line.slice(1).trim()
    }
    if (line.startsWith('+') && !line.startsWith('+++')) {
      aText = line.slice(1).trim()
    }
  }

  if (!refText || !aText) {
    // Fallback to raw diff if parsing fails
    return (
      <div style={styles.diffBlock}>
        {lines.map((line, i) => (
          <div key={i} style={{
            ...styles.diffLine,
            background: line.startsWith('+') && !line.startsWith('+++') ? '#f0fdf4'
                      : line.startsWith('-') && !line.startsWith('---') ? '#fef2f2'
                      : 'transparent',
            color:      line.startsWith('+') && !line.startsWith('+++') ? '#166534'
                      : line.startsWith('-') && !line.startsWith('---') ? '#991b1b'
                      : '#666',
          }}>
            {line}
          </div>
        ))}
      </div>
    )
  }

  const segments = charDiff(refText, aText)

  return (
    <div style={styles.charDiffWrap}>

      {/* Reference line */}
      <div style={styles.charDiffRow}>
        <span style={styles.charDiffLabel}>Ref</span>
        <div style={styles.charDiffText}>
          {segments.map((seg, i) => (
            seg.type === 'equal' ? (
              <span key={i}>{seg.text}</span>
            ) : seg.type === 'removed' ? (
              <span key={i} style={styles.removed}>{seg.text}</span>
            ) : null
          ))}
        </div>
      </div>

      {/* Project A line */}
      <div style={styles.charDiffRow}>
        <span style={styles.charDiffLabel}>A</span>
        <div style={styles.charDiffText}>
          {segments.map((seg, i) => (
            seg.type === 'equal' ? (
              <span key={i}>{seg.text}</span>
            ) : seg.type === 'added' ? (
              <span key={i} style={styles.added}>{seg.text}</span>
            ) : null
          ))}
        </div>
      </div>

    </div>
  )
}

function SummaryItem({ label, value, color }) {
  return (
    <div style={styles.summaryItem}>
      <span style={styles.summaryLabel}>{label}</span>
      <span style={{ ...styles.summaryValue, color: color || 'inherit' }}>
        {value}
      </span>
    </div>
  )
}

function Chip({ label, count, color, bg }) {
  return (
    <span style={{ ...styles.chip, color, background: bg }}>
      {count} {label}
    </span>
  )
}

const styles = {
  empty: {
    padding:   48,
    textAlign: 'center',
    color:     '#888',
    fontSize:  14,
  },
  summary: {
    display:      'flex',
    gap:          24,
    padding:      20,
    background:   '#f9fafb',
    border:       '1px solid #e5e5e5',
    borderRadius: 8,
    marginBottom: 12,
    flexWrap:     'wrap',
  },
  summaryItem: {
    display:       'flex',
    flexDirection: 'column',
    gap:           4,
  },
  summaryLabel: {
    fontSize:      11,
    color:         '#888',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  summaryValue: {
    fontSize:   16,
    fontWeight: 500,
  },
  chips: {
    display:      'flex',
    flexWrap:     'wrap',
    gap:          8,
    marginBottom: 20,
  },
  chip: {
    fontSize:     12,
    fontWeight:   500,
    padding:      '4px 10px',
    borderRadius: 4,
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
    display:      'flex',
    gap:          10,
    alignItems:   'center',
    marginBottom: 10,
    flexWrap:     'wrap',
  },
  badge: {
    fontSize:      11,
    fontWeight:    600,
    padding:       '3px 8px',
    borderRadius:  4,
    letterSpacing: '0.05em',
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
  charDiffWrap: {
    fontFamily:   'monospace',
    fontSize:     12,
    background:   '#f8f8f8',
    border:       '1px solid #e5e5e5',
    borderRadius: 4,
    padding:      12,
    marginBottom: 12,
    overflowX:    'auto',
  },
  charDiffRow: {
    display:    'flex',
    gap:        12,
    alignItems: 'baseline',
    lineHeight: 1.8,
  },
  charDiffLabel: {
    fontSize:     11,
    fontWeight:   600,
    color:        '#888',
    minWidth:     28,
    textAlign:    'right',
    flexShrink:   0,
  },
  charDiffText: {
    whiteSpace: 'pre-wrap',
    wordBreak:  'break-all',
  },
  removed: {
    background:    '#fee2e2',
    color:         '#991b1b',
    borderRadius:  2,
    padding:       '0 1px',
    fontWeight:    600,
  },
  added: {
    background:   '#dcfce7',
    color:        '#166534',
    borderRadius: 2,
    padding:      '0 1px',
    fontWeight:   600,
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
    padding:    '1px 6px',
    whiteSpace: 'pre-wrap',
    wordBreak:  'break-all',
    lineHeight: 1.5,
  },
  plainEvidence: {
    fontFamily:   'monospace',
    fontSize:     12,
    color:        '#555',
    background:   '#f8f8f8',
    padding:      12,
    borderRadius: 4,
    marginBottom: 12,
  },
  fix: {
    fontSize:     13,
    color:        '#555',
    background:   '#f9fafb',
    padding:      '10px 12px',
    borderRadius: 4,
  },
  fixLabel: {
    fontWeight: 600,
    color:      '#333',
  },
}