<template>
  <div class="app-container">
    <el-container>
      <el-header class="app-header">
        <div class="logo">
          <el-icon size="24"><VideoCamera /></el-icon>
          <span>智瞳灵声管理端</span>
        </div>
        <el-menu
          mode="horizontal"
          :default-active="currentRoute"
          router
          class="header-menu"
        >
          <el-menu-item index="/">
            <el-icon><DataAnalysis /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/violations">
            <el-icon><Document /></el-icon>
            <span>违规管理</span>
          </el-menu-item>
          <el-menu-item index="/ai-detect">
            <el-icon><VideoCamera /></el-icon>
            <span>智能识别</span>
          </el-menu-item>
          <el-menu-item index="/disagreements">
            <el-icon><WarningFilled /></el-icon>
            <span>分歧审核</span>
          </el-menu-item>
          <el-menu-item index="/statistics">
            <el-icon><PieChart /></el-icon>
            <span>统计分析</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
        </el-menu>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  VideoCamera,
  DataAnalysis,
  Document,
  PieChart,
  WarningFilled,
  Setting
} from '@element-plus/icons-vue'

const route = useRoute()
// 子路由 → 主菜单项映射：访问子页面时高亮对应主菜单
const subToMain = {
  '/events': '/violations',
  '/appeals': '/violations',
  '/realtime': '/ai-detect',
  '/ai-trace': '/ai-detect',
  '/collab-stats': '/statistics',
  '/devices': '/settings',
  '/quota': '/settings',
  '/system-log': '/settings',
  '/about': '/settings'
}
const currentRoute = computed(() => {
  const p = route.path
  // 匹配 /events/:id 等带参数的子路由
  for (const [sub, main] of Object.entries(subToMain)) {
    if (p === sub || p.startsWith(sub + '/')) return main
  }
  return p
})
</script>

<style scoped lang="scss">
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

:deep(.el-container) {
  flex: 1;
  min-height: 0;
}

:deep(.el-header) {
  height: 60px !important;
}

.app-header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
  height: 60px;

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 18px;
    font-weight: 600;
    color: #1890ff;
    margin-right: 30px;
    flex-shrink: 0;
    white-space: nowrap;

    .el-icon {
      flex-shrink: 0;
    }

    span {
      display: inline-block;
      white-space: nowrap;
      word-break: keep-all;
      line-height: 1;
    }
  }

  .header-menu {
    flex: 1;
    border-bottom: none;
  }
}

:deep(.el-main) {
  padding: 20px;
  background: #f0f2f5;
  overflow-y: auto;
  height: calc(100vh - 60px);
}

.app-main {
  padding: 20px;
}
</style>