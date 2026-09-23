/**
 * 申诉提交页面
 */
const app = getApp()

Page({
  data: {
    violationId: null,
    violation: null,
    reason: '',
    contact: '',
    images: [],
    maxImages: 3,
    loading: false,
    submitting: false
  },

  onLoad(options) {
    if (options.violation_id) {
      this.setData({ violationId: options.violation_id })
      this.loadViolation(options.violation_id)
    }
  },

  // 加载违规详情
  loadViolation(id) {
    this.setData({ loading: true })
    app.request(`/violations/${id}`).then(data => {
      this.setData({ violation: data, loading: false })
    }).catch(() => {
      this.setData({ loading: false })
    })
  },

  // 输入申诉原因
  onReasonInput(e) {
    this.setData({ reason: e.detail.value })
  },

  // 输入联系方式
  onContactInput(e) {
    this.setData({ contact: e.detail.value })
  },

  // 选择图片
  chooseImage() {
    const count = this.data.maxImages - this.data.images.length
    if (count <= 0) {
      wx.showToast({ title: '最多上传3张图片', icon: 'none' })
      return
    }
    wx.chooseImage({
      count: count,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: res => {
        const tempFilePaths = res.tempFilePaths
        this.setData({
          images: [...this.data.images, ...tempFilePaths]
        })
      }
    })
  },

  // 预览图片
  previewImage(e) {
    wx.previewImage({
      urls: this.data.images,
      current: e.currentTarget.dataset.src
    })
  },

  // 删除图片
  removeImage(e) {
    const index = e.currentTarget.dataset.index
    const images = this.data.images
    images.splice(index, 1)
    this.setData({ images })
  },

  // 提交申诉
  submitAppeal() {
    const { violationId, reason, contact, images } = this.data

    // 表单验证
    if (!violationId) {
      wx.showToast({ title: '违规记录不存在', icon: 'none' })
      return
    }
    if (!reason || reason.trim().length < 10) {
      wx.showToast({ title: '请详细描述申诉理由（至少10字）', icon: 'none' })
      return
    }
    if (!contact || contact.trim().length < 8) {
      wx.showToast({ title: '请输入有效的联系方式', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    app.showLoading('提交中...')

    // 模拟提交（实际项目中需要先上传图片获取URL）
    const appealData = {
      violation_id: violationId,
      reason: reason.trim(),
      contact: contact.trim(),
      evidence_urls: images // 实际应上传后获取真实URL
    }

    app.request('/appeals/submit', appealData, 'POST')
      .then(result => {
        app.hideLoading()
        this.setData({ submitting: false })
        wx.showToast({ title: '申诉提交成功', icon: 'success' })
        // 提交成功后跳转到申诉列表
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      })
      .catch(err => {
        app.hideLoading()
        this.setData({ submitting: false })
        wx.showToast({
          title: err.message || '提交失败，请重试',
          icon: 'none'
        })
      })
  }
})