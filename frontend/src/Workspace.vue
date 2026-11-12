<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useAuth } from './stores/auth'

const auth = useAuth()
const claiming = ref(false)
const claimNotice = ref('')

function expired() {
  auth.clear()
  window.location.reload()
}

onMounted(() => window.addEventListener('auth-expired', expired))
onUnmounted(() => window.removeEventListener('auth-expired', expired))

async function claim() {
  claiming.value = true
  try {
    const result = await auth.claimBrowser()
    claimNotice.value = `已认领 ${result.conversations} 个会话、${result.tickets} 张工单。请刷新页面查看。`
  } catch (error) {
    claimNotice.value = error.response?.data?.detail || '认领失败，请稍后重试。'
  } finally {
    claiming.value = false
  }
}
</script>

<template>
  <header class="masthead">
    <div class="masthead-inner">
      <span class="brand-mark" aria-hidden="true">知</span>
      <span class="brand-name">智能客服知识库</span>
      <nav v-if="auth.user" class="masthead-section workspace-nav" aria-label="主导航">
        <RouterLink v-if="auth.isStaff" to="/">知识库管理</RouterLink>
        <RouterLink to="/chat">智能客服</RouterLink>
        <RouterLink to="/tickets">售后工单</RouterLink>
      </nav>
    </div>
  </header>
  <div v-if="auth.user" class="account-bar">
    <span>{{ auth.user.username }} · {{ auth.isStaff ? '客服' : '普通用户' }}</span>
    <button type="button" :disabled="claiming" @click="claim">认领本浏览器历史数据</button>
    <button type="button" @click="auth.signOut">退出登录</button>
    <span v-if="claimNotice" role="status">{{ claimNotice }}</span>
  </div>
  <RouterView v-slot="{ Component }">
    <KeepAlive :key="auth.user?.id || 'anonymous'">
      <component :is="Component" />
    </KeepAlive>
  </RouterView>
</template>

<style scoped>
.workspace-nav { display: flex; flex-wrap: wrap; gap: 6px; }
.workspace-nav a { padding: 7px 9px; border-radius: 6px; color: #bbd2d7; text-decoration: none; }
.workspace-nav .router-link-exact-active { color: #fff; background: #2b515b; }
.account-bar { max-width: 1200px; margin: auto; padding: 10px 24px; display: flex; flex-wrap: wrap; align-items: center; gap: 12px; font-size: 13px; }
.account-bar button { border: 1px solid #b6c9ce; border-radius: 5px; background: white; color: #14574e; padding: 5px 9px; cursor: pointer; }
</style>
