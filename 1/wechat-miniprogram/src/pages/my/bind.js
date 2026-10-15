/**
 * 车辆绑定页（2026-10-03 由 DSH 新增）
 *
 * 为什么必须有这个页面：后端 `GET /api/wx/violations` 是**按绑定车牌**匹配的，
 * 不绑定车辆 -> 车主永远看不到自己的违规 -> "收通知 + 申诉"整条链路走不通。
 *
 * 交互设计：
 *   ① 上部显示已绑定车辆（可解绑）
 *   ② 下部为"可绑定车牌"建议列表（来自后端 /bind/status，数据源是系统识别到过的车牌）
 *      —— 演示时可直接点选，避免手输车牌出错
 *   ③ 同时保留手输入口（真实场景下车主自己输车牌）
 */
const app = getApp()

Page({
  data: {
    myVehicles: [],
    suggestPlates: [],
    hasBinding: false,
    manualPlate: '',
    loading: true,
    submitting: false,
  },

  onLoad() {
    this.loadStatus()
  },

  onShow() {
    this.loadStatus()
  },

  onPullDownRefresh() {
    this.loadStatus(() => wx.stopPullDownRefresh())
  },

  loadStatus(done) {
    this.setData({ loading: true })
    app.request('/bind/status').then(data => {
      this.setData({
        myVehicles: (data && data.my_vehicles) || [],
        suggestPlates: (data && data.suggest_plates) || [],
        hasBinding: !!(data && data.has_binding),
        loading: false,
      })
    }).catch(() => {
      this.setData({ loading: false })
    }).then(() => { if (typeof done === 'function') done() })
  },

  // 输入车牌
  onPlateInput(e) {
    this.setData({ manualPlate: (e.detail.value || '').toUpperCase().trim() })
  },

  // 一键绑定建议车牌
  onBindSuggest(e) {
    const plate = e.currentTarget.dataset.plate
    if (!plate || this.data.submitting) return
    this.doBind(plate)
  },

  // 手动绑定
  onBindManual() {
    const plate = this.data.manualPlate
    if (!plate) {
      wx.showToast({ title: '请输入车牌号', icon: 'none' })
      return
    }
    if (plate.length < 5) {
      wx.showToast({ title: '车牌号格式不正确', icon: 'none' })
      return
    }
    this.doBind(plate)
  },

  doBind(plate) {
    this.setData({ submitting: true })
    wx.showLoading({ title: '绑定中', mask: true })
    // 手输车牌不一定在系统记录里，走通用绑定；建议车牌走一键绑定（带校验）
    const isSuggest = this.data.suggestPlates.some(s => s.plate_number === plate)
    const url = isSuggest
      ? '/vehicles/bind-by-suggest?plate_number=' + encodeURIComponent(plate)
      : '/vehicles/bind'
    const body = isSuggest ? undefined : { plate_number: plate, relation: 'owner' }
    app.request(url, body, 'POST').then(() => {
      wx.hideLoading()
      wx.showToast({ title: '绑定成功', icon: 'success' })
      this.setData({ manualPlate: '', submitting: false })
      this.loadStatus()
    }).catch(err => {
      wx.hideLoading()
      this.setData({ submitting: false })
      const msg = (err && (err.detail || err.message)) || '绑定失败'
      wx.showToast({ title: String(msg).slice(0, 30), icon: 'none' })
    })
  },

  // 解绑
  onUnbind(e) {
    const plate = e.currentTarget.dataset.plate
    wx.showModal({
      title: '解除绑定',
      content: `确定解绑车辆 ${plate} 吗？解绑后将不再收到该车的违规通知。`,
      success: res => {
        if (!res.confirm) return
        app.request('/vehicles/unbind', { plate_number: plate }, 'POST').then(() => {
          wx.showToast({ title: '已解绑', icon: 'success' })
          this.loadStatus()
        }).catch(() => {})
      },
    })
  },

  // 去申诉
  goAppeal() {
    wx.switchTab({ url: '/pages/appeal/list' })
  },
})
