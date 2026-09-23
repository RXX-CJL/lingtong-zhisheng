/**
 * 首页 - Dashboard
 */
const app = getApp()

Page({
  data: {
    stats: {
      total: 0,
      today: 0,
      pending: 0,
      confirmed: 0
    },
    recentViolations: [],
    loading: true
  },
  
  onLoad() {
    this.loadStats()
    this.loadRecentViolations()
  },
  
  onShow() {
    this.loadStats()
    this.loadRecentViolations()
  },
  
  // 加载统计数据
  loadStats() {
    app.request('/statistics/overview').then(data => {
      this.setData({
        stats: {
          total: data.total || 0,
          today: data.today || 0,
          pending: (data.by_status || []).find(s => s.status === 'pending')?.count || 0,
          confirmed: (data.by_status || []).filter(s => ['confirmed', 'processed'].includes(s.status)).reduce((a, b) => a + b.count, 0)
        }
      })
    }).catch(() => {})
  },
  
  // 加载最近违规
  loadRecentViolations() {
    app.request('/violations/list', { page_size: 5 }).then(data => {
      this.setData({
        recentViolations: (data.items || []).slice(0, 5),
        loading: false
      })
    }).catch(() => {
      this.setData({ loading: false })
    })
  },
  
  // 跳转到违规列表
  goToViolations() {
    wx.navigateTo({ url: '/pages/violation/list' })
  },
  
  // 查看违规详情
  viewViolation(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/violation/detail?id=${id}` })
  },
  
  // 刷新数据
  onRefresh() {
    this.loadStats()
    this.loadRecentViolations()
  }
})
