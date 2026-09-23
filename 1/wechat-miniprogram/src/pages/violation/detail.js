/**
 * 违规详情页
 */
const app = getApp()

Page({
  data: {
    violation: null,
    loading: true,
    aiTrace: null,
    modeText: {
      urgent: '紧急上报',
      consult: '主动咨询',
      normal: '常规检测'
    }
  },
  
  onLoad(options) {
    if (options.id) {
      this.loadDetail(options.id)
    }
  },
  
  loadDetail(id) {
    app.request(`/violations/${id}`).then(data => {
      // 尝试解析ai_trace信息
      let aiTrace = null
      if (data.additional_info && data.additional_info.ai_trace) {
        aiTrace = data.additional_info.ai_trace
        aiTrace.mode = data.additional_info.collab_mode || 'normal'
        aiTrace.session_id = data.additional_info.session_id || ''
      }
      this.setData({ 
        violation: data, 
        aiTrace: aiTrace,
        loading: false 
      })
    }).catch(() => {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    })
  },
  
  // 预览图片
  previewImage(e) {
    const urls = [e.currentTarget.dataset.src]
    wx.previewImage({ urls, current: e.currentTarget.dataset.src })
  },
  
  // 提交申诉
  goToAppeal() {
    wx.navigateTo({
      url: `/pages/appeal/submit?violation_id=${this.data.violation.id}`
    })
  },
  
  // 查看申诉状态
  goToAppealList() {
    wx.switchTab({ url: '/pages/my/index' })
  }
})
