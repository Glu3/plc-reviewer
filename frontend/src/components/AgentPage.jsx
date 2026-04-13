import { useState, useEffect, useRef } from 'react'
import { sendAgentMessage, uploadProject, listProjects } from '../api'

export default function AgentPage() {
  const [messages,     setMessages]     = useState([
    {
        role:    'assistant',
        content: 'Hello! I can help you review PLC projects and compare routines between project versions. Upload a project ZIP on the right, then tell me what you want to analyse.',
        toolCalls: [], }
  ])
  const [input,        setInput]        = useState('')
  const [loading,      setLoading]      = useState(false)
  const [projects,     setProjects]     = useState([])
  const [uploadStatus, setUploadStatus] = useState('idle')
  const [uploadFile,   setUploadFile]   = useState(null)
  const [versionLabel, setVersionLabel] = useState('v1')
  const messagesEndRef = useRef(null)
  const fileInputRef   = useRef(null)

  useEffect(() => {
    loadProjects()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function loadProjects() {
    try {
      const data = await listProjects()
      setProjects(data)
    } catch (err) {
      console.error('Failed to load projects:', err)
    }
  }

  async function handleSend() {
    if (!input.trim() || loading) return
    const userMessage = { role: 'user', content: input.trim(), toolCalls: [] }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
        const { response, toolCallsMade } = await sendAgentMessage(
        newMessages.filter(m => typeof m.content === 'string')
                    .map(m => ({ role: m.role, content: m.content }))
        )
        setMessages(prev => [...prev, {
        role:      'assistant',
        content:   response,
        toolCalls: toolCallsMade,
        }])
    } catch (err) {
        setMessages(prev => [...prev, {
        role:      'assistant',
        content:   'Sorry, I encountered an error. Please check that the backend is running.',
        toolCalls: [],
        }])
    } finally {
        setLoading(false)
    }
}

  async function handleUpload() {
    if (!uploadFile) return
    setUploadStatus('loading')

    try {
      const data = await uploadProject(uploadFile, versionLabel)
      setUploadStatus('idle')
      setUploadFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      await loadProjects()

      const notifyMsg = {
        role:      'user',
        content:   `I just uploaded a project: ${data.project_name} (${data.version_label}), ` +
                   `${data.summary.total_programs} programs total, ` +
                   `${data.summary.with_prestate} with PreState routines. ` +
                   `Project ID: ${data.project_id}`,
        toolCalls: [],
      }
      const newMessages = [...messages, notifyMsg]
      setMessages(newMessages)
      setLoading(true)

      const { response, toolCallsMade } = await sendAgentMessage(
        newMessages.filter(m => typeof m.content === 'string')
                   .map(m => ({ role: m.role, content: m.content }))
      )
      setMessages(prev => [...prev, {
        role:      'assistant',
        content:   response,
        toolCalls: toolCallsMade,
      }])
    } catch (err) {
      setUploadStatus('error')
      setMessages(prev => [...prev, {
        role:      'assistant',
        content:   `I noticed an issue with the upload: ${err.response?.data?.detail || err.message}. Please try again.`,
        toolCalls: [],
      }])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={styles.wrap}>

      {/* Chat panel */}
      <div style={styles.chatPanel}>
        <div style={styles.chatHeader}>
          <span style={styles.chatTitle}>PLC Review Agent</span>
          {loading && <span style={styles.thinking}>thinking...</span>}
        </div>

        <div style={styles.messages}>
          {messages.map((msg, i) => (
            <div key={i} style={{
              ...styles.msg,
              ...(msg.role === 'user' ? styles.msgUser : styles.msgAI),
            }}>
              {msg.content}
            </div>
          ))}
          {loading && (
            <div style={{ ...styles.msg, ...styles.msgAI, ...styles.msgTyping }}>
              <span style={styles.dot} />
              <span style={styles.dot} />
              <span style={styles.dot} />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={styles.inputRow}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your PLC projects... (Enter to send)"
            style={styles.textarea}
            rows={2}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            style={{
              ...styles.sendBtn,
              opacity: (!input.trim() || loading) ? 0.5 : 1,
            }}
          >
            Send
          </button>
        </div>
      </div>

      {/* Side panel */}
      <div style={styles.sidePanel}>
        <div style={styles.sideHeader}>Projects</div>

        {/* Upload zone */}
        <div style={styles.uploadZone}>
          <div style={styles.uploadTitle}>Upload project ZIP</div>
          <div style={styles.uploadSub}>
            Rockwell project folder exported as ZIP
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            onChange={e => setUploadFile(e.target.files[0])}
            style={styles.fileInput}
          />

          <input
            type="text"
            value={versionLabel}
            onChange={e => setVersionLabel(e.target.value)}
            placeholder="Version label e.g. v1, baseline"
            style={styles.versionInput}
          />

          <button
            onClick={handleUpload}
            disabled={!uploadFile || uploadStatus === 'loading'}
            style={{
              ...styles.uploadBtn,
              opacity: (!uploadFile || uploadStatus === 'loading') ? 0.5 : 1,
            }}
          >
            {uploadStatus === 'loading' ? 'Scanning...' : 'Upload'}
          </button>
        </div>

        {/* Projects list */}
        <div style={styles.projectsList}>
          {projects.length === 0 && (
            <div style={styles.noProjects}>No projects uploaded yet.</div>
          )}
          {projects.map(p => (
            <div key={p.id} style={styles.projectCard}>
              <div style={styles.projectName}>{p.name}</div>
              <div style={styles.projectMeta}>
                {p.version_label} · {p.program_count} programs
              </div>
              <div style={styles.projectId}>{p.id.slice(0, 18)}...</div>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}

const styles = {
  wrap: {
    display:             'grid',
    gridTemplateColumns: '1fr 300px',
    gap:                 0,
    border:              '1px solid #e5e5e5',
    borderRadius:        8,
    overflow:            'hidden',
    height:              'calc(100vh - 180px)',
    minHeight:           500,
  },
  chatPanel: {
    display:       'flex',
    flexDirection: 'column',
    borderRight:   '1px solid #e5e5e5',
    background:    '#fff',
  },
  chatHeader: {
    padding:      '12px 16px',
    borderBottom: '1px solid #e5e5e5',
    display:      'flex',
    alignItems:   'center',
    gap:          12,
  },
  chatTitle: {
    fontSize:   14,
    fontWeight: 500,
  },
  thinking: {
    fontSize: 12,
    color:    '#888',
    fontStyle:'italic',
  },
  messages: {
    flex:      1,
    overflowY: 'auto',
    padding:   16,
    display:   'flex',
    flexDirection: 'column',
    gap:       12,
    background:'#f9fafb',
  },
  msg: {
    maxWidth:   '85%',
    padding:    '10px 14px',
    borderRadius: 12,
    fontSize:   14,
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap',
    wordBreak:  'break-word',
  },
  msgAI: {
    background:   '#fff',
    border:       '1px solid #e5e5e5',
    color:        '#1a1a1a',
    alignSelf:    'flex-start',
    borderRadius: '4px 12px 12px 12px',
  },
  msgUser: {
    background:   '#2563eb',
    color:        '#fff',
    alignSelf:    'flex-end',
    borderRadius: '12px 4px 12px 12px',
  },
  msgTyping: {
    display:    'flex',
    gap:        4,
    alignItems: 'center',
    padding:    '12px 16px',
  },
  dot: {
    width:        6,
    height:       6,
    borderRadius: '50%',
    background:   '#aaa',
    display:      'inline-block',
  },
  inputRow: {
    padding:    12,
    borderTop:  '1px solid #e5e5e5',
    display:    'flex',
    gap:        8,
    background: '#fff',
  },
  textarea: {
    flex:        1,
    fontSize:    13,
    padding:     '8px 12px',
    border:      '1px solid #ddd',
    borderRadius:8,
    resize:      'none',
    fontFamily:  'system-ui, sans-serif',
    lineHeight:  1.5,
  },
  sendBtn: {
    padding:      '8px 16px',
    background:   '#2563eb',
    color:        '#fff',
    border:       'none',
    borderRadius: 8,
    cursor:       'pointer',
    fontSize:     13,
    fontWeight:   500,
    alignSelf:    'flex-end',
  },
  sidePanel: {
    display:       'flex',
    flexDirection: 'column',
    background:    '#f9fafb',
    overflow:      'hidden',   // ← change from overflowY: 'auto'
  },
  sideHeader: {
    padding:      '12px 16px',
    borderBottom: '1px solid #e5e5e5',
    fontSize:     13,
    fontWeight:   500,
  },
  uploadZone: {
    margin:        12,
    border:        '1.5px dashed #ddd',
    borderRadius:  8,
    padding:       16,
    background:    '#fff',
    display:       'flex',
    flexDirection: 'column',
    gap:           8,
  },
  uploadTitle: {
    fontSize:   13,
    fontWeight: 500,
  },
  uploadSub: {
    fontSize: 12,
    color:    '#888',
  },
  fileInput: {
    fontSize: 12,
  },
  versionInput: {
    fontSize:     12,
    padding:      '5px 8px',
    border:       '1px solid #ddd',
    borderRadius: 6,
  },
  uploadBtn: {
    padding:      '6px 14px',
    background:   '#2563eb',
    color:        '#fff',
    border:       'none',
    borderRadius: 6,
    cursor:       'pointer',
    fontSize:     12,
    fontWeight:   500,
    alignSelf:    'flex-start',
  },
  projectsList: {
    padding:   '0 12px 12px',
    display:   'flex',
    flexDirection: 'column',
    gap:       8,
    overflowY: 'auto',   // ← only the projects list scrolls, not the whole panel
    flex:      1,        // ← takes remaining space after upload zone
  },
  noProjects: {
    fontSize:  12,
    color:     '#888',
    textAlign: 'center',
    padding:   16,
  },
  projectCard: {
    background:   '#fff',
    border:       '1px solid #e5e5e5',
    borderRadius: 6,
    padding:      '8px 12px',
  },
  projectName: {
    fontSize:   12,
    fontWeight: 500,
  },
  projectMeta: {
    fontSize: 11,
    color:    '#888',
    marginTop: 2,
  },
  projectId: {
    fontSize:   10,
    color:      '#bbb',
    fontFamily: 'monospace',
    marginTop:  4,
  },
}