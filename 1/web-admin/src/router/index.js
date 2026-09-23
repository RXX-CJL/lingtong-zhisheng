import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('../views/Dashboard.vue')
    },
    {
      path: '/violations',
      name: 'ViolationList',
      component: () => import('../views/ViolationList.vue')
    },
    {
      path: '/violations/:id',
      name: 'ViolationDetail',
      component: () => import('../views/ViolationDetail.vue')
    },
    {
      path: '/events',
      name: 'EventCenter',
      component: () => import('../views/EventCenter.vue')
    },
    {
      path: '/events/:id',
      name: 'EventDetail',
      component: () => import('../views/EventDetail.vue')
    },
    {
      path: '/devices',
      name: 'DeviceList',
      component: () => import('../views/DeviceList.vue')
    },
    {
      path: '/appeals',
      name: 'AppealList',
      component: () => import('../views/AppealList.vue')
    },
    {
      path: '/ai-detect',
      name: 'AIDetect',
      component: () => import('../views/AIDetect.vue')
    },
    {
      path: '/ai-trace',
      name: 'AITrace',
      component: () => import('../views/AITrace.vue')
    },
    {
      path: '/realtime',
      name: 'RealTimeMonitor',
      component: () => import('../views/RealTimeMonitor.vue')
    },
    {
      path: '/collab-stats',
      name: 'CollabStats',
      component: () => import('../views/CollabStats.vue')
    },
    {
      path: '/disagreements',
      name: 'DisagreementList',
      component: () => import('../views/DisagreementList.vue')
    },
    {
      path: '/quota',
      name: 'QuotaMonitor',
      component: () => import('../views/QuotaMonitor.vue')
    },
    {
      path: '/statistics',
      name: 'Statistics',
      component: () => import('../views/Statistics.vue')
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('../views/Settings.vue')
    },
    {
      path: '/system-log',
      name: 'SystemLog',
      component: () => import('../views/SystemLog.vue')
    },
    {
      path: '/about',
      name: 'About',
      component: () => import('../views/About.vue')
    }
  ]
})

export default router