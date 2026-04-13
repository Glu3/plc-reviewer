import axios from 'axios'

const api = axios.create({
   baseURL: '/api',
})

export async function uploadReference(file, description = 'PreState reference routine') {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post(`/reference?description=${encodeURIComponent(description)}`, form)
  return res.data
}

export async function submitReview(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post('/review', form)
  return res.data
}

export async function listProjects() {
  const res = await api.get('/projects')
  return res.data
}

export async function listRoutines(projectId) {
  const res = await api.get(`/project/${projectId}/routines`)
  return res.data
}

export async function compareProjects(params) {
  const {
    projectAId,
    projectRefId,
    routineName,
    normalise,
    programTypes,
    units
  } = params

  const query = new URLSearchParams({
    project_a_id:   projectAId,
    project_ref_id: projectRefId,
    routine_name:   routineName,
    normalise:      normalise,
  })

  if (programTypes?.length) {
    programTypes.forEach(t => query.append('program_types', t))
  }
  if (units?.length) {
    units.forEach(u => query.append('units', u))
  }

  const res = await api.post(`/project/compare?${query.toString()}`)
  return res.data
}

export async function uploadProject(file, versionLabel = 'v1') {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post(
    `/project/upload?version_label=${encodeURIComponent(versionLabel)}`,
    form
  )
  return res.data
}

export async function sendAgentMessage(messages) {
  const res = await api.post('/agent/chat', { messages })
  return {
    response:       res.data.response,
    toolCallsMade:  res.data.tool_calls_made,
  }
}