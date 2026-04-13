import { useState } from 'react'
import UploadReference from './components/UploadReference'
import ReviewUpload from './components/ReviewUpload'
import FindingsReport from './components/FindingsReport'
import ProjectCompare from './components/ProjectCompare'
import CompareReport from './components/CompareReport'
import ProjectUpload from './components/ProjectUpload'
import AgentPage from './components/AgentPage'

export default function App() {
  const [activeTab,   setActiveTab]   = useState('review')
  const [findings,    setFindings]    = useState(null)
  const [reviewMeta,  setReviewMeta]  = useState(null)
  const [compareData, setCompareData] = useState(null)

  function handleReviewComplete(data) {
    setFindings(data.findings)
    setReviewMeta({
      filename:        data.filename,
      reviewId:        data.review_id,
      totalDeviations: data.total_deviations,
      programsChecked: data.programs_checked,
    })
    setActiveTab('results')
  }

  function handleCompareComplete(data) {
    setCompareData(data)
    setActiveTab('compare-results')
  }

  const tabs = [
    { id: 'review',          label: 'Review Project' },
    { id: 'reference',       label: 'Upload Reference' },
    { id: 'compare',         label: 'Compare Projects' },
    { id: 'results',         label: `Results ${reviewMeta ? `(${reviewMeta.totalDeviations})` : ''}` },
    { id: 'compare-results', label: `Compare Results ${compareData ? `(${compareData.total_findings})` : ''}` },
    { id: 'upload-project', label: 'Upload Project' },
    { id: 'agent', label: 'AI Agent' },
  ]

  return (
    <div style={styles.app}>

      <header style={styles.header}>
        <h1 style={styles.title}>PLC Reviewer</h1>
        <p style={styles.subtitle}>PreState routine compliance checker</p>
      </header>

      <nav style={styles.nav}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...styles.tab,
              ...(activeTab === tab.id ? styles.tabActive : {}),
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main>
        {activeTab === 'reference'       && <UploadReference />}
        {activeTab === 'review'          && <ReviewUpload onComplete={handleReviewComplete} />}
        {activeTab === 'results'         && <FindingsReport findings={findings} meta={reviewMeta} />}
        {activeTab === 'compare'         && <ProjectCompare onComplete={handleCompareComplete} />}
        {activeTab === 'compare-results' && <CompareReport data={compareData} />}
        {activeTab === 'upload-project' && <ProjectUpload onUploaded={() => {}} />}
        {activeTab === 'agent' && <AgentPage />}
      </main>

    </div>
  )
}

const styles = {
  app: {
    fontFamily: 'system-ui, sans-serif',
    maxWidth:   900,
    margin:     '0 auto',
    padding:    '0 24px 48px',
    color:      '#1a1a1a',
  },
  header: {
    padding:      '32px 0 16px',
    borderBottom: '1px solid #e5e5e5',
    marginBottom: 0,
  },
  title: {
    fontSize:   24,
    fontWeight: 600,
    margin:     0,
  },
  subtitle: {
    fontSize: 14,
    color:    '#666',
    margin:   '4px 0 0',
  },
  nav: {
    display:      'flex',
    gap:          4,
    padding:      '12px 0',
    borderBottom: '1px solid #e5e5e5',
    marginBottom: 24,
    flexWrap:     'wrap',
  },
  tab: {
    padding:      '8px 16px',
    border:       '1px solid transparent',
    borderRadius: 6,
    background:   'transparent',
    cursor:       'pointer',
    fontSize:     14,
    color:        '#444',
  },
  tabActive: {
    background:  '#f0f0f0',
    border:      '1px solid #ddd',
    color:       '#000',
    fontWeight:  500,
  },
}