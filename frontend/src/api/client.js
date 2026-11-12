import axios from 'axios'

export const TOKEN_KEY = 'customer-service.session'

export function authenticatedClient(options) {
  const client = axios.create(options)
  client.interceptors.request.use((config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) config.headers.Authorization = 'Bearer ' + token
    return config
  })
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) window.dispatchEvent(new Event('auth-expired'))
      return Promise.reject(error)
    },
  )
  return client
}
