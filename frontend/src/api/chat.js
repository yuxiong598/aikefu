import { authenticatedClient } from './client'

const chat = authenticatedClient({ baseURL: '/api/chat/conversations', timeout: 75_000 })

export async function listConversations() {
  const { data } = await chat.get('')
  return data
}

export async function readConversation(id) {
  const { data } = await chat.get('/' + id)
  return data
}

export async function sendQuestion(id, question) {
  const { data } = await chat.post(`/${id}/messages`, question)
  return data
}
