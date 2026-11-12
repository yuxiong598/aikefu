import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import 'element-plus/es/components/alert/style/css'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/input/style/css'
import App from './App.vue'
import ChatView from './ChatView.vue'
import DocumentsView from './DocumentsView.vue'
import TicketsView from './TicketsView.vue'
import LoginView from './LoginView.vue'
import { useAuth } from './stores/auth'
import Workspace from './Workspace.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: DocumentsView, meta: { staff: true, title: '知识库管理' } },
    { path: '/documents/upload', component: App, meta: { staff: true, title: '文档预览' } },
    { path: '/chat', component: ChatView, meta: { title: '智能客服' } },
    { path: '/tickets', component: TicketsView, meta: { title: '售后工单' } },
    { path: '/login', component: LoginView, meta: { title: '账号登录' } },
  ],
})

const pinia = createPinia()
router.beforeEach(async (to) => {
  const auth = useAuth(pinia)
  try { await auth.restore() } catch { return to.path === '/login' ? true : '/login' }
  if (!auth.user && to.path !== '/login') return '/login'
  if (auth.user && to.path === '/login') return auth.isStaff ? '/' : '/chat'
  if (to.meta.staff && !auth.isStaff) return '/chat'
})
router.afterEach((to) => {
  document.title = to.meta.title + ' | 智能客服知识库'
})

createApp(Workspace).use(pinia).use(router).mount('#app')
