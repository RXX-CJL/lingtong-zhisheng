/**
 * 违规列表页
 */
const app = getApp()

Page({
  data: {
    violations: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    filters: {
      status: '',
      violation_type: ''
    }
  },
  
  onLoad(options) {
    if (options.status) {
      this.setData({ 'filters.status': options.status })
    }
    this.loadViolations()
  },
  
  onShow() {
    this.onRefresh()
  },
  
  // 加载违规列表
  loadViolations(isAppend = false) {
    if (this.data.loading) return
    
    this.setData({ loading: true })
    
    const params = {
      page: this.data.page,
      page_size: this.data.pageSize
    }
    
    if (this.data.filters.status) {
      params.status = this.data.filters.status
    }
    if (this.data.filters.violation_type) {
      params.violation_type = this.data.filters.violation_type
    }
    
    app.request('/violations/list', params).then(data => {
      const items = data.items || []
      this.setData({
        violations: isAppend ? [...this.data.violations, ...items] : items,
        hasMore: items.length >= this.data.pageSize,
        loading: false
      })
    }).catch(() => {
      this.setData({ loading: false })
    })
  },
  
  // 下拉刷新
  onRefresh() {
    this.setData({ page: 1, violations: [] })
    this.loadViolations()
  },
  
  // 上拉加载更多
  onReachBottom() {
    if (this.data.hasMore) {
      this.setData({ page: this.data.page + 1 })
      this.loadViolations(true)
    }
  },
  
  // 查看详情
  viewDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/violation/detail?id=${id}` })
  },
  
  // 筛选状态
  onStatusChange(e) {
    this.setData({ 'filters.status': e.detail.value })
    this.onRefresh()
  },
  
  // 筛选类型
  onTypeChange(e) {
    this.setData({ 'filters.violation_type': e.detail.value })
    this.onRefresh()
  }
})
