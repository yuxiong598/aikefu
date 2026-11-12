<script setup>
import { ElAlert, ElButton, ElInput } from 'element-plus'
import { computed, ref, shallowRef } from 'vue'
import { confirmDocument, previewChunks, uploadDocument } from './api/documents'

const MAX_FILE_SIZE = 10 * 1024 * 1024
const MAX_CHUNK_LENGTH = 500
const steps = ['上传文档', '核对正文', '核对片段']

const fileInput = ref(null)
const selectedFile = shallowRef(null)
const filename = ref('')
const text = ref('')
const chunks = ref([])
const busyAction = ref('')
const errorMessage = ref('')
const pendingConfirmation = shallowRef(null)
const confirmationResult = shallowRef(null)

const activeStep = computed(() => (chunks.value.length ? 3 : filename.value ? 2 : 1))
const textLength = computed(() => Array.from(text.value).length)
const uploadLocked = computed(() => Boolean(busyAction.value || pendingConfirmation.value))
const draftLocked = computed(() => uploadLocked.value || Boolean(confirmationResult.value))
const invalidChunk = computed(() => chunks.value.find(
  ({ text }) => !text.trim() || Array.from(text).length > MAX_CHUNK_LENGTH,
))

function selectFile(event) {
  const input = event.target
  const file = input.files?.[0]
  // 允许重新选择同一份文件。
  input.value = ''
  if (!file) return

  errorMessage.value = ''
  selectedFile.value = null
  if (!/\.(pdf|docx)$/i.test(file.name)) {
    errorMessage.value = '请选择 .pdf 或 .docx 文件。'
    return
  }
  if (file.size > MAX_FILE_SIZE) {
    errorMessage.value = '单个文件不得超过 10 MiB。'
    return
  }
  selectedFile.value = file
}

function updateText(value) {
  text.value = value
  // 正文发生变化后，旧片段不能代表当前版本。
  chunks.value = []
  errorMessage.value = ''
}

function showError(error, fallback) {
  const detail = error.response?.data?.detail
  errorMessage.value = typeof detail === 'string' ? detail : fallback
}

async function parseSelectedFile() {
  if (!selectedFile.value || uploadLocked.value) return
  busyAction.value = 'upload'
  errorMessage.value = ''
  try {
    const preview = await uploadDocument(selectedFile.value)
    confirmationResult.value = null
    filename.value = preview.filename
    updateText(preview.text)
  } catch (error) {
    showError(error, '解析请求失败，请检查后端是否运行后再试。')
  } finally {
    busyAction.value = ''
  }
}

async function generatePreview() {
  if (!text.value.trim() || draftLocked.value) return
  busyAction.value = 'chunks'
  errorMessage.value = ''
  try {
    chunks.value = await previewChunks(text.value)
  } catch (error) {
    showError(error, '切分请求失败，请稍后重试。')
  } finally {
    busyAction.value = ''
  }
}

async function submitConfirmation() {
  if (busyAction.value || confirmationResult.value || !chunks.value.length || invalidChunk.value) return
  busyAction.value = 'confirm'
  errorMessage.value = ''
  try {
    // 保存用户确认时的副本，重试时复用同一份内容与 UUID。
    pendingConfirmation.value ??= {
      request_id: crypto.randomUUID(),
      filename: filename.value,
      chunks: chunks.value.map(({ text }) => text),
    }
    confirmationResult.value = await confirmDocument(pendingConfirmation.value)
    pendingConfirmation.value = null
    selectedFile.value = null
  } catch (error) {
    const status = error.response?.status
    if (status === 409 || status === 422) {
      pendingConfirmation.value = null
      showError(error, '确认内容未通过校验，请检查文件名和片段后重新提交。')
    } else if (pendingConfirmation.value) {
      showError(error, '暂未收到入库结果，请点击「重试入库」。')
    } else {
      errorMessage.value = '无法生成入库请求编号，请通过本机预览地址或 HTTPS 打开页面。'
    }
  } finally {
    busyAction.value = ''
  }
}
</script>

<template>
  <main class="workspace">
    <p class="eyebrow">知识库管理 / 文档预览</p>
    <RouterLink class="back-link" to="/">返回文档列表</RouterLink>
    <h1>文档预览</h1>
    <p class="intro">从 PDF 或 Word 提取正文，核对知识片段后确认入库。</p>

    <ol class="steps" aria-label="文档处理进度">
      <li
        v-for="(label, index) in steps"
        :key="label"
        :class="{ current: activeStep === index + 1, complete: activeStep > index + 1 }"
        :aria-current="activeStep === index + 1 ? 'step' : undefined"
      >
        <span class="step-number">{{ index + 1 }}</span>
        {{ label }}
      </li>
    </ol>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />

    <div class="work-grid">
      <section class="panel upload-panel" aria-labelledby="upload-title">
        <h2 id="upload-title">上传文档</h2>
        <p class="hint">支持有文字层的 PDF 和 .docx，单个文件最多 10 MiB。</p>
        <div class="file-box">
          <span class="file-tag">文档</span>
          <span class="file-name">{{ selectedFile?.name || '尚未选择文件' }}</span>
        </div>
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,.docx"
          hidden
          :disabled="uploadLocked"
          @change="selectFile"
        />
        <div class="actions">
          <el-button :disabled="uploadLocked" @click="fileInput.click()">选择文件</el-button>
          <el-button
            type="primary"
            :loading="busyAction === 'upload'"
            :disabled="!selectedFile || uploadLocked"
            @click="parseSelectedFile"
          >
            上传并解析
          </el-button>
        </div>
      </section>

      <section class="panel" aria-labelledby="editor-title">
        <h2 id="editor-title">核对正文</h2>
        <p class="hint">在生成片段前，可以修正错字或删除无关内容。</p>
        <label class="field-label" for="document-text">
          {{ filename ? '当前文档 · ' + filename : '文档正文' }}
        </label>
        <el-input
          id="document-text"
          :model-value="text"
          type="textarea"
          :rows="9"
          placeholder="上传解析成功后，正文将在这里显示。"
          :disabled="!filename || draftLocked"
          @update:model-value="updateText"
        />
        <div class="editor-footer">
          <span class="hint" role="status">{{ textLength }} 字符</span>
          <el-button
            type="primary"
            :loading="busyAction === 'chunks'"
            :disabled="!text.trim() || draftLocked"
            @click="generatePreview"
          >
            预览切分
          </el-button>
        </div>
      </section>
    </div>

    <section class="panel chunks-panel" aria-labelledby="chunks-title">
      <div class="section-heading">
        <h2 id="chunks-title">核对片段</h2>
        <span v-if="chunks.length" class="count" role="status">{{ chunks.length }} 个片段</span>
      </div>
      <p v-if="!chunks.length" class="empty">核对正文后，点击「预览切分」生成片段。</p>
      <template v-else>
        <p v-if="!draftLocked" class="hint">请逐条核对片段。每条最多 {{ MAX_CHUNK_LENGTH }} 个字符。</p>
        <ol class="chunk-list">
          <li v-for="chunk in chunks" :key="chunk.index">
            <label class="field-label" :for="'chunk-' + chunk.index">片段 {{ chunk.index }}</label>
            <el-input
              :id="'chunk-' + chunk.index"
              v-model="chunk.text"
              type="textarea"
              :rows="4"
              :disabled="draftLocked"
            />
          </li>
        </ol>
        <div class="confirmation">
          <el-alert
            v-if="confirmationResult"
            :title="`入库成功 · 文档编号 ${confirmationResult.document_id} · ${confirmationResult.chunk_count} 个片段`"
            type="success"
            :closable="false"
            show-icon
          />
          <div v-else class="editor-footer">
            <span class="hint" role="status">
              <template v-if="busyAction === 'confirm'">正在写入知识库，首次加载模型可能较慢。</template>
              <template v-else-if="pendingConfirmation">已保留这次提交，请重试入库。</template>
              <template v-else-if="invalidChunk">
                请检查片段 {{ invalidChunk.index }}，内容不能为空白，且最多 {{ MAX_CHUNK_LENGTH }} 个字符。
              </template>
            </span>
            <el-button
              type="primary"
              :loading="busyAction === 'confirm'"
              :disabled="Boolean(busyAction || invalidChunk)"
              @click="submitConfirmation"
            >
              <template v-if="busyAction === 'confirm'">正在入库</template>
              <template v-else>{{ pendingConfirmation ? '重试入库' : '确认入库' }}</template>
            </el-button>
          </div>
        </div>
      </template>
    </section>
  </main>
</template>

<style>
:root {
  font-family: 'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif;
  color: #172b36;
  background: #f3f6f7;
  --el-color-primary: #11685f;
}

* { box-sizing: border-box; }
body { margin: 0; }

.masthead { background: #122d38; color: #f0f7f7; }
.masthead-inner {
  max-width: 1200px;
  min-height: 64px;
  margin: auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-mark {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 8px;
  background: #a8e4cf;
  color: #122d38;
  font-weight: 700;
}
.brand-name { font-weight: 700; }
.masthead-section { margin-left: auto; font-size: 13px; color: #bbd2d7; }

.workspace { max-width: 1200px; margin: auto; padding: 34px 24px 56px; }
.eyebrow { margin: 0 0 9px; color: #11685f; font-size: 13px; font-weight: 700; }
.back-link { display: inline-block; margin-bottom: 12px; color: #11685f; font-size: 14px; }
h1 { margin: 0; font-size: clamp(28px, 5vw, 40px); line-height: 1.2; }
h2 { margin: 0; font-size: 20px; }
.intro { margin: 12px 0 24px; color: #506371; line-height: 1.65; }

.steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin: 0 0 18px;
  padding: 0;
  list-style: none;
}
.steps li {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 12px;
  border: 1px solid #dce5e7;
  border-radius: 9px;
  background: #fff;
  color: #506371;
  font-size: 14px;
}
.steps .current { border-color: #81b8a9; background: #eaf6f1; color: #14574e; font-weight: 700; }
.steps .complete { color: #14574e; }
.step-number {
  display: grid;
  flex: 0 0 26px;
  height: 26px;
  place-items: center;
  border-radius: 50%;
  background: #edf2f4;
  font-weight: 700;
}
.current .step-number { color: #fff; background: #11685f; }

.work-grid {
  display: grid;
  grid-template-columns: minmax(255px, 1fr) minmax(0, 2fr);
  align-items: start;
  gap: 16px;
  margin-top: 18px;
}
.panel { min-width: 0; padding: 22px; border: 1px solid #dce5e7; border-radius: 12px; background: #fff; }
.hint { margin: 9px 0 15px; color: #506371; font-size: 14px; line-height: 1.6; }
.file-box {
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 58px;
  padding: 12px;
  border: 1px dashed #b6c9ce;
  border-radius: 8px;
  background: #f8fafb;
}
.file-tag { flex-shrink: 0; color: #14574e; font-size: 12px; font-weight: 700; }
.file-name { overflow-wrap: anywhere; font-size: 14px; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 15px; }
.actions .el-button + .el-button { margin-left: 0; }
.field-label { display: block; margin-bottom: 8px; overflow-wrap: anywhere; font-size: 14px; font-weight: 700; }
.editor-footer, .section-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.editor-footer { margin-top: 12px; }
.editor-footer .hint { margin: 0; }

.chunks-panel { margin-top: 16px; }
.count { color: #14574e; font-size: 14px; }
.empty {
  margin: 15px 0 0;
  padding: 18px;
  border-radius: 8px;
  background: #f3f6f7;
  color: #506371;
  font-size: 14px;
}
.chunk-list { display: grid; gap: 14px; padding: 0; margin: 0; list-style: none; }
.chunk-list li { min-width: 0; padding: 13px; border: 1px solid #e1e8e9; border-radius: 8px; }
.confirmation { margin-top: 16px; }

@media (max-width: 700px) {
  .masthead-inner { padding: 0 16px; }
  .workspace { padding: 24px 16px 40px; }
  .work-grid { grid-template-columns: 1fr; }
  .panel { padding: 17px; }
  .steps li { gap: 5px; padding: 8px 6px; font-size: 12px; }
  .step-number { flex-basis: 21px; height: 21px; }
}
</style>
