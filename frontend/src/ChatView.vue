<script setup>
import { ElAlert, ElButton, ElInput } from 'element-plus'
import { nextTick, onMounted, ref, watch } from 'vue'
import { useChat } from './stores/chat'
import { useRouter } from 'vue-router'

const chat = useChat()
const router = useRouter()
const latestTurn = ref(null)

onMounted(() => chat.initialize())
watch(() => chat.turns.length, async () => {
  await nextTick()
  latestTurn.value?.scrollIntoView({ block: 'nearest' })
})
</script>

<template>
  <main class="workspace chat-workspace">
    <header>
      <p class="eyebrow">售后支持 / 智能客服</p>
      <h1>智能客服问答</h1>
      <p class="intro">询问退换货、订单或其他售后问题，回答下方会显示使用的知识库来源。</p>
      <el-button
        v-if="chat.activeId && chat.turns.length"
        :disabled="Boolean(chat.action || chat.pending)"
        @click="router.push({ path: '/tickets', query: { conversation: chat.activeId } })"
      >基于当前会话创建工单</el-button>
    </header>
    <div class="chat-grid">
      <aside class="panel conversation-list" aria-label="会话列表">
        <div class="section-heading">
          <h2>历史会话</h2>
          <el-button size="small" :disabled="Boolean(chat.action || chat.pending)" @click="chat.newConversation">
            新建会话
          </el-button>
        </div>
        <p v-if="!chat.conversations.length" class="hint">发送第一条消息后，会话会出现在这里。</p>
        <ul v-else>
          <li v-for="item in chat.conversations" :key="item.id">
            <button
              type="button"
              :aria-current="chat.activeId === item.id ? 'true' : undefined"
              :disabled="Boolean(chat.action || chat.pending)"
              @click="chat.openConversation(item.id)"
            >{{ item.title }}</button>
          </li>
        </ul>
      </aside>

      <section class="panel chat-panel" aria-label="客服对话">
        <div class="chat-log" aria-live="polite" aria-label="消息记录">
          <p v-if="!chat.turns.length && chat.action === 'loading'" class="hint">正在加载会话。</p>
          <div v-else-if="!chat.turns.length && !chat.pending" class="chat-empty">
            <h2>有什么可以帮你？</h2>
            <p class="hint">例如「签收后几天内可以退货？」</p>
          </div>
          <article v-for="turn in chat.turns" :key="turn.id" class="chat-turn">
            <p class="question"><strong>你</strong><span>{{ turn.question }}</span></p>
            <div class="answer">
              <strong>智能客服</strong>
              <p>{{ turn.answer }}</p>
              <div v-if="turn.sources.length" class="chat-sources">
                <h3>引用来源</h3>
                <ol>
                  <li v-for="source in turn.sources" :key="source.citation">
                    <span>来源 {{ source.citation }} · {{ source.filename }} · 片段 {{ source.position }}</span>
                    <blockquote>{{ source.text }}</blockquote>
                  </li>
                </ol>
              </div>
            </div>
          </article>
          <div ref="latestTurn"></div>
        </div>

        <form class="composer" @submit.prevent="chat.ask">
          <el-alert v-if="chat.error" :title="chat.error" type="error" :closable="false" show-icon />
          <label class="field-label" for="chat-question">你的问题</label>
          <el-input
            id="chat-question"
            v-model="chat.draft"
            type="textarea"
            :rows="3"
            placeholder="输入你的售后问题"
            :disabled="Boolean(chat.action || chat.pending)"
          />
          <div class="editor-footer">
            <span class="hint" role="status">
              {{ chat.action === 'sending' ? '正在检索并生成回答…' : chat.questionLength + ' / 500 字符' }}
            </span>
            <el-button
              native-type="submit"
              type="primary"
              :loading="chat.action === 'sending'"
              :disabled="Boolean(chat.action || (!chat.pending && (!chat.questionLength || chat.questionLength > 500)))"
            >
              {{ chat.pending && !chat.action ? '重试提问' : '发送问题' }}
            </el-button>
          </div>
          <el-button v-if="chat.pending && !chat.action" size="small" @click="chat.cancelRetry">
            取消本次重试
          </el-button>
        </form>
      </section>
    </div>
  </main>
</template>

<style scoped>
.chat-grid { display: grid; grid-template-columns: minmax(210px, 1fr) minmax(0, 3fr); gap: 16px; align-items: start; }
.conversation-list h2 { font-size: 16px; }
.conversation-list ul, .chat-sources ol { margin: 14px 0 0; padding: 0; list-style: none; }
.conversation-list button {
  width: 100%; text-align: left; padding: 9px 10px; margin-bottom: 5px;
  border: 1px solid #dce5e7; border-radius: 7px; background: white; color: #172b36;
  font: inherit; font-size: 14px; cursor: pointer; overflow-wrap: anywhere;
}
.conversation-list button[aria-current] { background: #eaf6f1; border-color: #81b8a9; }
.conversation-list button:disabled { cursor: default; }
.chat-panel { display: flex; flex-direction: column; gap: 16px; }
.chat-log { min-height: 220px; max-height: 58vh; overflow-y: auto; }
.chat-empty { padding: 52px 12px; text-align: center; }
.chat-turn { margin-bottom: 18px; overflow-wrap: anywhere; }
.question, .answer { padding: 12px 14px; border-radius: 9px; }
.question { display: flex; gap: 10px; background: #eaf6f1; }
.question strong { flex-shrink: 0; }
.answer { border: 1px solid #dce5e7; background: #f8fafb; line-height: 1.65; }
.answer p, .question span, .chat-sources blockquote { white-space: pre-wrap; }
.answer p { margin: 8px 0 0; }
.chat-sources { margin-top: 12px; border-top: 1px solid #dce5e7; }
.chat-sources h3 { margin: 10px 0 0; font-size: 14px; }
.chat-sources li { margin-bottom: 9px; font-size: 13px; }
.chat-sources blockquote { margin: 3px 0 0; color: #506371; }
.composer .el-alert { margin-bottom: 12px; }
@media (max-width: 700px) { .chat-grid { grid-template-columns: 1fr; } }
</style>
