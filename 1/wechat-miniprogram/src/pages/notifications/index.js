/**
 * 通知中心页（2026-10-03 由 DSH 新增）
 *
 * 设计依据：微信订阅消息是"一次性"的（用户每次授权只能收 1 条），
 * 所以**站内通知列表才是主渠道**，订阅消息只做提醒。后端已有
 * `wx_notifications` 表 + `/api/wx/notifications` 接口。
 */
const app = getApp()

// 违规类型 -> 中文（与后端 VIOLATION_TYPE_CN 保持一致）
const TYPE_CN = {
  red_light: '闯红灯',
  wrong_way: '逆行',
  illegal_parking: '违规停车',
  lane_departure: '压线行驶',
  no_helmet: '未戴头盔',
  speeding: '超速',
}

Page({
  data: {
    list: [],
    unread: 0,
    loading: true,
    onlyUnread: false,
  },

  onLoad() {
    this.loadList()
  },

  onShow() {
    this.loadList()
  },

  onPullDownRefresh() {
    this.loadList(() => wx.stopPullDownRefresh())
  },

  loadList(done) {
    this.setData({ loading: true })
    const q = this.data.onlyUnread ? '?only_unread=true' : ''
    app.request('/notifications' + q).then(data => {
      const rows = (data || []).map(x => ({
        ...x,
        typeCn: TYPE_CN[(x.payload && x.payload.violation_type)] || x.title || '违规通知',
        timeText: String(x.created_at || '').slice(5, 16),
      }))
      this.setData({
        list: rows,
        unread: rows.filter(r => !r.is_read).length,
        loading: false,
      })
    }).catch(() => {
      this.setData({ loading: false })
    }).then(() => { if (typeof done === 'function') done() })
  },

  // 切换"只看未读"
  onToggleUnread() {
    this.setData({ onlyUnread: !this.data.onlyUnread }, () => this.loadList())
  },

  // 点击单条 -> 标记已读
  onTapItem(e) {
    const id = e.currentTarget.dataset.id
    const item = this.data.list.find(x => x.id === id)
    if (item && !item.is_read) {
      app.request('/notifications/read', { notification_id: id }, 'POST')
        .then(() => this.loadList()).catch(() => {})
    }
  },

  // 全部已读
  onReadAll() {
    if (!this.data.unread) return
    app.request('/notifications/read', { all_read: true }, 'POST').then(() => {
      wx.showToast({ title: '已全部标记为已读', icon: 'success' })
      this.loadList()
    }).catch(() => {})
  },

  // 去绑定车辆（未绑定则收不到通知）
  goBind() {
    wx.navigateTo({ url: '/pages/my/bind' })
  },
})
