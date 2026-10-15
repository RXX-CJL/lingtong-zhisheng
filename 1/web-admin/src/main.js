import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import './styles/global.scss'
// 设计令牌（必须晚于 element-plus 与 global.scss，才能覆盖 EP 主题变量）
// 2026-10-03 由 DSH 新增：消除 Element Plus 默认主题的 "AI 生成感"
import './styles/design-tokens.css'
import logger, { installVueErrorHandler } from './utils/logger'

// ===== 前端日志：接入全局路由记录 =====
// navigator 记录（进入每一条路由时）
router.beforeEach((to, from, next) => {
  to.meta.__navStart = Date.now()
  logger.tag('router').info(
    `NAVIGATE: ${from.fullPath || '(init)'} --> ${to.fullPath}`,
    { routeName: to.name?.toString() || '', path: to.path }
  )
  next()
})
router.afterEach((to, from) => {
  const start = to.meta && to.meta.__navStart
  const cost = start ? Date.now() - start : -1
  logger.tag('router').debug(
    `NAVIGATE-DONE ${to.fullPath} cost=${cost}ms`,
    { name: to.name?.toString() || '', hash: to.hash }
  )
})
router.onError(err => {
  logger.tag('router').fatal('Router.onError:', err)
})

const app = createApp(App)

// ===== 前端日志：Vue 全局错误 =====
installVueErrorHandler(app)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia()).use(router).use(ElementPlus).mount('#app')

logger.info('App mounted. router ready.')
