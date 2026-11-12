import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import { listConversations, readConversation, sendQuestion } from '../api/chat'

const ACTIVE_KEY = 'customer-service.chat-active'

export const useChat = defineStore('chat', () => {
  const conversations = ref([])
  const turns = ref([])
  const activeId = ref(null)
  const draft = ref('')
  const pending = shallowRef(null)
  const action = ref('')
  const error = ref('')
  const questionLength = computed(() => Array.from(draft.value.trim()).length)

  function showError(exception, fallback) {
    const detail = exception.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : fallback
  }

  async function load(id) {
    const result = await readConversation(id)
    localStorage.setItem(ACTIVE_KEY, result.id)
    activeId.value = result.id
    turns.value = result.turns
    draft.value = ''
  }

  async function initialize() {
    action.value = 'loading'
    error.value = ''
    try {
      conversations.value = await listConversations()
      const remembered = localStorage.getItem(ACTIVE_KEY)
      const selected = conversations.value.find(({ id }) => id === remembered) || conversations.value[0]
      if (selected) await load(selected.id)
    } catch (exception) {
      showError(exception, '会话加载失败，请刷新页面重试。')
    } finally {
      action.value = ''
    }
  }

  async function openConversation(id) {
    if (action.value || pending.value || id === activeId.value) return
    action.value = 'loading'
    error.value = ''
    try {
      await load(id)
    } catch (exception) {
      showError(exception, '会话加载失败，请稍后重试。')
    } finally {
      action.value = ''
    }
  }

  function newConversation() {
    if (action.value || pending.value) return
    localStorage.removeItem(ACTIVE_KEY)
    activeId.value = null
    turns.value = []
    draft.value = ''
    error.value = ''
  }

  async function ask() {
    if (action.value || (!pending.value && (!questionLength.value || questionLength.value > 500))) return
    action.value = 'sending'
    error.value = ''
    try {
      // 超时后继续用原会话、问题和请求编号，避免重复保存同一轮。
      pending.value ??= {
        id: activeId.value || crypto.randomUUID(),
        payload: { request_id: crypto.randomUUID(), question: draft.value.trim() },
      }
      const { id, payload } = pending.value
      localStorage.setItem(ACTIVE_KEY, id)
      const turn = await sendQuestion(id, payload)
      activeId.value = id
      if (!turns.value.some(({ id }) => id === turn.id)) turns.value.push(turn)
      const title = conversations.value.find((item) => item.id === id)?.title
        || Array.from(turn.question).slice(0, 60).join('')
      conversations.value = [{ id, title }, ...conversations.value.filter((item) => item.id !== id)]
      draft.value = ''
      pending.value = null
    } catch (exception) {
      const status = exception.response?.status
      if (status && status < 500 && status !== 408) pending.value = null
      showError(exception, pending.value ? '暂未收到回答，请原样重试。' : '提问失败，请稍后重试。')
    } finally {
      action.value = ''
    }
  }

  function cancelRetry() {
    if (action.value) return
    pending.value = null
    error.value = ''
  }

  return {
    conversations, turns, activeId, draft, pending, action, error, questionLength,
    initialize, openConversation, newConversation, ask, cancelRetry,
  }
})
