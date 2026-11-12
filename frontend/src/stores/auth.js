import axios from 'axios'
import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import { TOKEN_KEY } from '../api/client'

const api = axios.create({ baseURL: '/api/auth', timeout: 15_000 })

export const useAuth = defineStore('auth', () => {
  const user = shallowRef(null)
  const restored = ref(false)
  const isStaff = computed(() => user.value?.role === 'staff')

  function headers() {
    return { Authorization: 'Bearer ' + localStorage.getItem(TOKEN_KEY) }
  }

  function clear() {
    localStorage.removeItem(TOKEN_KEY)
    user.value = null
    restored.value = true
  }

  async function restore() {
    if (restored.value) return
    if (localStorage.getItem(TOKEN_KEY)) {
      try {
        const { data } = await api.get('/me', { headers: headers() })
        user.value = data
      } catch (error) {
        if (error.response?.status === 401) clear()
        else throw error
      }
    }
    restored.value = true
  }

  async function signIn(credentials, register) {
    if (register) await api.post('/register', credentials)
    const { data } = await api.post('/login', credentials)
    localStorage.setItem(TOKEN_KEY, data.token)
    user.value = data.user
    restored.value = true
  }

  async function signOut() {
    try {
      await api.post('/logout', null, { headers: headers() })
    } finally {
      clear()
      // 刷新清理各模块的草稿与会话缓存。
      window.location.reload()
    }
  }

  async function claimBrowser() {
    const browserId = localStorage.getItem('customer-service.chat-client')
    if (!browserId) return { conversations: 0, tickets: 0 }
    const { data } = await api.post('/claim-browser', { browser_id: browserId }, { headers: headers() })
    return data
  }

  return { user, isStaff, restore, clear, signIn, signOut, claimBrowser }
})
