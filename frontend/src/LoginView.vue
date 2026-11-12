<script setup>
import { ElAlert, ElButton, ElInput } from 'element-plus'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from './stores/auth'

const auth = useAuth()
const router = useRouter()
const username = ref('')
const password = ref('')
const registering = ref(false)
const busy = ref(false)
const error = ref('')

async function submit() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await auth.signIn({ username: username.value, password: password.value }, registering.value)
    password.value = ''
    await router.replace(auth.isStaff ? '/' : '/chat')
  } catch (exception) {
    const message = exception.response?.data?.detail
    error.value = typeof message === 'string' ? message : '请检查账号格式和密码，稍后重试。'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="workspace login-workspace">
    <form class="panel login-panel" @submit.prevent="submit">
      <p class="eyebrow">智能客服与售后支持</p>
      <h1>{{ registering ? '注册账号' : '登录账号' }}</h1>
      <p class="hint">账号为 3–32 位英文字母、数字或下划线，密码为 8–128 个字符。</p>
      <el-alert v-if="error" :title="error" type="error" :closable="false" />
      <label class="field-label" for="login-username">用户名</label>
      <el-input id="login-username" v-model="username" autocomplete="username" :disabled="busy" />
      <label class="field-label" for="login-password">密码</label>
      <el-input
        id="login-password" v-model="password" type="password" show-password
        :autocomplete="registering ? 'new-password' : 'current-password'" :disabled="busy"
      />
      <div class="actions">
        <el-button native-type="submit" type="primary" :loading="busy" :disabled="busy">
          {{ registering ? '注册并登录' : '登录' }}
        </el-button>
        <el-button :disabled="busy" @click="registering = !registering; error = ''">
          {{ registering ? '已有账号，去登录' : '注册普通用户' }}
        </el-button>
      </div>
    </form>
  </main>
</template>

<style scoped>
.login-workspace { max-width: 550px; padding-top: 60px; }
.login-panel .field-label { margin-top: 18px; }
.login-panel h1 { font-size: 30px; }
</style>
