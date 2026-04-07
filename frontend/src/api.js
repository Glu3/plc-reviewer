import axios from 'axios'

const api = axios.create({
   baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
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