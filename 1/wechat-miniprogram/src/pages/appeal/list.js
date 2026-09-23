/**
 * 申诉列表页
 */
const app = getApp()

Page({
  data: {
    appeals: [],
    stats: {},
    loading: false,
    tabIndex: 0,
    tabs: ['全部', '待处理', '审核中', '已通过', '已驳回'],
    statusMap: { pending: '待处理', reviewing: '审核中', approved: '已通过', rejected: '已驳回' }
  },
  
  onLoad() {
    this.loadStats()
    this.loadAppeals()
  },
  
  onShow() {
    this.loadStats()
    this.loadAppeals()
  },
  
  // 切换标签
  onTabChange(e) {
    this.setData({ tabIndex: e.detail.index })
    this.loadAppeals()
  },
  
  // 加载申诉列表
  loadAppeals() {
    this.setData({ loading: true })
    const params = {}
    const tabIndex = this.data.tabIndex
    if (tabIndex === 1) params.status = 'pending'
    else if (tabIndex === 2) params.status = 'reviewing'
    else if (tabIndex === 3) params.status = 'approved'
    else if (tabIndex === 4) params.status = 'rejected'
    
    app.request('/appeals/list', params).then(data => {
      this.setData({ appeals: data.appeals || [], loading: false })
    }).catch(() => {
      this.setData({ loading: false })
    })
  },
  
  // 加载统计数据
  loadStats() {
    app.request('/appeals/statistics/summary').then(data => {
      this.setData({ stats: data })
    }).catch(() => {})
  },
  
  // 查看详情
  viewDetail(e) {
    const violationId = e.currentTarget.dataset.violationId
    wx.navigateTo({ url: `/pages/violation/detail?id=${violationId}` })
  }
})
