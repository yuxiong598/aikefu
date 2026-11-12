import { authenticatedClient } from './client'

const documents = authenticatedClient({
  baseURL: '/api/documents',
  timeout: 60_000,
})

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  // 由浏览器生成 multipart 边界。
  const { data } = await documents.post('/preview', form)
  return data
}

export async function previewChunks(text) {
  const { data } = await documents.post('/chunks/preview', { text })
  return data.chunks
}

export async function confirmDocument(payload) {
  const { data } = await documents.post('/confirm', payload)
  return data
}

export async function listDocuments() {
  const { data } = await documents.get('')
  return data
}

export async function readDocument(id) {
  const { data } = await documents.get('/' + id)
  return data
}

export async function retryDocument(id) {
  const { data } = await documents.post(`/${id}/retry`)
  return data
}

export async function deleteDocument(id) {
  await documents.delete('/' + id)
}
