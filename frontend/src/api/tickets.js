import { authenticatedClient } from './client'

const tickets = authenticatedClient({ baseURL: '/api/tickets', timeout: 20_000 })

export async function listTickets(status) {
  const { data } = await tickets.get('', { params: status ? { status } : {} })
  return data
}

export async function readTicket(id) {
  const { data } = await tickets.get('/' + id)
  return data
}

export async function createTicket(payload) {
  const { data } = await tickets.post('', payload)
  return data
}

export async function updateTicketStatus(id, status, version) {
  const { data } = await tickets.patch(`/${id}/status`, { status, version })
  return data
}
