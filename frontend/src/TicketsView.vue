<script setup>
import { ElAlert, ElButton, ElInput } from 'element-plus'
import { computed, onActivated, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { readConversation } from './api/chat'
import { useAuth } from './stores/auth'
import { createTicket, listTickets, readTicket, updateTicketStatus } from './api/tickets'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const labels = { pending: '待处理', processing: '处理中', completed: '已完成' }
const tickets = ref([])
const detail = shallowRef(null)
const filter = ref('')
const title = ref('')
const description = ref('')
const source = shallowRef(null)
const showForm = ref(false)
const pending = shallowRef(null)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const formValid = computed(() => {
  const titleLength = Array.from(title.value.trim()).length
  const descriptionLength = Array.from(description.value.trim()).length
  return titleLength > 0 && titleLength <= 120 && descriptionLength > 0 && descriptionLength <= 5000
})

async function refresh() {
  tickets.value = await listTickets(filter.value)
}

async function run(operation, fallback) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    await operation()
  } catch (exception) {
    const message = exception.response?.data?.detail
    error.value = typeof message === 'string' ? message : fallback
  } finally {
    busy.value = false
  }
}

function beginManual() {
  source.value = null
  title.value = ''
  description.value = ''
  showForm.value = true
  error.value = ''
}

async function activate() {
  await run(async () => {
    await refresh()
    const conversation = route.query.conversation
    if (typeof conversation === 'string' && !pending.value) {
      const context = await readConversation(conversation)
      source.value = context
      title.value = Array.from(context.title).slice(0, 120).join('')
      description.value = context.turns.at(-1)?.question || ''
      showForm.value = true
      // 消费入口参数，后续切换页面不会覆盖尚未提交的表单。
      await router.replace('/tickets')
    }
  }, '无法加载工单或关联会话。')
}

onActivated(activate)
watch(() => route.query.conversation, (value) => {
  if (route.path === '/tickets' && value) activate()
})

function openDetail(id) {
  return run(async () => { detail.value = await readTicket(id) }, '工单详情加载失败。')
}

function submit() {
  if (!pending.value && !formValid.value) return
  return run(async () => {
    pending.value ??= {
      request_id: crypto.randomUUID(),
      title: title.value.trim(),
      description: description.value.trim(),
      conversation_id: source.value?.id || null,
    }
    try {
      detail.value = await createTicket(pending.value)
    } catch (exception) {
      if (exception.response && exception.response.status < 500) pending.value = null
      throw exception
    }
    pending.value = null
    showForm.value = false
    notice.value = '工单已创建。'
    // 列表刷新失败时，已经创建的工单详情仍可查看。
    await refresh()
  }, '暂未收到创建结果，请使用原内容重试。')
}

function changeStatus() {
  const current = detail.value
  if (!current || current.status === 'completed') return
  return run(async () => {
    const next = current.status === 'pending' ? 'processing' : 'completed'
    try {
      detail.value = await updateTicketStatus(current.id, next, current.version)
    } catch (exception) {
      if (exception.response?.status === 409) detail.value = await readTicket(current.id)
      throw exception
    }
    await refresh()
    notice.value = '工单状态已更新。'
  }, '状态更新失败，请刷新详情后重试。')
}
</script>

<template>
  <main class="workspace">
    <p class="eyebrow">售后支持 / 工单管理</p>
    <div class="section-heading">
      <h1>售后工单</h1>
      <el-button type="primary" :disabled="busy || Boolean(pending)" @click="beginManual">新建工单</el-button>
    </div>
    <p class="intro">记录需要人工跟进的问题，并查看处理进度。</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <el-alert v-if="notice" :title="notice" type="success" :closable="false" show-icon />

    <form v-if="showForm" class="panel ticket-section" @submit.prevent="submit">
      <h2>{{ source ? '基于会话创建工单' : '创建售后工单' }}</h2>
      <p v-if="source" class="hint">关联会话「{{ source.title }}」，提交时会保存最近 20 轮会话。</p>
      <label for="ticket-title" class="field-label">工单标题</label>
      <el-input id="ticket-title" v-model="title" :disabled="busy || Boolean(pending)" placeholder="最多 120 个字符" />
      <label for="ticket-description" class="field-label description-label">问题描述</label>
      <el-input
        id="ticket-description" v-model="description" type="textarea" :rows="4"
        :disabled="busy || Boolean(pending)" placeholder="请说明具体问题和希望获得的处理，最多 5000 个字符"
      />
      <div class="actions">
        <el-button native-type="submit" type="primary" :loading="busy" :disabled="busy || (!pending && !formValid)">
          {{ pending && !busy ? '重试创建' : '提交工单' }}
        </el-button>
        <el-button :disabled="busy || Boolean(pending)" @click="showForm = false">取消</el-button>
      </div>
    </form>

    <section class="panel ticket-section" aria-labelledby="ticket-list-title">
      <div class="section-heading">
        <h2 id="ticket-list-title">工单列表</h2>
        <el-button size="small" :disabled="busy" @click="run(refresh, '刷新失败。')">刷新列表</el-button>
      </div>
      <label for="ticket-filter" class="filter-label">处理状态</label>
      <select id="ticket-filter" v-model="filter" :disabled="busy" @change="run(refresh, '筛选失败。')">
        <option value="">全部</option>
        <option v-for="(label, value) in labels" :key="value" :value="value">{{ label }}</option>
      </select>
      <p v-if="!tickets.length" class="empty">{{ busy ? '正在加载…' : '当前没有工单。' }}</p>
      <ul v-else class="ticket-list">
        <li v-for="ticket in tickets" :key="ticket.id">
          <div>
            <strong>{{ ticket.title }}</strong>
            <p class="hint">工单 #{{ ticket.id }} · {{ ticket.conversation_id ? '来自客服会话' : '手动创建' }}</p>
          </div>
          <span class="ticket-status" :data-status="ticket.status">{{ labels[ticket.status] }}</span>
          <el-button size="small" :disabled="busy" @click="openDetail(ticket.id)">查看详情</el-button>
        </li>
      </ul>
    </section>

    <section v-if="detail" class="panel ticket-section" aria-labelledby="ticket-detail-title">
      <div class="section-heading">
        <h2 id="ticket-detail-title">工单 #{{ detail.id }} · {{ detail.title }}</h2>
        <el-button size="small" :disabled="busy" @click="detail = null">关闭详情</el-button>
      </div>
      <p class="hint">当前状态 · {{ labels[detail.status] }}</p>
      <p class="ticket-text">{{ detail.description }}</p>
      <el-button v-if="auth.isStaff && detail.status !== 'completed'" type="primary" :disabled="busy" @click="changeStatus">
        {{ detail.status === 'pending' ? '开始处理' : '标记完成' }}
      </el-button>
      <div v-if="detail.conversation_id" class="ticket-context">
        <h3>建单时的会话上下文</h3>
        <p v-if="!detail.conversation_snapshot.length" class="hint">该会话在建单时没有消息。</p>
        <article v-for="turn in detail.conversation_snapshot" :key="turn.id">
          <p class="ticket-text"><strong>用户</strong> {{ turn.question }}</p>
          <p class="ticket-text"><strong>智能客服</strong> {{ turn.answer }}</p>
          <blockquote v-for="source in turn.sources" :key="source.citation" class="ticket-text">
            {{ source.filename }} · 片段 {{ source.position }}<br />{{ source.text }}
          </blockquote>
        </article>
      </div>
    </section>
  </main>
</template>

<style scoped>
.ticket-section { margin-top: 16px; }
.ticket-section h2 { overflow-wrap: anywhere; }
.ticket-section .field-label { margin-top: 14px; }
.filter-label { margin-right: 10px; font-size: 14px; }
select { margin-top: 16px; padding: 7px 10px; border: 1px solid #b6c9ce; border-radius: 5px; background: white; color: #172b36; }
.ticket-list { list-style: none; padding: 0; margin: 12px 0 0; }
.ticket-list li { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 12px; align-items: center; padding: 13px 0; border-top: 1px solid #dce5e7; }
.ticket-list strong { overflow-wrap: anywhere; }
.ticket-list .hint { margin: 5px 0 0; }
.ticket-status { padding: 4px 8px; border-radius: 5px; background: #edf2f4; color: #506371; font-size: 13px; }
.ticket-status[data-status='processing'] { background: #fff3d5; color: #77530b; }
.ticket-status[data-status='completed'] { background: #eaf6f1; color: #14574e; }
.ticket-text { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.7; }
.ticket-context { margin-top: 20px; padding-top: 12px; border-top: 1px solid #dce5e7; }
.ticket-context article { padding: 0 12px; border: 1px solid #dce5e7; border-radius: 8px; margin-top: 12px; }
.ticket-context blockquote { margin: 9px 0; color: #506371; font-size: 13px; }
@media (max-width: 700px) { .ticket-list li { grid-template-columns: minmax(0, 1fr) auto; } .ticket-list .el-button { grid-column: 1 / -1; justify-self: start; } }
</style>
