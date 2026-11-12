<script setup>
import { ElAlert, ElButton } from 'element-plus'
import { onActivated, ref, shallowRef } from 'vue'
import { deleteDocument, listDocuments, readDocument, retryDocument } from './api/documents'

const labels = { pending: '待索引', indexed: '已索引', deleting: '待完成删除' }
const documents = ref([])
const detail = shallowRef(null)
const deleteTarget = shallowRef(null)
const busy = ref(false)
const error = ref('')
const notice = ref('')

async function refresh() {
  documents.value = await listDocuments()
  if (detail.value && !documents.value.some((item) => item.request_id === detail.value.request_id)) {
    detail.value = null
  }
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

onActivated(() => run(refresh, '无法加载文档列表，请刷新重试。'))

function openDetail(id) {
  return run(async () => {
    detail.value = await readDocument(id)
  }, '无法读取文档详情。')
}

function retry(id) {
  return run(async () => {
    const updated = await retryDocument(id)
    if (detail.value?.request_id === id) detail.value = updated
    await refresh()
    notice.value = '文档索引已完成。'
  }, '索引未完成，请稍后重试。')
}

function remove() {
  const id = deleteTarget.value?.request_id
  if (!id) return
  return run(async () => {
    deleteTarget.value = null
    try {
      await deleteDocument(id)
    } catch (exception) {
      // 若已记录删除意图，刷新列表即可提供「继续删除」入口。
      try { await refresh() } catch { /* 保留原删除错误 */ }
      throw exception
    }
    if (detail.value?.request_id === id) detail.value = null
    documents.value = documents.value.filter((item) => item.request_id !== id)
    notice.value = '文档已删除。'
  }, '无法确认删除结果，请刷新列表后重试。')
}
</script>

<template>
  <main class="workspace">
    <p class="eyebrow">知识库管理 / 文档列表</p>
    <div class="section-heading documents-header">
      <h1>知识库文档</h1>
      <RouterLink to="/documents/upload" class="upload-link">上传文档</RouterLink>
    </div>
    <p class="intro">查看已入库片段，处理待索引或待删除的文档。</p>

    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <el-alert v-if="notice" :title="notice" type="success" :closable="false" show-icon />

    <section v-if="deleteTarget" class="panel delete-panel" aria-labelledby="delete-title">
      <h2 id="delete-title">删除「{{ deleteTarget.filename }}」？</h2>
      <p class="hint">删除会移除文档片段和检索索引。</p>
      <div class="actions">
        <el-button :disabled="busy" @click="deleteTarget = null">取消</el-button>
        <el-button type="danger" :disabled="busy" @click="remove">确认删除</el-button>
      </div>
    </section>

    <section class="panel document-list" aria-labelledby="documents-title">
      <div class="section-heading">
        <h2 id="documents-title">文档列表</h2>
        <el-button size="small" :disabled="busy" @click="run(refresh, '无法刷新文档列表。')">刷新列表</el-button>
      </div>
      <p v-if="!documents.length" class="empty">{{ busy ? '正在加载文档…' : '还没有入库文档。' }}</p>
      <ul v-else>
        <li v-for="item in documents" :key="item.request_id" class="document-row">
          <div>
            <strong>{{ item.filename }}</strong>
            <p class="hint">{{ item.chunk_count }} 个片段 · 文档编号 {{ item.document_id }}</p>
          </div>
          <span class="document-status" :data-status="item.status">{{ labels[item.status] }}</span>
          <div class="actions">
            <el-button size="small" :disabled="busy" @click="openDetail(item.request_id)">片段详情</el-button>
            <el-button
              v-if="item.status === 'pending'" size="small" type="primary" :disabled="busy"
              @click="retry(item.request_id)"
            >重试索引</el-button>
            <el-button size="small" type="danger" plain :disabled="busy" @click="deleteTarget = item">
              {{ item.status === 'deleting' ? '继续删除' : '删除' }}
            </el-button>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="detail" class="panel detail-panel" aria-labelledby="detail-title">
      <div class="section-heading">
        <h2 id="detail-title">{{ detail.filename }} · 片段详情</h2>
        <el-button size="small" @click="detail = null">关闭详情</el-button>
      </div>
      <ol class="chunk-list">
        <li v-for="chunk in detail.chunks" :key="chunk.index">
          <strong>片段 {{ chunk.index }}</strong>
          <p>{{ chunk.text }}</p>
        </li>
      </ol>
    </section>
  </main>
</template>

<style scoped>
.upload-link { background: #11685f; color: #fff; text-decoration: none; padding: 9px 14px; border-radius: 7px; }
.document-list, .detail-panel, .delete-panel { margin-top: 16px; }
.document-list ul { list-style: none; margin: 12px 0 0; padding: 0; }
.document-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 12px;
  border-top: 1px solid #dce5e7;
  padding: 12px 0;
}
.document-row strong, .detail-panel h2 { overflow-wrap: anywhere; }
.document-row .actions, .document-row .hint { margin: 0; }
.document-status { color: #4f626d; background: #edf2f4; padding: 4px 8px; border-radius: 5px; font-size: 13px; }
.document-status[data-status='indexed'] { color: #14574e; background: #eaf6f1; }
.document-status[data-status='deleting'] { color: #943823; background: #fceeea; }
.detail-panel .chunk-list { margin-top: 15px; }
.detail-panel p { margin: 7px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; }
@media (max-width: 700px) {
  .document-row { grid-template-columns: minmax(0, 1fr) auto; }
  .document-row .actions { grid-column: 1 / -1; }
}
</style>
